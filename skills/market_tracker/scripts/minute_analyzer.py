"""
市场跟踪器 - 分时数据分析器
分析当日分时数据，提供价格、成交量、趋势等分析指标
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
import numpy as np
import pandas as pd

import db
import data_fetcher


class MinuteAnalyzer:
    """分时数据分析器"""

    def __init__(self, code: str, asset_type: str, period: str = "5"):
        self.code = code
        self.asset_type = asset_type
        self.period = period
        self.db = db.MarketDB()
        self.data = None

    def load_today(self) -> pd.DataFrame:
        """加载今日分时数据"""
        today = datetime.now().strftime("%Y-%m-%d")
        self.data = self.db.load_minute_kline(
            self.code, self.period,
            start_date=today, end_date=today)
        return self.data

    def fetch_and_load(self) -> pd.DataFrame:
        """从网络获取并加载今日分时数据"""
        fetcher = data_fetcher.MinuteDataFetcher(self.db)
        self.data = fetcher.get_realtime_minute(
            self.code, self.asset_type, self.period)
        return self.data

    def analyze(self) -> dict:
        """
        分析当日分时数据，返回分析结果字典。
        """
        if self.data is None or self.data.empty:
            return {"error": "No data available"}

        df = self.data.copy()

        # 基本信息
        result = {
            "code": self.code,
            "asset_type": self.asset_type,
            "period": self.period,
            "data_points": len(df),
            "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # 价格分析
        result["price"] = self._analyze_price(df)

        # 成交量分析
        result["volume"] = self._analyze_volume(df)

        # 时间点分析
        result["time_points"] = self._analyze_time_points(df)

        # 趋势分析
        result["trend"] = self._analyze_trend(df)

        # 波动分析
        result["volatility"] = self._analyze_volatility(df)

        # 均线分析
        result["ma"] = self._analyze_ma(df)

        return result

    def _analyze_price(self, df: pd.DataFrame) -> dict:
        """价格分析"""
        close = df["close"].iloc[-1] if not df.empty else 0
        open_price = df["open"].iloc[0] if not df.empty else 0
        high = df["high"].max() if "high" in df.columns else df["close"].max()
        low = df["low"].min() if "low" in df.columns else df["close"].min()

        change = close - open_price
        change_pct = (change / open_price * 100) if open_price != 0 else 0

        return {
            "open": round(open_price, 2),
            "close": round(close, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
        }

    def _analyze_volume(self, df: pd.DataFrame) -> dict:
        """成交量分析"""
        total_volume = df["volume"].sum() if "volume" in df.columns else 0

        # 计算量能变化（对比前几个周期）
        if len(df) >= 4:
            recent_vol = df["volume"].iloc[-4:].mean()
            earlier_vol = df["volume"].iloc[:-4].mean()
            vol_change = ((recent_vol - earlier_vol) / earlier_vol * 100) if earlier_vol != 0 else 0
        else:
            vol_change = 0

        return {
            "total_volume": int(total_volume),
            "avg_volume": int(df["volume"].mean()) if "volume" in df.columns else 0,
            "volume_change_pct": round(vol_change, 2),
        }

    def _analyze_time_points(self, df: pd.DataFrame) -> dict:
        """时间点分析"""
        if "time" not in df.columns or df.empty:
            return {}

        # 找到最高价和最低价出现的时间
        high_col = "high" if "high" in df.columns else "close"
        low_col = "low" if "low" in df.columns else "close"

        high_idx = df[high_col].idxmax()
        low_idx = df[low_col].idxmin()

        return {
            "highest_time": str(df.loc[high_idx, "time"]),
            "highest_price": round(df.loc[high_idx, high_col], 2),
            "lowest_time": str(df.loc[low_idx, "time"]),
            "lowest_price": round(df.loc[low_idx, low_col], 2),
        }

    def _analyze_trend(self, df: pd.DataFrame) -> dict:
        """趋势分析"""
        if len(df) < 2:
            return {"direction": "unknown"}

        # 简单趋势：比较首尾
        first_close = df["close"].iloc[0]
        last_close = df["close"].iloc[-1]

        if last_close > first_close * 1.01:
            direction = "up"
        elif last_close < first_close * 0.99:
            direction = "down"
        else:
            direction = "sideways"

        # 计算斜率
        x = np.arange(len(df))
        y = df["close"].values
        slope = np.polyfit(x, y, 1)[0]

        return {
            "direction": direction,
            "slope": round(slope, 4),
        }

    def _analyze_volatility(self, df: pd.DataFrame) -> dict:
        """波动性分析"""
        close = df["close"]
        open_price = df["open"].iloc[0] if not df.empty else 0

        # 振幅
        high = df["high"].max() if "high" in df.columns else close.max()
        low = df["low"].min() if "low" in df.columns else close.min()
        amplitude = ((high - low) / low * 100) if low != 0 else 0

        # 标准差
        std = close.std()
        cv = (std / close.mean() * 100) if close.mean() != 0 else 0

        return {
            "amplitude": round(amplitude, 2),
            "std": round(std, 4),
            "cv": round(cv, 2),  # 变异系数
        }

    def _analyze_ma(self, df: pd.DataFrame) -> dict:
        """均线分析"""
        close = df["close"]

        # 简单移动平均
        ma5 = close.rolling(window=min(5, len(close)), min_periods=1).mean().iloc[-1]
        ma10 = close.rolling(window=min(10, len(close)), min_periods=1).mean().iloc[-1]
        ma20 = close.rolling(window=min(20, len(close)), min_periods=1).mean().iloc[-1]

        last_price = close.iloc[-1]

        return {
            "ma5": round(ma5, 2),
            "ma10": round(ma10, 2),
            "ma20": round(ma20, 2) if len(close) >= 20 else None,
            "price_vs_ma5": "above" if last_price > ma5 else "below",
            "ma5_vs_ma10": "above" if ma5 > ma10 else "below",
        }

    def get_signals(self) -> dict:
        """
        获取分时交易信号。
        """
        if self.data is None or self.data.empty:
            return {"error": "No data available"}

        signals = []
        df = self.data
        close = df["close"]

        # 均线信号
        ma5 = close.rolling(window=min(5, len(close)), min_periods=1).mean()
        ma10 = close.rolling(window=min(10, len(close)), min_periods=1).mean()

        if len(df) >= 2:
            # 金叉/死叉
            if ma5.iloc[-1] > ma10.iloc[-1] and ma5.iloc[-2] <= ma10.iloc[-2]:
                signals.append({"type": "golden_cross", "signal": "buy", "reason": "MA5 crosses above MA10"})
            elif ma5.iloc[-1] < ma10.iloc[-1] and ma5.iloc[-2] >= ma10.iloc[-2]:
                signals.append({"type": "death_cross", "signal": "sell", "reason": "MA5 crosses below MA10"})

        # 价格突破信号
        high = df["high"].max() if "high" in df.columns else close.max()
        if close.iloc[-1] >= high * 0.99:
            signals.append({"type": "high_break", "signal": "sell", "reason": "Price near daily high"})

        low = df["low"].min() if "low" in df.columns else close.min()
        if close.iloc[-1] <= low * 1.01:
            signals.append({"type": "low_break", "signal": "buy", "reason": "Price near daily low"})

        # 放量信号
        if len(df) >= 4:
            recent_vol = df["volume"].iloc[-2:].mean()
            earlier_vol = df["volume"].iloc[:-2].mean()
            if recent_vol > earlier_vol * 1.5:
                signals.append({"type": "volume_surge", "signal": "watch", "reason": "Volume surge detected"})

        return {
            "signals": signals,
            "signal_count": len(signals),
        }


def format_analysis(analysis: dict) -> str:
    """格式化分析结果为文本"""
    if "error" in analysis:
        return f"Error: {analysis['error']}"

    lines = []
    lines.append("=" * 50)
    lines.append(f"分时数据分析 - {analysis['code']} ({analysis['asset_type']})")
    lines.append(f"周期: {analysis['period']}分钟 | 数据点: {analysis['data_points']}")
    lines.append("=" * 50)

    # 价格
    p = analysis.get("price", {})
    lines.append(f"\n【价格】")
    lines.append(f"  开盘: {p.get('open', 'N/A')} | 收盘: {p.get('close', 'N/A')}")
    lines.append(f"  最高: {p.get('high', 'N/A')} | 最低: {p.get('low', 'N/A')}")
    lines.append(f"  涨跌: {p.get('change', 'N/A')} ({p.get('change_pct', 'N/A')}%)")

    # 成交量
    v = analysis.get("volume", {})
    lines.append(f"\n【成交量】")
    lines.append(f"  总成交量: {v.get('total_volume', 'N/A'):,}")
    lines.append(f"  平均成交量: {v.get('avg_volume', 'N/A'):,}")
    lines.append(f"  量能变化: {v.get('volume_change_pct', 'N/A')}%")

    # 时间点
    t = analysis.get("time_points", {})
    if t:
        lines.append(f"\n【时间点】")
        lines.append(f"  最高价: {t.get('highest_time', 'N/A')} @ {t.get('highest_price', 'N/A')}")
        lines.append(f"  最低价: {t.get('lowest_time', 'N/A')} @ {t.get('lowest_price', 'N/A')}")

    # 趋势
    tr = analysis.get("trend", {})
    if tr:
        direction_map = {"up": "上涨", "down": "下跌", "sideways": "震荡"}
        lines.append(f"\n【趋势】")
        lines.append(f"  方向: {direction_map.get(tr.get('direction'), '未知')}")
        lines.append(f"  斜率: {tr.get('slope', 'N/A')}")

    # 波动
    vol = analysis.get("volatility", {})
    if vol:
        lines.append(f"\n【波动】")
        lines.append(f"  振幅: {vol.get('amplitude', 'N/A')}%")
        lines.append(f"  标准差: {vol.get('std', 'N/A')}")

    # 均线
    ma = analysis.get("ma", {})
    if ma:
        lines.append(f"\n【均线】")
        lines.append(f"  MA5: {ma.get('ma5', 'N/A')} | MA10: {ma.get('ma10', 'N/A')}")
        if ma.get("ma20"):
            lines.append(f"  MA20: {ma.get('ma20')}")

    lines.append("\n" + "=" * 50)

    return "\n".join(lines)


# ============================================================
# CLI 入口
# ============================================================
def _parse_args(argv: list[str]) -> dict:
    args = {}
    i = 0
    while i < len(argv):
        if argv[i].startswith("--"):
            key = argv[i][2:]
            if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                args[key] = argv[i + 1]
                i += 2
            else:
                args[key] = True
                i += 1
        else:
            i += 1
    return args


def main():
    args = _parse_args(sys.argv[1:])
    code = args.get("code", "")
    asset_type = args.get("type", "stock")
    period = args.get("period", "5")

    if not code:
        print("Usage: python minute_analyzer.py --code CODE [--type stock|etf|index] [--period 1|5|15|30|60]")
        sys.exit(1)

    # 检查支持
    if not data_fetcher.get_minute_supported(asset_type):
        print(f"Error: 资产类型 {asset_type} 不支持分时数据")
        print(f"支持的类型: {data_fetcher.MINUTE_SUPPORTED_ASSETS}")
        sys.exit(1)

    # 创建分析器
    analyzer = MinuteAnalyzer(code, asset_type, period)

    # 获取数据
    print(f"正在获取 {code} ({asset_type}) {period}分钟分时数据...")
    data = analyzer.fetch_and_load()

    if data is None or data.empty:
        print("Error: 无法获取分时数据")
        sys.exit(1)

    print(f"获取到 {len(data)} 条分时数据")

    # 分析
    analysis = analyzer.analyze()
    print(format_analysis(analysis))

    # 信号
    signals = analyzer.get_signals()
    if signals.get("signals"):
        print("\n【交易信号】")
        for s in signals["signals"]:
            signal_map = {"buy": "买入", "sell": "卖出", "watch": "关注"}
            print(f"  - {signal_map.get(s['signal'], s['signal'])}: {s['reason']}")


if __name__ == "__main__":
    main()
