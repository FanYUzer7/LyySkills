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
    VALID_PERIODS, PERIOD_NAMES, DAILY_ONLY_ASSET_TYPES,
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
        # 用于 monitor 信号变化检测：{code: {"action": str, "score": float}}
        self._prev_signals = {}

    # ==========================================================
    # 单标的分析
    # ==========================================================
    def _analyze_raw(self, code: str, asset_type: str,
                     test_mode: bool = False,
                     period: str = "daily") -> dict:
        """执行分析并返回原始结果 dict（含 error 时也是 dict）"""
        if test_mode:
            return self._analyze_raw_test(code, asset_type, period)

        quote = self.fetcher.get_realtime_quote(code, asset_type)
        df = self.fetcher.get_history_kline(code, asset_type, period=period)
        return self.engine.analyze(df, quote)

    def _analyze_raw_test(self, code: str, asset_type: str,
                          period: str = "daily") -> dict:
        """离线测试模式的原始分析"""
        import os
        import pandas as pd

        exact_path = os.path.join(TEST_DATA_DIR, f"{code}.json")
        sample_path = os.path.join(TEST_DATA_DIR, "sample_kline.json")
        data_path = exact_path if os.path.exists(exact_path) else sample_path

        if not os.path.exists(data_path):
            return {"error": f"测试数据文件不存在: {data_path}"}

        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        if "amount" in df.columns and "turnover" not in df.columns:
            df["turnover"] = df["amount"]

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
        result["_test_data_path"] = os.path.basename(data_path)
        return result

    def analyze(self, code: str, asset_type: str,
                output_format: str = "text",
                test_mode: bool = False,
                period: str = "daily") -> str | dict:
        """
        对单个标的执行完整分析。
        :param code: 资产代码
        :param asset_type: stock/index/etf/futures/gold
        :param output_format: "text" 或 "json"
        :param test_mode: 使用本地测试数据，跳过网络请求
        :param period: K线周期 daily/weekly/monthly
        :return: 格式化报告或 dict
        """
        result = self._analyze_raw(code, asset_type, test_mode, period)

        if "error" in result:
            if output_format == "json":
                return result
            return format_error_for_display(result)

        # 提取内部标记后再序列化
        test_data_path = result.pop("_test_data_path", None)

        # 记录决策到 SQLite（非测试模式）
        if not test_mode:
            self._record_decision(code, asset_type, result, period)

        if output_format == "json":
            return _serialize(result)

        report = self._format_report(code, asset_type, result, period)
        if test_mode and test_data_path:
            period_label = PERIOD_NAMES.get(period, period)
            report = f"🧪 [离线测试模式] 数据来源: {test_data_path} | 周期: {period_label}\n\n{report}"
        return report

    def _record_decision(self, code: str, asset_type: str,
                         result: dict, period: str = "daily"):
        """将分析决策记录到 SQLite"""
        try:
            action_info = result.get("action", {})
            quote = result.get("quote") or {}
            self.db.save_decision(
                code=code,
                asset_type=asset_type,
                timestamp=datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S"),
                action=action_info.get("action", ""),
                score=result.get("final_score", 0),
                price=quote.get("price", 0),
                stop_loss=result.get("stop_loss", 0),
                take_profit=result.get("take_profit", 0),
                period=period,
            )
        except Exception:
            pass  # 决策记录失败不影响主流程

    # ==========================================================
    # 决策历史查询
    # ==========================================================
    def history(self, code: str = None, limit: int = 20,
                output_format: str = "text") -> str | list:
        """查询决策历史"""
        df = self.db.load_decisions(code=code, limit=limit)

        if df.empty:
            msg = f"暂无{'该标的' if code else ''}决策记录"
            return {"records": [], "message": msg} if output_format == "json" else f"📋 {msg}"

        if output_format == "json":
            return df.to_dict(orient="records")

        return self._format_history(df, code)

    def _format_history(self, df, code: str = None) -> str:
        """格式化决策历史表格"""
        lines = []
        sep = "=" * 70
        lines.append(sep)
        title = f"📜 决策历史记录" + (f" — {code}" if code else " — 全部标的")
        lines.append(title)
        lines.append(f"📋 共 {len(df)} 条记录")
        lines.append(sep)
        lines.append(f"  {'时间':<20} {'代码':<8} {'操作':<10} {'得分':>6} {'价格':>10} {'止损':>10} {'止盈':>10}")
        lines.append(f"  {'─'*20} {'─'*8} {'─'*10} {'─'*6} {'─'*10} {'─'*10} {'─'*10}")
        for _, row in df.iterrows():
            lines.append(
                f"  {row['timestamp']:<20} {row['code']:<8} {row['action']:<10} "
                f"{row['score']:>+6.2f} {_fmt_num(row['price']):>10} "
                f"{_fmt_num(row['stop_loss']):>10} {_fmt_num(row['take_profit']):>10}"
            )
        lines.append(sep)
        return "\n".join(lines)

    # ==========================================================
    # 数据导出
    # ==========================================================
    def export(self, code: str, asset_type: str,
               period: str = "daily",
               output_path: str = None,
               test_mode: bool = False) -> str:
        """导出K线数据 + 技术指标到 CSV"""
        import pandas as pd
        from . import indicators as ind
        from .indicators import compute_all_indicators

        if test_mode:
            import os
            exact = os.path.join(TEST_DATA_DIR, f"{code}.json")
            sample = os.path.join(TEST_DATA_DIR, "sample_kline.json")
            path = exact if os.path.exists(exact) else sample
            if not os.path.exists(path):
                return f"⚠️ 测试数据文件不存在: {path}"
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            df = pd.DataFrame(data)
            if "amount" in df.columns and "turnover" not in df.columns:
                df["turnover"] = df["amount"]
        else:
            df = self.fetcher.get_history_kline(code, asset_type, period=period)

        if df is None or df.empty:
            return "⚠️ 无可导出的数据"

        # 计算所有技术指标
        indicators = compute_all_indicators(df)
        for name, series in indicators.items():
            if isinstance(series, pd.Series):
                df[name] = series.values

        # 确定输出路径
        if not output_path:
            output_path = f"{code}_{period}.csv"

        # 移除非数据列
        drop_cols = ["code", "asset_type"]
        df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        return f"✅ 已导出到 {output_path} ({len(df)} 行, {len(df.columns)} 列)"

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
                 test_mode: bool = False,
                 period: str = "daily") -> str | dict:
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
            df = self.fetcher.get_history_kline(code, asset_type, period=period)

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
        """定时轮询模式，支持信号变化检测"""
        print(f"🔄 启动市场监控 (间隔: {interval}秒)")
        print(f"   监控标的: {self.watchlist.count()} 个")
        print(f"   按 Ctrl+C 停止\n")
        try:
            while True:
                now = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")
                print(f"{'='*60}")
                print(f"⏰ {now} 开始扫描...")

                items = self.watchlist.list_all()
                if not items:
                    print("📋 自选列表为空，请先添加标的。")
                else:
                    changes = []
                    for item in items:
                        code = item["code"]
                        asset_type = item["asset_type"]

                        # 单次分析获取原始结果
                        result = self._analyze_raw(code, asset_type)

                        if "error" in result:
                            print(format_error_for_display(result))
                            continue

                        # 打印文本报告
                        print(self._format_report(code, asset_type, result))

                        # 信号变化检测
                        action_info = result.get("action", {})
                        cur_action = action_info.get("action", "")
                        cur_score = result.get("final_score", 0)

                        prev = self._prev_signals.get(code)
                        if prev and prev["action"] != cur_action:
                            changes.append({
                                "code": code,
                                "name": (result.get("quote") or {}).get("name", code),
                                "prev_action": prev["action"],
                                "cur_action": cur_action,
                                "prev_score": prev["score"],
                                "cur_score": cur_score,
                            })

                        self._prev_signals[code] = {
                            "action": cur_action,
                            "score": cur_score,
                        }

                    # 信号变化摘要
                    if changes:
                        print(f"\n{'─'*60}")
                        print(f"🔔 【信号变化提醒】 共 {len(changes)} 个标的信号变化:")
                        for c in changes:
                            print(f"   ⚡ {c['name']} ({c['code']}): "
                                  f"{c['prev_action']} → {c['cur_action']} "
                                  f"(得分: {c['prev_score']:+.2f} → {c['cur_score']:+.2f})")
                        print(f"{'─'*60}")
                    elif self._prev_signals:
                        print(f"\n   ℹ️ 本轮扫描无信号变化")

                print(f"\n⏰ 下次扫描: {interval}秒后\n")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n✅ 监控已停止")

    # ==========================================================
    # 格式化
    # ==========================================================
    def _format_report(self, code: str, asset_type: str,
                       result: dict, period: str = "daily") -> str:
        """格式化分析报告"""
        now = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")
        quote = result.get("quote") or {}
        name = quote.get("name", code)
        type_name = ASSET_TYPE_NAMES.get(asset_type, asset_type)
        period_name = PERIOD_NAMES.get(period, period)

        lines = []
        sep = "=" * 60
        lines.append(sep)
        lines.append(f"📊 投资决策分析报告")
        lines.append(f"📅 {now} CST")
        lines.append(f"🎯 标的: {name} ({code}) [{type_name}]")
        lines.append(f"📈 K线周期: {period_name}")
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
        stop_loss = result.get("stop_loss", 0)
        take_profit = result.get("take_profit", 0)
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
        lines.append(
            f"   🛑 止损位: ¥{_fmt_num(stop_loss)} (ATR×2)  "
            f"🎯 止盈位: ¥{_fmt_num(take_profit)} (ATR×3)")

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
        period = args.get("period", "daily")
        if not code:
            print("错误: --code 为必填")
            sys.exit(1)
        if period not in VALID_PERIODS:
            print(f"错误: --period 仅支持 {', '.join(VALID_PERIODS)}")
            sys.exit(1)
        if period != "daily" and asset_type in DAILY_ONLY_ASSET_TYPES:
            print(f"提示: {ASSET_TYPE_NAMES.get(asset_type, asset_type)}仅支持日线，已自动切换为 daily")
            period = "daily"
        result = tracker.analyze(code, asset_type, fmt, test_mode=test_mode, period=period)
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
        period = args.get("period", "daily")
        if not code:
            print("错误: --code 为必填")
            sys.exit(1)
        if period not in VALID_PERIODS:
            print(f"错误: --period 仅支持 {', '.join(VALID_PERIODS)}")
            sys.exit(1)
        if period != "daily" and asset_type in DAILY_ONLY_ASSET_TYPES:
            print(f"提示: {ASSET_TYPE_NAMES.get(asset_type, asset_type)}仅支持日线，已自动切换为 daily")
            period = "daily"
        result = tracker.backtest(code, asset_type, fmt, test_mode=test_mode, period=period)
        if fmt == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result)

    elif cmd == "history":
        code = args.get("code", None)
        limit = int(args.get("limit", 20))
        result = tracker.history(code=code, limit=limit, output_format=fmt)
        if fmt == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result)

    elif cmd == "export":
        code = args.get("code", "")
        asset_type = args.get("type", "stock")
        period = args.get("period", "daily")
        output_path = args.get("output", None)
        test_mode = args.get("test", False)
        if not code:
            print("错误: --code 为必填")
            sys.exit(1)
        print(tracker.export(code, asset_type, period=period,
                             output_path=output_path, test_mode=test_mode))

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

  analyze     --code CODE --type TYPE [--period PERIOD] [--format json] [--test]
  analyze-all [--format json]
  overview    [--format json]
  monitor     [--interval SECONDS]
  backtest    --code CODE --type TYPE [--period PERIOD] [--format json] [--test]
  history     [--code CODE] [--limit N] [--format json]
  export      --code CODE --type TYPE [--period PERIOD] [--output FILE] [--test]

资产类型 (--type):
  stock    A股个股
  index    指数
  etf      ETF基金
  futures  期货
  gold     黄金/贵金属

K线周期 (--period):
  daily    日线（默认）
  weekly   周线
  monthly  月线
  注: 期货/黄金仅支持日线

示例:
  python -m skills.market_tracker.tracker watchlist add --code 600519 --name 贵州茅台 --type stock
  python -m skills.market_tracker.tracker analyze --code 600519 --type stock
  python -m skills.market_tracker.tracker analyze --code 600519 --type stock --period weekly
  python -m skills.market_tracker.tracker overview
  python -m skills.market_tracker.tracker backtest --code 600519 --type stock --test
  python -m skills.market_tracker.tracker monitor --interval 300
""")


if __name__ == "__main__":
    main()
