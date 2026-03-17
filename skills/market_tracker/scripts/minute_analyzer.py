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

        # 时间段分析
        result["segments"] = self._analyze_segments(df)

        # 量价关系分析
        result["price_volume"] = self._analyze_price_volume(df)

        # 主力行为分析
        result["institutional"] = self._analyze_institutional(df)

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

    # ============================================================
    # 时间段分析
    # ============================================================
    def _segment_by_time(self, df: pd.DataFrame) -> dict:
        """按时间段分割分时数据"""
        if "time" not in df.columns:
            return {}

        segments = {
            "pre_open": [],      # 09:15-09:30 集合竞价
            "morning": [],       # 09:30-11:30 早盘
            "afternoon": [],     # 13:00-14:30 午盘
            "closing": [],       # 14:30-15:00 尾盘
        }

        for idx, row in df.iterrows():
            time_str = str(row.get("time", ""))
            if not time_str or time_str == "nan":
                continue

            # 提取小时分钟
            try:
                if len(time_str) >= 5:
                    hour = int(time_str[:2])
                    minute = int(time_str[3:5])
                else:
                    continue
            except:
                continue

            time_val = hour * 60 + minute  # 转换为分钟数

            if 555 <= time_val < 570:  # 09:15-09:30
                segments["pre_open"].append(row)
            elif 570 <= time_val < 690:  # 09:30-11:30
                segments["morning"].append(row)
            elif 780 <= time_val < 870:  # 13:00-14:30
                segments["afternoon"].append(row)
            elif 870 <= time_val <= 900:  # 14:30-15:00
                segments["closing"].append(row)

        return segments

    def _analyze_segments(self, df: pd.DataFrame) -> dict:
        """分析各时间段的量价特征"""
        segments = self._segment_by_time(df)

        if not segments:
            return {}

        result = {}
        avg_volume = df["volume"].mean() if "volume" in df.columns else 1

        for seg_name, seg_data in segments.items():
            if not seg_data:
                continue

            seg_df = pd.DataFrame(seg_data)
            if seg_df.empty:
                continue

            close = seg_df["close"]
            open_price = seg_df["open"].iloc[0]
            last_close = close.iloc[-1]

            change = last_close - open_price
            change_pct = (change / open_price * 100) if open_price != 0 else 0

            seg_vol = seg_df["volume"].sum() if "volume" in seg_df.columns else 0
            seg_vol_ratio = (seg_vol / avg_volume) if avg_volume > 0 else 0

            seg_label = {
                "pre_open": "集合竞价",
                "morning": "早盘",
                "afternoon": "午盘",
                "closing": "尾盘"
            }.get(seg_name, seg_name)

            result[seg_label] = {
                "open": round(open_price, 2),
                "close": round(last_close, 2),
                "change_pct": round(change_pct, 2),
                "volume": int(seg_vol),
                "volume_ratio": round(seg_vol_ratio, 2),  # 相对平均量能
            }

        return result

    # ============================================================
    # 量价关系分析
    # ============================================================
    def _analyze_price_volume(self, df: pd.DataFrame) -> dict:
        """分析涨跌幅与成交量的关系"""
        if len(df) < 2:
            return {}

        close = df["close"]
        volume = df["volume"] if "volume" in df.columns else pd.Series([1] * len(df))

        # 计算涨跌幅
        returns = close.pct_change().fillna(0)

        # 计算量能变化
        vol_change = volume.pct_change().fillna(0)

        # 涨跌幅与成交量相关性
        corr = returns.corr(volume) if len(df) > 2 else 0

        # 统计上涨/下跌时的平均量能
        up_mask = returns > 0
        down_mask = returns < 0

        up_vol_avg = volume[up_mask].mean() if up_mask.sum() > 0 else 0
        down_vol_avg = volume[down_mask].mean() if down_mask.sum() > 0 else 0

        # 检测量价形态
        pattern = self._detect_volume_price_pattern(df)

        return {
            "correlation": round(corr, 3),
            "up_volume_avg": int(up_vol_avg),
            "down_volume_avg": int(down_vol_avg),
            "volume_price_pattern": pattern,
        }

    def _detect_volume_price_pattern(self, df: pd.DataFrame) -> dict:
        """检测量价形态"""
        if len(df) < 4:
            return {}

        close = df["close"]
        volume = df["volume"] if "volume" in df.columns else pd.Series([1] * len(df))
        avg_vol = volume.mean()

        patterns = []

        # 放量上涨：量能 > 均量120% 且上涨
        recent_vol = volume.iloc[-3:].mean()
        recent_change = (close.iloc[-1] - close.iloc[-3]) / close.iloc[-3] * 100 if len(df) >= 3 else 0

        if recent_vol > avg_vol * 1.2 and recent_change > 2:
            patterns.append({"type": "放量上涨", "strength": "strong"})
        elif recent_vol > avg_vol * 1.2 and recent_change < -2:
            patterns.append({"type": "放量下跌", "strength": "strong"})

        # 缩量上涨/下跌
        if recent_vol < avg_vol * 0.5:
            if recent_change > 1:
                patterns.append({"type": "缩量上涨", "strength": "weak"})
            elif recent_change < -1:
                patterns.append({"type": "缩量下跌", "strength": "weak"})

        # 量价背离：价格创新高但量能不足
        price_high = close.max()
        if close.iloc[-1] >= price_high * 0.99 and recent_vol < avg_vol * 0.8:
            patterns.append({"type": "量价背离", "strength": "warning"})

        # 量价齐升：量能放大且价格上涨
        if recent_vol > avg_vol * 1.1 and recent_change > 1:
            patterns.append({"type": "量价齐升", "strength": "strong"})

        return {
            "detected": [p["type"] for p in patterns],
            "main_pattern": patterns[0]["type"] if patterns else "normal",
        }

    # ============================================================
    # 主力行为识别
    # ============================================================
    def _analyze_institutional(self, df: pd.DataFrame) -> dict:
        """综合分析主力行为"""
        if df.empty or len(df) < 4:
            return {"error": "数据不足"}

        # 计算各项特征
        accumulation_score = self._detect_accumulation(df)
        washout_score = self._detect_washout(df)
        distribution_score = self._detect_distribution(df)
        rally_score = self._detect_rally(df)

        # 计算各行为概率
        behavior_scores = {
            "吸筹": accumulation_score,
            "洗盘": washout_score,
            "出货": distribution_score,
            "拉升": rally_score,
        }

        # 归一化为概率
        total = sum(behavior_scores.values())
        if total > 0:
            probabilities = {k: round(v / total * 100, 1) for k, v in behavior_scores.items()}
        else:
            probabilities = {"吸筹": 25, "洗盘": 25, "出货": 25, "拉升": 25}

        # 综合判断
        dominant = max(probabilities, key=probabilities.get)

        # 生成操作建议
        advice = self._generate_advice(dominant, probabilities, df)

        return {
            "probabilities": probabilities,
            "dominant_behavior": dominant,
            "advice": advice,
            "features": {
                "accumulation": accumulation_score,
                "washout": washout_score,
                "distribution": distribution_score,
                "rally": rally_score,
            }
        }

    def _detect_accumulation(self, df: pd.DataFrame) -> float:
        """检测吸筹特征"""
        score = 0

        close = df["close"]
        volume = df["volume"] if "volume" in df.columns else pd.Series([1] * len(df))
        avg_vol = volume.mean()

        first_close = close.iloc[0]
        last_close = close.iloc[-1]
        high_price = close.max()
        low_price = close.min()

        # 特征1: 整体缩量（总成交量低于均量的1.1倍）
        total_vol = volume.sum()
        expected_vol = avg_vol * len(df)
        if total_vol < expected_vol * 1.1:
            score += 15

        # 特征2: 价格在低位（收盘价位置 < 30%，且相比开盘下跌或持平）
        price_position = (last_close - low_price) / (high_price - low_price) * 100 if high_price > low_price else 50
        if price_position < 30 and last_close <= first_close:
            score += 25

        # 特征3: 振幅较小（< 4%），低位横盘
        amplitude = (high_price - low_price) / low_price * 100 if low_price > 0 else 0
        if amplitude < 4:
            score += 20

        # 特征4: 尾盘有拉升行为（14:00后涨幅 > 0.5%）
        if "time" in df.columns:
            late_df = df[df["time"].astype(str).str.startswith("14:")]
            if not late_df.empty:
                late_change = (late_df["close"].iloc[-1] - late_df["close"].iloc[0]) / late_df["close"].iloc[0] * 100 if late_df["close"].iloc[0] > 0 else 0
                if late_change > 0.5:
                    score += 30

        # 特征5: 整体呈横盘或下跌趋势（不是上涨趋势）
        if last_close <= first_close * 1.01:
            score += 10

        return min(score, 100)

    def _detect_washout(self, df: pd.DataFrame) -> float:
        """检测洗盘特征"""
        score = 0

        close = df["close"]
        volume = df["volume"] if "volume" in df.columns else pd.Series([1] * len(df))

        # 特征1: 冲高后回落（最高点 > 均价3%，收盘接近均价）
        avg_price = close.mean()
        high = close.max()
        last_close = close.iloc[-1]

        if high > avg_price * 1.03 and abs(last_close - avg_price) / avg_price < 0.02:
            score += 30

        # 特征2: 回调缩量（下跌时量能 < 上涨时量能）
        returns = close.pct_change().fillna(0)
        up_vol = volume[returns > 0].mean() if (returns > 0).sum() > 0 else 0
        down_vol = volume[returns < 0].mean() if (returns < 0).sum() > 0 else 0

        if down_vol < up_vol and down_vol > 0:
            score += 35

        # 特征3: 整体振幅适中（3%-8%）
        amplitude = (close.max() - close.min()) / close.min() * 100 if close.min() > 0 else 0
        if 3 <= amplitude <= 8:
            score += 35

        return min(score, 100)

    def _detect_distribution(self, df: pd.DataFrame) -> float:
        """检测出货特征"""
        score = 0

        close = df["close"]
        volume = df["volume"] if "volume" in df.columns else pd.Series([1] * len(df))
        avg_vol = volume.mean()

        first_close = close.iloc[0]
        last_close = close.iloc[-1]
        high_price = close.max()
        low_price = close.min()

        # 特征1: 放量（量能 > 均量100%，即总量大于预期）
        if volume.sum() > avg_vol * len(df):
            score += 15

        # 特征2: 尾盘跳水（14:00后下跌 > 0.3%）
        if "time" in df.columns:
            late_df = df[df["time"].astype(str).str.startswith("14:")]
            if not late_df.empty and len(late_df) >= 2:
                late_change = (late_df["close"].iloc[-1] - late_df["close"].iloc[0]) / late_df["close"].iloc[0] * 100 if late_df["close"].iloc[0] > 0 else 0
                if late_change < -0.3:
                    score += 35

        # 特征3: 冲高回落走势（最高点在盘中，收盘低于开盘）
        if high_price == close.max() and last_close < first_close:
            score += 35

        # 特征4: 涨幅很小（< 1%）但有量能
        total_change = (last_close - first_close) / first_close * 100 if first_close > 0 else 0
        if abs(total_change) < 1:
            score += 15

        return min(score, 100)

    def _detect_rally(self, df: pd.DataFrame) -> float:
        """检测拉升特征"""
        score = 0

        close = df["close"]
        volume = df["volume"] if "volume" in df.columns else pd.Series([1] * len(df))
        avg_vol = volume.mean()

        # 特征1: 放量上涨（量能 > 均量120%）
        recent_vol = volume.iloc[-3:].mean()
        if recent_vol > avg_vol * 1.2:
            score += 25

        # 特征2: 价格创新高
        if close.iloc[-1] >= close.max() * 0.99:
            score += 25

        # 特征3: 快速拉升（连续上涨）
        returns = close.pct_change().fillna(0)
        consecutive_up = 0
        for r in returns:
            if r > 0:
                consecutive_up += 1
            else:
                break
        if consecutive_up >= 3:
            score += 30

        # 特征4: 尾盘强势
        if "time" in df.columns:
            last_rows = df.tail(3)
            last_change = (last_rows["close"].iloc[-1] - last_rows["open"].iloc[0]) / last_rows["open"].iloc[0] * 100
            if last_change > 2:
                score += 20

        return min(score, 100)

    def _generate_advice(self, dominant: str, probabilities: dict, df: pd.DataFrame) -> str:
        """生成操作建议"""
        close = df["close"]
        change_pct = (close.iloc[-1] - close.iloc[0]) / close.iloc[0] * 100

        advice_map = {
            "吸筹": f"检测到吸筹特征({probabilities.get('吸筹', 0)}%)，主力可能在低位建仓，建议观望或轻仓关注",
            "洗盘": f"检测到洗盘特征({probabilities.get('洗盘', 0)}%)，可能是上涨中继，建议持股待涨",
            "出货": f"检测到出货特征({probabilities.get('出货', 0)}%)，注意风险，建议减仓或观望",
            "拉升": f"检测到拉升特征({probabilities.get('拉升', 0)}%)，走势较强，可考虑顺势而为",
        }

        base_advice = advice_map.get(dominant, "建议观望")

        # 添加风险提示
        if probabilities.get("出货", 0) > 40:
            base_advice += "\n[注意] 出货概率较高，请谨慎操作"
        elif probabilities.get("拉升", 0) > 40:
            base_advice += "\n[提示] 走势较强，可考虑顺势而为"

        return base_advice

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

    # 时间段分析
    segments = analysis.get("segments", {})
    if segments:
        lines.append(f"\n【时间段分析】")
        for seg_name, seg_data in segments.items():
            vol_ratio = seg_data.get("volume_ratio", 0)
            vol_indicator = "放量" if vol_ratio > 1.2 else ("缩量" if vol_ratio < 0.8 else "正常")
            lines.append(f"  {seg_name}: {seg_data.get('change_pct', 'N/A')}% {vol_indicator}量比{seg_data.get('volume_ratio', 'N/A')}")

    # 量价关系
    pv = analysis.get("price_volume", {})
    if pv:
        lines.append(f"\n【量价关系】")
        corr = pv.get("correlation", 0)
        corr_desc = "正相关" if corr > 0.3 else ("负相关" if corr < -0.3 else "弱相关")
        lines.append(f"  量价相关性: {corr} ({corr_desc})")
        main_pattern = pv.get("volume_price_pattern", {}).get("main_pattern", "normal")
        lines.append(f"  主要形态: {main_pattern}")

    # 主力行为
    inst = analysis.get("institutional", {})
    if inst and "error" not in inst:
        probs = inst.get("probabilities", {})
        lines.append(f"\n【主力行为分析】")
        for behavior, prob in probs.items():
            bar = "█" * int(prob / 10)
            lines.append(f"  {behavior}: {prob}% {bar}")
        lines.append(f"\n  综合判断: {inst.get('dominant_behavior', 'N/A')}")
        lines.append(f"\n  >> {inst.get('advice', 'N/A')}")

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
