"""
市场跟踪器 - 综合决策引擎
Layer 1: 基于经典技术指标的规则信号
Layer 2: 基于量化因子的评分（借鉴 AlphaGPT 思路，numpy/pandas 实现）
综合两层信号得出最终投资决策
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd

import indicators as ind
import config

INDICATOR_PARAMS = config.INDICATOR_PARAMS
SIGNAL_WEIGHTS = config.SIGNAL_WEIGHTS
FACTOR_WEIGHTS = config.FACTOR_WEIGHTS
LAYER_WEIGHTS = config.LAYER_WEIGHTS
DECISION_THRESHOLDS = config.DECISION_THRESHOLDS
FACTOR_PARAMS = config.FACTOR_PARAMS
RSI_OVERBOUGHT = config.RSI_OVERBOUGHT
RSI_OVERSOLD = config.RSI_OVERSOLD
ADX_TREND_THRESHOLD = config.ADX_TREND_THRESHOLD


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

        # 新增指标信号
        signals["supertrend"] = self._supertrend_signal(indicators, close)
        signals["sar"] = self._sar_signal(indicators, close)
        signals["ichimoku"] = self._ichimoku_signal(indicators, close)
        signals["stochastic"] = self._stochastic_signal(indicators)
        signals["williams_r"] = self._williams_signal(indicators)
        signals["keltner"] = self._keltner_signal(indicators, close)
        signals["donchian"] = self._donchian_signal(indicators, close)

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
        # 使用配置的RSI周期，默认14
        rsi_periods = self.params.get("rsi_periods", [14])
        # 优先使用14周期（行业标准），否则用配置的第一个
        rsi_period = 14 if 14 in rsi_periods else rsi_periods[0]
        rsi_val = ind_data.get(f"rsi_{rsi_period}")
        if rsi_val is None or rsi_val.empty:
            return {"signal": 0, "confidence": 0, "detail": "数据不足"}

        val = rsi_val.iloc[-1]
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

    # ============================================================
    # 新增指标信号
    # ============================================================
    def _supertrend_signal(self, ind_data: dict, close: pd.Series) -> dict:
        """SuperTrend 趋势信号"""
        st_line = ind_data.get("supertrend_line")
        st_dir = ind_data.get("supertrend_direction")
        if st_line is None or st_dir is None:
            return {"signal": 0, "confidence": 0, "detail": "数据不足"}

        c = close.iloc[-1]
        st = st_line.iloc[-1]
        direction = st_dir.iloc[-1] if hasattr(st_dir, 'iloc') else st_dir

        if direction == 1:  # 上升趋势
            return {"signal": 0.7, "confidence": 0.7,
                    "detail": f"ST上升趋势 (价格={c:.2f}, ST线={st:.2f})"}
        elif direction == -1:  # 下降趋势
            return {"signal": -0.7, "confidence": 0.7,
                    "detail": f"ST下降趋势 (价格={c:.2f}, ST线={st:.2f})"}
        else:
            return {"signal": 0, "confidence": 0.3, "detail": "ST趋势不明"}

    def _sar_signal(self, ind_data: dict, close: pd.Series) -> dict:
        """SAR 抛物线转向信号"""
        sar_val = ind_data.get("sar")
        if sar_val is None:
            return {"signal": 0, "confidence": 0, "detail": "数据不足"}

        c = close.iloc[-1]
        s = sar_val.iloc[-1]

        if c > s:
            return {"signal": 0.6, "confidence": 0.65,
                    "detail": f"价格({c:.2f})在SAR({s:.2f})上方, 看多"}
        else:
            return {"signal": -0.6, "confidence": 0.65,
                    "detail": f"价格({c:.2f})在SAR({s:.2f})下方, 看空"}

    def _ichimoku_signal(self, ind_data: dict, close: pd.Series) -> dict:
        """Ichimoku 云图信号"""
        ichimoku = ind_data.get("ichimoku")
        if ichimoku is None:
            return {"signal": 0, "confidence": 0, "detail": "数据不足"}

        try:
            tenkan, kijun, senkou_a, senkou_b, chikou = ichimoku
            c = close.iloc[-1]

            # 简化的云图信号：价格与云的关系
            if tenkan is None or kijun is None:
                return {"signal": 0, "confidence": 0, "detail": "数据不足"}

            tk = tenkan.iloc[-1]
            kj = kijun.iloc[-1]

            # 基准线与转换线金叉/死叉
            if tk > kj:
                return {"signal": 0.5, "confidence": 0.5,
                        "detail": f"云图偏多 (T={tk:.2f}>K={kj:.2f})"}
            else:
                return {"signal": -0.5, "confidence": 0.5,
                        "detail": f"云图偏空 (T={tk:.2f}<K={kj:.2f})"}
        except:
            return {"signal": 0, "confidence": 0, "detail": "数据不足"}

    def _stochastic_signal(self, ind_data: dict) -> dict:
        """Stochastic 随机指标信号"""
        stoch_k = ind_data.get("stoch_k")
        stoch_d = ind_data.get("stoch_d")
        if stoch_k is None or stoch_d is None:
            return {"signal": 0, "confidence": 0, "detail": "数据不足"}

        k = stoch_k.iloc[-1]
        d = stoch_d.iloc[-1]

        if k > 80:
            return {"signal": -0.6, "confidence": 0.6,
                    "detail": f"随机指标超买 K={k:.1f}"}
        elif k < 20:
            return {"signal": 0.6, "confidence": 0.6,
                    "detail": f"随机指标超卖 K={k:.1f}"}
        elif k > d and len(stoch_k) > 1 and stoch_k.iloc[-2] <= stoch_d.iloc[-2]:
            return {"signal": 0.7, "confidence": 0.6,
                    "detail": f"随机指标金叉 (K={k:.1f}, D={d:.1f})"}
        elif k < d and len(stoch_k) > 1 and stoch_k.iloc[-2] >= stoch_d.iloc[-2]:
            return {"signal": -0.7, "confidence": 0.6,
                    "detail": f"随机指标死叉 (K={k:.1f}, D={d:.1f})"}
        elif k > d:
            return {"signal": 0.3, "confidence": 0.4,
                    "detail": f"随机指标偏多 (K={k:.1f}, D={d:.1f})"}
        else:
            return {"signal": -0.3, "confidence": 0.4,
                    "detail": f"随机指标偏空 (K={k:.1f}, D={d:.1f})"}

    def _williams_signal(self, ind_data: dict) -> dict:
        """Williams %R 威廉指标信号"""
        williams = ind_data.get("williams_r")
        if williams is None:
            return {"signal": 0, "confidence": 0, "detail": "数据不足"}

        w = williams.iloc[-1]

        if w > -20:
            return {"signal": -0.7, "confidence": 0.6,
                    "detail": f"威廉指标超买 W%R={w:.1f}"}
        elif w < -80:
            return {"signal": 0.7, "confidence": 0.6,
                    "detail": f"威廉指标超卖 W%R={w:.1f}"}
        elif w > -50:
            return {"signal": -0.3, "confidence": 0.4,
                    "detail": f"威廉指标偏空 W%R={w:.1f}"}
        else:
            return {"signal": 0.3, "confidence": 0.4,
                    "detail": f"威廉指标偏多 W%R={w:.1f}"}

    def _keltner_signal(self, ind_data: dict, close: pd.Series) -> dict:
        """Keltner Channel 肯特纳通道信号"""
        kc_mid = ind_data.get("kc_middle")
        kc_upper = ind_data.get("kc_upper")
        kc_lower = ind_data.get("kc_lower")
        if kc_mid is None or kc_upper is None:
            return {"signal": 0, "confidence": 0, "detail": "数据不足"}

        c = close.iloc[-1]
        upper = kc_upper.iloc[-1]
        lower = kc_lower.iloc[-1]

        if c > upper:
            return {"signal": -0.6, "confidence": 0.6,
                    "detail": f"突破KC上轨, 注意回调"}
        elif c < lower:
            return {"signal": 0.6, "confidence": 0.6,
                    "detail": f"跌破KC下轨, 关注反弹"}
        else:
            mid = kc_mid.iloc[-1]
            pct = (c - lower) / (upper - lower) if upper != lower else 0.5
            signal = (pct - 0.5) * 0.4
            return {"signal": signal, "confidence": 0.4,
                    "detail": f"KC通道内运行, 震荡整理"}

    def _donchian_signal(self, ind_data: dict, close: pd.Series) -> dict:
        """Donchian Channel 唐奇安通道信号"""
        dc_upper = ind_data.get("donchian_upper")
        dc_lower = ind_data.get("donchian_lower")
        if dc_upper is None or dc_lower is None:
            return {"signal": 0, "confidence": 0, "detail": "数据不足"}

        c = close.iloc[-1]
        upper = dc_upper.iloc[-1]
        lower = dc_lower.iloc[-1]

        if c >= upper:
            return {"signal": 0.7, "confidence": 0.65,
                    "detail": f"突破DC上轨, 强势上涨"}
        elif c <= lower:
            return {"signal": -0.7, "confidence": 0.65,
                    "detail": f"跌破DC下轨, 强势下跌"}
        else:
            pct = (c - lower) / (upper - lower) if upper != lower else 0.5
            signal = (pct - 0.5) * 0.4
            return {"signal": signal, "confidence": 0.4,
                    "detail": f"DC通道内, 观望为主"}


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

    def __init__(self, indicator_params: dict = None):
        self.signal_gen = TechnicalSignalGenerator(indicator_params)
        self.factor_scorer = FactorScorer()

    def analyze(self, df: pd.DataFrame, quote: dict = None,
                minute_df: pd.DataFrame = None) -> dict:
        """
        对单个标的进行完整分析。
        :param df: 历史K线 DataFrame
        :param quote: 实时行情 dict (可选)
        :param minute_df: 分时数据 DataFrame (可选)
        :return: 完整决策报告 dict
        """
        if df is None or df.empty or len(df) < 20:
            return {"error": "历史数据不足（至少需要20个交易日）"}

        # Layer 1: 技术信号
        tech_signals = self.signal_gen.generate(df)

        # Layer 2: 因子评分
        factor_scores = self.factor_scorer.score(df)
        composite = self.factor_scorer.composite_score(factor_scores)

        # Layer 3: 分时行为分析（可选）
        institutional_score = 0
        institutional_analysis = None
        if minute_df is not None and not minute_df.empty:
            try:
                import minute_analyzer as ma
                analyzer = ma.MinuteAnalyzer("", "")
                analyzer.data = minute_df
                # 只取行为分析部分
                inst_result = analyzer._analyze_institutional(minute_df)
                if inst_result and "probabilities" in inst_result:
                    probs = inst_result["probabilities"]
                    # 将概率转换为得分
                    # 吸筹/拉升 -> 正分，出货 -> 负分
                    institutional_score = (
                        probs.get("吸筹", 0) / 100 * 0.3 +
                        probs.get("拉升", 0) / 100 * 0.5 -
                        probs.get("出货", 0) / 100 * 0.5
                    )
                    institutional_analysis = inst_result
            except Exception:
                pass  # 分时分析失败不影响主流程

        # 综合
        tech_score = self._weighted_tech_score(tech_signals)

        # 如果有分时数据，调整最终得分
        if minute_df is not None and not minute_df.empty:
            # 分时行为分析权重 15%
            final_score = (
                tech_score * LAYER_WEIGHTS["technical_signal"] * 0.85
                + composite * LAYER_WEIGHTS["factor_score"] * 0.85
                + institutional_score * 0.15
            )
        else:
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
            "institutional_analysis": institutional_analysis,
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
