"""
市场跟踪器 - 主入口
编排：数据获取 → 指标计算 → 决策输出
支持 CLI 和模块调用
"""

import sys
import json
import time
from datetime import datetime, timezone, timedelta

from .config import (
    ASSET_TYPE_NAMES, DEFAULT_MONITOR_INTERVAL, TEST_DATA_DIR,
)
from .db import MarketDB
from .watchlist import Watchlist
from .data_fetcher import MarketDataFetcher
from .decision_engine import InvestmentDecision
from .backtest import BacktestEngine, format_backtest_report
from .errors import format_error_for_display

CST = timezone(timedelta(hours=8))


class MarketTracker:
    """市场跟踪器主编排类"""

    def __init__(self):
        self.db = MarketDB()
        self.watchlist = Watchlist()
        self.fetcher = MarketDataFetcher(self.db)
        self.engine = InvestmentDecision()

    # ==========================================================
    # 单标的分析
    # ==========================================================
    def analyze(self, code: str, asset_type: str,
                output_format: str = "text",
                test_mode: bool = False) -> str | dict:
        """
        对单个标的执行完整分析。
        :param code: 资产代码
        :param asset_type: stock/index/etf/futures/gold
        :param output_format: "text" 或 "json"
        :param test_mode: 使用本地测试数据，跳过网络请求
        :return: 格式化报告或 dict
        """
        if test_mode:
            return self._analyze_from_test_data(code, asset_type, output_format)

        # 1. 获取实时行情
        quote = self.fetcher.get_realtime_quote(code, asset_type)

        # 2. 获取历史K线 (自动增量缓存)
        df = self.fetcher.get_history_kline(code, asset_type)

        # 3. 决策分析
        result = self.engine.analyze(df, quote)

        if "error" in result:
            if output_format == "json":
                return result
            return format_error_for_display(result)

        if output_format == "json":
            return _serialize(result)

        return self._format_report(code, asset_type, result)

    def _analyze_from_test_data(self, code: str, asset_type: str,
                                output_format: str) -> str | dict:
        """离线测试模式：从 test_data/ 加载数据进行分析"""
        import os
        import pandas as pd

        # 查找测试数据文件：优先精确匹配 {code}.json，否则用 sample_kline.json
        exact_path = os.path.join(TEST_DATA_DIR, f"{code}.json")
        sample_path = os.path.join(TEST_DATA_DIR, "sample_kline.json")
        data_path = exact_path if os.path.exists(exact_path) else sample_path

        if not os.path.exists(data_path):
            msg = f"测试数据文件不存在: {data_path}"
            return {"error": msg} if output_format == "json" else f"⚠️ {msg}"

        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        if "amount" in df.columns and "turnover" not in df.columns:
            df["turnover"] = df["amount"]

        # 构造模拟行情
        last = df.iloc[-1]
        quote = {
            "name": f"[测试] {code}",
            "code": code,
            "price": float(last["close"]),
            "change_pct": round((last["close"] / df.iloc[-2]["close"] - 1) * 100, 2) if len(df) > 1 else 0,
            "volume": float(last["volume"]),
            "turnover": float(last.get("turnover", 0)),
            "high": float(last["high"]),
            "low": float(last["low"]),
            "open": float(last["open"]),
        }

        result = self.engine.analyze(df, quote)

        if "error" in result:
            if output_format == "json":
                return result
            return format_error_for_display(result)

        if output_format == "json":
            return _serialize(result)

        report = self._format_report(code, asset_type, result)
        return f"🧪 [离线测试模式] 数据来源: {os.path.basename(data_path)}\n\n{report}"

    # ==========================================================
    # 全自选分析
    # ==========================================================
    def analyze_all(self, output_format: str = "text") -> str | list:
        """分析自选列表中所有标的"""
        items = self.watchlist.list_all()
        if not items:
            return "📋 自选列表为空，请先添加标的。"

        reports = []
        for item in items:
            report = self.analyze(item["code"], item["asset_type"],
                                  output_format)
            reports.append(report)

        if output_format == "json":
            return reports

        return "\n\n".join(reports)

    # ==========================================================
    # 市场概览
    # ==========================================================
    def overview(self, output_format: str = "text") -> str | list:
        """获取大盘指数概览"""
        data = self.fetcher.get_market_overview()

        if output_format == "json":
            return data

        return self._format_overview(data)

    # ==========================================================
    # 策略回测
    # ==========================================================
    def backtest(self, code: str, asset_type: str,
                 output_format: str = "text",
                 test_mode: bool = False) -> str | dict:
        """对单个标的执行策略回测"""
        import os
        import pandas as pd

        if test_mode:
            exact_path = os.path.join(TEST_DATA_DIR, f"{code}.json")
            sample_path = os.path.join(TEST_DATA_DIR, "sample_kline.json")
            data_path = exact_path if os.path.exists(exact_path) else sample_path
            if not os.path.exists(data_path):
                msg = f"测试数据文件不存在: {data_path}"
                return {"error": msg} if output_format == "json" else f"⚠️ {msg}"
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            df = pd.DataFrame(data)
            if "amount" in df.columns and "turnover" not in df.columns:
                df["turnover"] = df["amount"]
        else:
            df = self.fetcher.get_history_kline(code, asset_type)

        if df is None or df.empty:
            msg = "无法获取历史数据"
            return {"error": msg} if output_format == "json" else f"⚠️ {msg}"

        engine = BacktestEngine()
        result = engine.run(df)

        if output_format == "json":
            return _serialize(result)

        name = self.watchlist.get(code)
        name_str = name["name"] if name else ""
        return format_backtest_report(result, code, name_str)

    # ==========================================================
    # 定时监控
    # ==========================================================
    def monitor(self, interval: int = DEFAULT_MONITOR_INTERVAL):
        """定时轮询模式"""
        print(f"🔄 启动市场监控 (间隔: {interval}秒)")
        print(f"   监控标的: {self.watchlist.count()} 个")
        print(f"   按 Ctrl+C 停止\n")
        try:
            while True:
                now = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")
                print(f"{'='*60}")
                print(f"⏰ {now} 开始扫描...")
                print(self.analyze_all())
                print(f"\n⏰ 下次扫描: {interval}秒后\n")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n✅ 监控已停止")

    # ==========================================================
    # 格式化
    # ==========================================================
    def _format_report(self, code: str, asset_type: str,
                       result: dict) -> str:
        """格式化分析报告"""
        now = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")
        quote = result.get("quote") or {}
        name = quote.get("name", code)
        type_name = ASSET_TYPE_NAMES.get(asset_type, asset_type)

        lines = []
        sep = "=" * 60
        lines.append(sep)
        lines.append(f"📊 投资决策分析报告")
        lines.append(f"📅 {now} CST")
        lines.append(f"🎯 标的: {name} ({code}) [{type_name}]")
        lines.append(sep)

        # 实时行情
        if quote and "error" not in quote:
            lines.append("")
            lines.append("📈 【实时行情】")
            price = quote.get("price")
            chg = quote.get("change_pct")
            vol = quote.get("volume")
            turn = quote.get("turnover")
            lines.append(f"   当前价: ¥{_fmt_num(price)}  "
                         f"涨跌幅: {_fmt_pct(chg)}")
            lines.append(f"   成交量: {_fmt_vol(vol)}  "
                         f"成交额: {_fmt_money(turn)}")

        # 技术信号
        tech = result.get("technical_signals", {})
        lines.append("")
        lines.append("🔍 【技术指标信号】")
        signal_order = ["ma_alignment", "macd_cross", "rsi",
                        "kdj", "bollinger", "adx_trend", "volume_price"]
        signal_labels = {
            "ma_alignment": "趋势", "macd_cross": "MACD",
            "rsi": "RSI", "kdj": "KDJ", "bollinger": "布林",
            "adx_trend": "ADX", "volume_price": "量价",
        }
        for key in signal_order:
            sig = tech.get(key, {})
            label = signal_labels.get(key, key)
            detail = sig.get("detail", "N/A")
            lines.append(f"   {label}: {detail}")

        # 市场状态
        ms = result.get("market_state", "")
        if ms:
            lines.append(f"   市场状态: {ms}")

        # 因子评分
        factors = result.get("factor_scores", {})
        composite = result.get("composite_factor_score", 0)
        final = result.get("final_score", 0)
        lines.append("")
        lines.append("📊 【量化因子评分】")
        for fname, fdata in factors.items():
            flabel = {"momentum": "动量", "volatility": "波动",
                     "volume_price": "量价"}.get(fname, fname)
            fscore = fdata.get("score", 0)
            fdetail = fdata.get("detail", "")
            lines.append(f"   {flabel}因子: {fscore:+.2f} ({fdetail})")
        lines.append(f"   综合得分: {int((final + 1) / 2 * 100)}/100")

        # 投资决策
        action = result.get("action", {})
        support = result.get("support", 0)
        resistance = result.get("resistance", 0)
        lines.append("")
        lines.append("💡 【投资决策】")
        lines.append(
            f"   建议操作: {action.get('emoji', '')} "
            f"{action.get('action', 'N/A')}")
        lines.append(
            f"   置信度: {action.get('confidence', 0):.0%}  "
            f"推荐仓位: {action.get('position_pct', 'N/A')}")
        lines.append(
            f"   支撑位: ¥{_fmt_num(support)}  "
            f"阻力位: ¥{_fmt_num(resistance)}")

        # 风险提示
        risk = result.get("risk", {})
        lines.append("")
        lines.append("⚠️ 【风险提示】")
        lines.append(
            f"   当前波动率: {risk.get('volatility_level', 'N/A')} "
            f"(ATR={risk.get('atr', 0):.2f})")
        lines.append(
            f"   近20日最大回撤: {risk.get('max_drawdown_20d', 0):.1%}")
        for w in risk.get("warnings", []):
            lines.append(f"   ⚠ {w}")

        lines.append("")
        lines.append("⚠️ 本分析基于技术指标与量化因子，仅供参考，不构成投资建议。")
        lines.append(sep)

        return "\n".join(lines)

    def _format_overview(self, data: list[dict]) -> str:
        """格式化市场概览"""
        now = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")
        lines = []
        sep = "=" * 60
        lines.append(sep)
        lines.append(f"📊 市场概览")
        lines.append(f"📅 {now} CST")
        lines.append(sep)
        lines.append("")

        if not data:
            lines.append("  暂无数据")
            return "\n".join(lines)

        for item in data:
            if "error" in item:
                lines.append(f"  ⚠️ {item['error']}")
                continue
            name = item.get("name", "")
            price = item.get("price")
            chg = item.get("change_pct")
            turn = item.get("turnover")
            arrow = "🔺" if (chg or 0) > 0 else "🔻" if (chg or 0) < 0 else "➖"
            lines.append(
                f"  {arrow} {name:<10} {_fmt_num(price):>12}  "
                f"{_fmt_pct(chg):>8}  成交额: {_fmt_money(turn)}")

        lines.append("")
        lines.append(sep)
        return "\n".join(lines)


# ==============================================================
# 工具函数
# ==============================================================

def _fmt_num(val) -> str:
    if val is None:
        return "--"
    try:
        return f"{float(val):,.2f}"
    except (ValueError, TypeError):
        return str(val)


def _fmt_pct(val) -> str:
    if val is None:
        return "--"
    try:
        v = float(val)
        sign = "+" if v > 0 else ""
        return f"{sign}{v:.2f}%"
    except (ValueError, TypeError):
        return str(val)


def _fmt_vol(val) -> str:
    if val is None:
        return "--"
    try:
        v = float(val)
        if v >= 1e8:
            return f"{v / 1e8:.2f}亿手"
        elif v >= 1e4:
            return f"{v / 1e4:.1f}万手"
        return f"{v:.0f}手"
    except (ValueError, TypeError):
        return str(val)


def _fmt_money(val) -> str:
    if val is None:
        return "--"
    try:
        v = float(val)
        if v >= 1e8:
            return f"{v / 1e8:.2f}亿"
        elif v >= 1e4:
            return f"{v / 1e4:.1f}万"
        return f"{v:.0f}"
    except (ValueError, TypeError):
        return str(val)


def _serialize(obj):
    """将结果转为 JSON-safe dict"""
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    if isinstance(obj, float):
        if obj != obj:  # NaN
            return None
        return round(obj, 6)
    return obj


# ==============================================================
# CLI 入口
# ==============================================================

def _parse_args(argv: list[str]) -> dict:
    result = {}
    i = 0
    while i < len(argv):
        if argv[i].startswith("--"):
            key = argv[i][2:]
            # Next arg exists and is not another flag → key-value pair
            if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                result[key] = argv[i + 1]
                i += 2
            else:
                # Boolean flag
                result[key] = True
                i += 1
        else:
            i += 1
    return result


def main():
    if len(sys.argv) < 2:
        _print_usage()
        sys.exit(1)

    cmd = sys.argv[1]
    args = _parse_args(sys.argv[2:])
    fmt = args.get("format", "text")

    tracker = MarketTracker()

    if cmd == "watchlist":
        _handle_watchlist(tracker, args)

    elif cmd == "analyze":
        code = args.get("code", "")
        asset_type = args.get("type", "stock")
        test_mode = args.get("test", False)
        if not code:
            print("错误: --code 为必填")
            sys.exit(1)
        result = tracker.analyze(code, asset_type, fmt, test_mode=test_mode)
        if fmt == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result)

    elif cmd == "analyze-all":
        result = tracker.analyze_all(fmt)
        if fmt == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result)

    elif cmd == "overview":
        result = tracker.overview(fmt)
        if fmt == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result)

    elif cmd == "monitor":
        interval = int(args.get("interval", DEFAULT_MONITOR_INTERVAL))
        tracker.monitor(interval)

    elif cmd == "backtest":
        code = args.get("code", "")
        asset_type = args.get("type", "stock")
        test_mode = args.get("test", False)
        if not code:
            print("错误: --code 为必填")
            sys.exit(1)
        result = tracker.backtest(code, asset_type, fmt, test_mode=test_mode)
        if fmt == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result)

    else:
        print(f"未知命令: {cmd}")
        _print_usage()
        sys.exit(1)


def _handle_watchlist(tracker: MarketTracker, args: dict):
    """处理 watchlist 子命令"""
    sub_cmd = sys.argv[2] if len(sys.argv) > 2 else "list"

    wl = tracker.watchlist

    if sub_cmd == "add":
        code = args.get("code", "")
        name = args.get("name", "")
        asset_type = args.get("type", "stock")
        group = args.get("group", "默认")
        if not code or not name:
            print("错误: --code 和 --name 为必填")
            sys.exit(1)
        entry = wl.add(code, name, asset_type, group)
        print(f"✅ 已添加: {entry['name']} ({entry['code']}) "
              f"[{ASSET_TYPE_NAMES.get(asset_type, asset_type)}]")

    elif sub_cmd == "remove":
        code = args.get("code", "")
        if not code:
            print("错误: --code 为必填")
            sys.exit(1)
        if wl.remove(code):
            print(f"✅ 已移除: {code}")
        else:
            print(f"⚠️ 未找到: {code}")

    elif sub_cmd == "list":
        group = args.get("group")
        asset_type = args.get("type")
        items = wl.list_all(group=group, asset_type=asset_type)
        print(f"📋 自选列表 ({len(items)} 个)")
        print(wl.format_table(items))

    else:
        print(f"未知 watchlist 子命令: {sub_cmd}")
        sys.exit(1)


def _print_usage():
    print("""用法: python -m skills.market_tracker.tracker <command> [options]

命令:
  watchlist add    --code CODE --name NAME --type TYPE [--group GROUP]
  watchlist remove --code CODE
  watchlist list   [--group GROUP] [--type TYPE]

  analyze     --code CODE --type TYPE [--format json] [--test]
  analyze-all [--format json]
  overview    [--format json]
  monitor     [--interval SECONDS]
  backtest    --code CODE --type TYPE [--format json] [--test]

资产类型 (--type):
  stock    A股个股
  index    指数
  etf      ETF基金
  futures  期货
  gold     黄金/贵金属

示例:
  python -m skills.market_tracker.tracker watchlist add --code 600519 --name 贵州茅台 --type stock
  python -m skills.market_tracker.tracker analyze --code 600519 --type stock
  python -m skills.market_tracker.tracker overview
  python -m skills.market_tracker.tracker backtest --code 600519 --type stock --test
  python -m skills.market_tracker.tracker monitor --interval 300
""")


if __name__ == "__main__":
    main()
