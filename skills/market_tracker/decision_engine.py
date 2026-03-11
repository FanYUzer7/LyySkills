"""
市场跟踪器 - 综合决策引擎
Layer 1: 基于经典技术指标的规则信号
Layer 2: 基于量化因子的评分（借鉴 AlphaGPT 思路，numpy/pandas 实现）
综合两层信号得出最终投资决策
"""

import numpy as np
import pandas as pd

from . import indicators as ind
from .config import (
    INDICATOR_PARAMS, SIGNAL_WEIGHTS, FACTOR_WEIGHTS,
    LAYER_WEIGHTS, DECISION_THRESHOLDS, FACTOR_PARAMS,
    RSI_OVERBOUGHT, RSI_OVERSOLD, ADX_TREND_THRESHOLD,
)


# ==============================================================
# Layer 1: 技术信号生成器
# ==============================================================

class TechnicalSignalGenerator:
    """
    基于经典技术指标生成交易信号。
    每个指标输出: signal (-1=看空, 0=中性, +1=看多) + confidence (0~1)
    """

    def __init__(self, params: dict = None):
        self.params = params or INDICATOR_PARAMS

    def generate(self, df: pd.DataFrame) -> dict[str, dict]:
        """
        输入 K线 DataFrame (含 close, high, low, volume)。
        返回各指标信号: {"ma_alignment": {"signal": 1, "confidence": 0.8, "detail": "..."}, ...}
        """
        indicators = ind.compute_all_indicators(df, self.params)
        close = df["close"].astype(float)
        vol = df["volume"].astype(float)

        signals = {}
        signals["ma_alignment"] = self._ma_signal(indicators, close)
        signals["macd_cross"] = self._macd_signal(indicators)
        signals["rsi"] = self._rsi_signal(indicators)
        signals["kdj"] = self._kdj_signal(indicators)
        signals["bollinger"] = self._bollinger_signal(indicators, close)
        signals["adx_trend"] = self._adx_signal(indicators)
        signals["volume_price"] = self._volume_price_signal(indicators, close, vol)

        return signals

    def _ma_signal(self, ind_data: dict, close: pd.Series) -> dict:
        """均线多空排列信号"""
        ma5 = ind_data.get("sma_5")
        ma20 = ind_data.get("sma_20")
        ma60 = ind_data.get("sma_60")
        if ma5 is None or ma20 is None or ma60 is None:
            return {"signal": 0, "confidence": 0, "detail": "数据不足"}

        latest = -1
        ma5_v, ma20_v, ma60_v = ma5.iloc[latest], ma20.iloc[latest], ma60.iloc[latest]
        close_v = close.iloc[latest]

        if ma5_v > ma20_v > ma60_v and close_v > ma5_v:
            return {"signal": 1, "confidence": 0.85,
                    "detail": f"⬆️ 多头排列 (MA5={ma5_v:.2f}>MA20={ma20_v:.2f}>MA60={ma60_v:.2f})"}
        elif ma5_v < ma20_v < ma60_v and close_v < ma5_v:
            return {"signal": -1, "confidence": 0.85,
                    "detail": f"⬇️ 空头排列 (MA5={ma5_v:.2f}<MA20={ma20_v:.2f}<MA60={ma60_v:.2f})"}
        elif ma5_v > ma20_v:
            # 金叉但未完全多头
            return {"signal": 0.5, "confidence": 0.5,
                    "detail": f"↗️ MA5上穿MA20, 短期偏多"}
        elif ma5_v < ma20_v:
            return {"signal": -0.5, "confidence": 0.5,
                    "detail": f"↘️ MA5下穿MA20, 短期偏空"}
        else:
            return {"signal": 0, "confidence": 0.3, "detail": "均线纠缠, 方向不明"}

    def _macd_signal(self, ind_data: dict) -> dict:
        """MACD 金叉/死叉信号"""
        dif = ind_data.get("macd_dif")
        dea = ind_data.get("macd_dea")
        hist = ind_data.get("macd_hist")
        if dif is None or dea is None:
            return {"signal": 0, "confidence": 0, "detail": "数据不足"}

        dif_v = dif.iloc[-1]
        dea_v = dea.iloc[-1]
        hist_v = hist.iloc[-1]
        hist_prev = hist.iloc[-2] if len(hist) > 1 else 0

        # 金叉: DIF 从下方穿越 DEA
        if dif_v > dea_v and dif.iloc[-2] <= dea.iloc[-2] if len(dif) > 1 else False:
            return {"signal": 1, "confidence": 0.8,
                    "detail": f"🟢 金叉 (DIF={dif_v:.4f}, DEA={dea_v:.4f})"}
        # 死叉
        elif dif_v < dea_v and (dif.iloc[-2] >= dea.iloc[-2] if len(dif) > 1 else False):
            return {"signal": -1, "confidence": 0.8,
                    "detail": f"🔴 死叉 (DIF={dif_v:.4f}, DEA={dea_v:.4f})"}
        # 柱状图放大（多头延续）
        elif hist_v > 0 and hist_v > hist_prev:
            return {"signal": 0.6, "confidence": 0.6,
                    "detail": f"🟢 多头延续, 柱状图放大"}
        elif hist_v < 0 and hist_v < hist_prev:
            return {"signal": -0.6, "confidence": 0.6,
                    "detail": f"🔴 空头延续, 柱状图放大"}
        elif hist_v > 0:
            return {"signal": 0.3, "confidence": 0.4, "detail": "MACD 零轴上方"}
        elif hist_v < 0:
            return {"signal": -0.3, "confidence": 0.4, "detail": "MACD 零轴下方"}
        else:
            return {"signal": 0, "confidence": 0.2, "detail": "MACD 中性"}

    def _rsi_signal(self, ind_data: dict) -> dict:
        """RSI 超买超卖信号"""
        rsi_14 = ind_data.get("rsi_14")
        if rsi_14 is None or rsi_14.empty:
            return {"signal": 0, "confidence": 0, "detail": "数据不足"}

        val = rsi_14.iloc[-1]
        if np.isnan(val):
            return {"signal": 0, "confidence": 0, "detail": "RSI 计算中"}

        if val > RSI_OVERBOUGHT:
            strength = min((val - RSI_OVERBOUGHT) / 30, 1.0)
            return {"signal": -1, "confidence": 0.6 + 0.3 * strength,
                    "detail": f"⚠️ RSI={val:.1f} 超买区"}
        elif val < RSI_OVERSOLD:
            strength = min((RSI_OVERSOLD - val) / 30, 1.0)
            return {"signal": 1, "confidence": 0.6 + 0.3 * strength,
                    "detail": f"💡 RSI={val:.1f} 超卖区"}
        elif val > 50:
            return {"signal": 0.3, "confidence": 0.4,
                    "detail": f"RSI={val:.1f} 中性偏多"}
        elif val < 50:
            return {"signal": -0.3, "confidence": 0.4,
                    "detail": f"RSI={val:.1f} 中性偏空"}
        else:
            return {"signal": 0, "confidence": 0.3, "detail": f"RSI={val:.1f} 中性"}

    def _kdj_signal(self, ind_data: dict) -> dict:
        """KDJ 交叉与极端信号"""
        k = ind_data.get("kdj_k")
        d = ind_data.get("kdj_d")
        j = ind_data.get("kdj_j")
        if k is None or d is None or j is None:
            return {"signal": 0, "confidence": 0, "detail": "数据不足"}

        k_v, d_v, j_v = k.iloc[-1], d.iloc[-1], j.iloc[-1]

        if j_v > 100:
            return {"signal": -0.8, "confidence": 0.7,
                    "detail": f"⚠️ J={j_v:.1f}>100 超买极端"}
        elif j_v < 0:
            return {"signal": 0.8, "confidence": 0.7,
                    "detail": f"💡 J={j_v:.1f}<0 超卖极端"}
        elif k_v > d_v and (k.iloc[-2] <= d.iloc[-2] if len(k) > 1 else False):
            return {"signal": 1, "confidence": 0.7,
                    "detail": f"🟢 KDJ金叉 (K={k_v:.1f}, D={d_v:.1f}, J={j_v:.1f})"}
        elif k_v < d_v and (k.iloc[-2] >= d.iloc[-2] if len(k) > 1 else False):
            return {"signal": -1, "confidence": 0.7,
                    "detail": f"🔴 KDJ死叉 (K={k_v:.1f}, D={d_v:.1f}, J={j_v:.1f})"}
        elif k_v > d_v:
            return {"signal": 0.3, "confidence": 0.4,
                    "detail": f"KDJ偏多 (K={k_v:.1f}, D={d_v:.1f}, J={j_v:.1f})"}
        else:
            return {"signal": -0.3, "confidence": 0.4,
                    "detail": f"KDJ偏空 (K={k_v:.1f}, D={d_v:.1f}, J={j_v:.1f})"}

    def _bollinger_signal(self, ind_data: dict, close: pd.Series) -> dict:
        """布林带位置信号"""
        upper = ind_data.get("bb_upper")
        lower = ind_data.get("bb_lower")
        mid = ind_data.get("bb_middle")
        bw = ind_data.get("bb_bandwidth")
        if upper is None or lower is None:
            return {"signal": 0, "confidence": 0, "detail": "数据不足"}

        c = close.iloc[-1]
        u, l, m = upper.iloc[-1], lower.iloc[-1], mid.iloc[-1]
        bw_v = bw.iloc[-1] if bw is not None else 0

        if c > u:
            return {"signal": -0.7, "confidence": 0.65,
                    "detail": f"⚠️ 突破上轨({u:.2f}), 注意回调"}
        elif c < l:
            return {"signal": 0.7, "confidence": 0.65,
                    "detail": f"💡 跌破下轨({l:.2f}), 关注反弹"}
        elif c > m:
            pct = (c - m) / (u - m) if u != m else 0
            return {"signal": 0.3 * pct, "confidence": 0.4,
                    "detail": f"中轨上方, 带宽={bw_v:.4f}"}
        else:
            pct = (m - c) / (m - l) if m != l else 0
            return {"signal": -0.3 * pct, "confidence": 0.4,
                    "detail": f"中轨下方, 带宽={bw_v:.4f}"}

    def _adx_signal(self, ind_data: dict) -> dict:
        """ADX 趋势强度信号"""
        adx_val = ind_data.get("adx")
        plus_di = ind_data.get("plus_di")
        minus_di = ind_data.get("minus_di")
        if adx_val is None:
            return {"signal": 0, "confidence": 0, "detail": "数据不足"}

        adx_v = adx_val.iloc[-1]
        p_di = plus_di.iloc[-1] if plus_di is not None else 0
        m_di = minus_di.iloc[-1] if minus_di is not None else 0

        if adx_v < ADX_TREND_THRESHOLD:
            return {"signal": 0, "confidence": 0.5,
                    "detail": f"ADX={adx_v:.1f} 无明显趋势 (震荡市)"}

        # ADX > 25 → 有效趋势
        if p_di > m_di:
            return {"signal": 0.7, "confidence": 0.7,
                    "detail": f"ADX={adx_v:.1f} 有效上升趋势 (+DI={p_di:.1f}>-DI={m_di:.1f})"}
        else:
            return {"signal": -0.7, "confidence": 0.7,
                    "detail": f"ADX={adx_v:.1f} 有效下降趋势 (-DI={m_di:.1f}>+DI={p_di:.1f})"}

    def _volume_price_signal(self, ind_data: dict,
                             close: pd.Series, volume: pd.Series) -> dict:
        """量价配合信号"""
        vol_ma = ind_data.get("volume_ma")
        if vol_ma is None:
            return {"signal": 0, "confidence": 0, "detail": "数据不足"}

        price_chg = close.pct_change().iloc[-1]
        vol_ratio = volume.iloc[-1] / vol_ma.iloc[-1] if vol_ma.iloc[-1] > 0 else 1

        if price_chg > 0 and vol_ratio > 1.5:
            return {"signal": 0.8, "confidence": 0.75,
                    "detail": f"🔥 放量上涨 (量比={vol_ratio:.2f})"}
        elif price_chg < 0 and vol_ratio > 1.5:
            return {"signal": -0.8, "confidence": 0.75,
                    "detail": f"⚠️ 放量下跌 (量比={vol_ratio:.2f})"}
        elif price_chg > 0 and vol_ratio < 0.7:
            return {"signal": -0.2, "confidence": 0.4,
                    "detail": f"缩量上涨 (量比={vol_ratio:.2f}), 上涨动力不足"}
        elif price_chg < 0 and vol_ratio < 0.7:
            return {"signal": 0.2, "confidence": 0.4,
                    "detail": f"缩量下跌 (量比={vol_ratio:.2f}), 抛压减轻"}
        else:
            return {"signal": 0, "confidence": 0.3,
                    "detail": f"量价正常 (量比={vol_ratio:.2f})"}


# ==============================================================
# Layer 2: 量化因子评分
# ==============================================================

class FactorScorer:
    """
    基于量化因子的评分系统。
    借鉴 AlphaGPT 的因子构造思路，使用 numpy/pandas 实现。
    - 动量因子: 多周期收益率
    - 波动因子: 特异波动率、最大回撤
    - 量价因子: 量价相关性
    """

    def __init__(self, params: dict = None):
        self.params = params or FACTOR_PARAMS

    def score(self, df: pd.DataFrame) -> dict:
        """
        计算各维度因子得分。
        输入 K线 DataFrame。
        返回: {"momentum": {"score": 0.5, "detail": ...}, ...}
        """
        close = df["close"].astype(float)
        volume = df["volume"].astype(float)

        momentum = self._momentum_score(close)
        volatility = self._volatility_score(close)
        vol_price = self._volume_price_score(close, volume)

        return {
            "momentum": momentum,
            "volatility": volatility,
            "volume_price": vol_price,
        }

    def composite_score(self, factor_scores: dict) -> float:
        """综合因子得分 (加权平均, 输出 -1 ~ +1)"""
        total = 0
        for name, weight in FACTOR_WEIGHTS.items():
            s = factor_scores.get(name, {}).get("score", 0)
            total += s * weight
        return np.clip(total, -1, 1)

    def _momentum_score(self, close: pd.Series) -> dict:
        """动量因子: 多周期收益率的标准化加权"""
        windows = self.params.get("momentum_windows", [20, 60, 120])
        scores = []
        details = []
        for w in windows:
            if len(close) < w + 1:
                continue
            ret = (close.iloc[-1] / close.iloc[-w] - 1)
            # Z-Score 标准化 (简化: 使用 tanh 映射到 -1~1)
            z = np.tanh(ret * 5)  # 放大后 tanh 压缩
            scores.append(z)
            details.append(f"{w}日收益={ret:.2%}")

        if not scores:
            return {"score": 0, "detail": "数据不足"}

        avg_score = float(np.mean(scores))
        return {"score": np.clip(avg_score, -1, 1),
                "detail": "; ".join(details)}

    def _volatility_score(self, close: pd.Series) -> dict:
        """波动因子: 波动率高→-分, 低→+分; 回撤大→-分"""
        window = self.params.get("volatility_window", 20)
        if len(close) < window + 1:
            return {"score": 0, "detail": "数据不足"}

        hv = ind.historical_volatility(close, window).iloc[-1]
        mdd = ind.max_drawdown(close.tail(window))

        # 波动率越低越好 (0.2为中性基准，年化20%)
        vol_score = np.tanh((0.2 - hv) * 3) if not np.isnan(hv) else 0
        # 回撤越小越好
        dd_score = np.tanh((mdd + 0.05) * 5)  # mdd 是负数

        combined = 0.5 * vol_score + 0.5 * dd_score
        return {"score": float(np.clip(combined, -1, 1)),
                "detail": f"波动率={hv:.2%}, 近{window}日最大回撤={mdd:.2%}"}

    def _volume_price_score(self, close: pd.Series,
                            volume: pd.Series) -> dict:
        """量价因子: 量价正相关（放量涨）→正分"""
        window = self.params.get("volume_corr_window", 20)
        if len(close) < window + 1:
            return {"score": 0, "detail": "数据不足"}

        price_ret = close.pct_change().tail(window)
        vol_chg = volume.pct_change().tail(window)

        # 量价相关性
        corr = price_ret.corr(vol_chg)
        if np.isnan(corr):
            corr = 0

        # 近期量能趋势
        vol_trend = (volume.tail(5).mean() / volume.tail(window).mean() - 1
                     if volume.tail(window).mean() > 0 else 0)

        score = np.tanh(corr + vol_trend * 0.5)
        return {"score": float(np.clip(score, -1, 1)),
                "detail": f"量价相关性={corr:.3f}, 量能趋势={vol_trend:+.2%}"}


# ==============================================================
# 综合决策
# ==============================================================

class InvestmentDecision:
    """综合 Layer1 + Layer2，输出最终投资决策"""

    def __init__(self):
        self.signal_gen = TechnicalSignalGenerator()
        self.factor_scorer = FactorScorer()

    def analyze(self, df: pd.DataFrame, quote: dict = None) -> dict:
        """
        对单个标的进行完整分析。
        :param df: 历史K线 DataFrame
        :param quote: 实时行情 dict (可选)
        :return: 完整决策报告 dict
        """
        if df is None or df.empty or len(df) < 20:
            return {"error": "历史数据不足（至少需要20个交易日）"}

        # Layer 1: 技术信号
        tech_signals = self.signal_gen.generate(df)

        # Layer 2: 因子评分
        factor_scores = self.factor_scorer.score(df)
        composite = self.factor_scorer.composite_score(factor_scores)

        # 综合
        tech_score = self._weighted_tech_score(tech_signals)
        final_score = (
            tech_score * LAYER_WEIGHTS["technical_signal"]
            + composite * LAYER_WEIGHTS["factor_score"]
        )

        # 决策
        action = self._score_to_action(final_score)

        # 支撑/阻力位 & ATR 止损/止盈
        sr = self._support_resistance(df)

        # 市场状态判断
        market_state = self._detect_market_state(df, tech_signals)

        # 风险评估
        risk = self._risk_assessment(df)

        return {
            "technical_signals": tech_signals,
            "factor_scores": factor_scores,
            "composite_factor_score": composite,
            "technical_score": tech_score,
            "final_score": final_score,
            "action": action,
            "support": sr["support"],
            "resistance": sr["resistance"],
            "stop_loss": sr["stop_loss"],
            "take_profit": sr["take_profit"],
            "market_state": market_state,
            "risk": risk,
            "quote": quote,
        }

    def _weighted_tech_score(self, signals: dict) -> float:
        """计算加权技术信号总分"""
        total = 0
        w_sum = 0
        for name, weight in SIGNAL_WEIGHTS.items():
            sig = signals.get(name, {})
            s = sig.get("signal", 0)
            c = sig.get("confidence", 0)
            total += s * c * weight
            w_sum += weight
        return total / w_sum if w_sum > 0 else 0

    def _score_to_action(self, score: float) -> dict:
        """将综合得分映射为操作建议"""
        t = DECISION_THRESHOLDS
        if score >= t["strong_buy"]:
            return {"action": "强烈买入", "emoji": "🟢🟢",
                    "confidence": min(abs(score), 1),
                    "position_pct": "80-100%"}
        elif score >= t["buy"]:
            return {"action": "买入/加仓", "emoji": "🟢",
                    "confidence": min(abs(score), 1),
                    "position_pct": "50-70%"}
        elif score >= t["hold_lower"]:
            if score > 0:
                return {"action": "持有观望", "emoji": "🟡",
                        "confidence": 0.5,
                        "position_pct": "维持当前"}
            else:
                return {"action": "持有观望", "emoji": "🟡",
                        "confidence": 0.5,
                        "position_pct": "维持或减仓"}
        elif score >= t["strong_sell"]:
            return {"action": "卖出/减仓", "emoji": "🔴",
                    "confidence": min(abs(score), 1),
                    "position_pct": "30-50%"}
        else:
            return {"action": "强烈卖出", "emoji": "🔴🔴",
                    "confidence": min(abs(score), 1),
                    "position_pct": "0-20%"}

    def _support_resistance(self, df: pd.DataFrame) -> dict:
        """支撑/阻力位识别 + ATR 动态止损/止盈"""
        close = df["close"].astype(float)
        low = df["low"].astype(float)
        high = df["high"].astype(float)

        lookback = min(20, len(df))
        support = float(low.tail(lookback).min())
        resistance = float(high.tail(lookback).max())

        # ATR 动态止损/止盈
        atr_val = ind.atr(high, low, close).iloc[-1]
        last_close = float(close.iloc[-1])
        if np.isnan(atr_val):
            atr_val = 0
        stop_loss = last_close - 2 * atr_val
        take_profit = last_close + 3 * atr_val

        return {
            "support": support,
            "resistance": resistance,
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2),
            "atr": round(float(atr_val), 2),
        }

    def _detect_market_state(self, df: pd.DataFrame,
                             signals: dict) -> str:
        """判断当前市场状态: 趋势/震荡"""
        adx_sig = signals.get("adx_trend", {})
        adx_detail = adx_sig.get("detail", "")
        if "无明显趋势" in adx_detail or "震荡" in adx_detail:
            return "震荡市"

        bb_bw = ind.bollinger_bands(df["close"].astype(float))[3]
        if bb_bw.iloc[-1] < bb_bw.rolling(60, min_periods=1).mean().iloc[-1]:
            return "波动率收缩（可能变盘）"

        ma_sig = signals.get("ma_alignment", {}).get("signal", 0)
        if ma_sig > 0:
            return "上升趋势"
        elif ma_sig < 0:
            return "下降趋势"
        return "方向不明"

    def _risk_assessment(self, df: pd.DataFrame) -> dict:
        """风险评估"""
        close = df["close"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)

        atr_val = ind.atr(high, low, close).iloc[-1]
        hv = ind.historical_volatility(close).iloc[-1]
        mdd_20 = ind.max_drawdown(close.tail(20))

        # 波动率等级
        if hv < 0.15:
            vol_level = "低"
        elif hv < 0.30:
            vol_level = "中等"
        elif hv < 0.50:
            vol_level = "偏高"
        else:
            vol_level = "极高"

        warnings = []
        rsi_14 = ind.rsi(close, 14).iloc[-1]
        if rsi_14 > 75:
            warnings.append(f"RSI={rsi_14:.1f} 深度超买, 注意回调风险")
        elif rsi_14 > RSI_OVERBOUGHT:
            warnings.append(f"RSI={rsi_14:.1f} 接近超买区, 注意短期回调")

        if mdd_20 < -0.10:
            warnings.append(f"近20日回撤={mdd_20:.1%}, 已有较大下跌")

        return {
            "atr": float(atr_val) if not np.isnan(atr_val) else 0,
            "volatility": float(hv) if not np.isnan(hv) else 0,
            "volatility_level": vol_level,
            "max_drawdown_20d": float(mdd_20),
            "warnings": warnings,
        }
