"""
市场跟踪器 - 技术指标计算库
纯 numpy/pandas 实现，覆盖趋势/动量/成交量/波动率四大类指标
参考 knowledge.md 中的指标体系
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd


# ==============================================================
# 趋势类指标
# ==============================================================

def sma(series: pd.Series, period: int) -> pd.Series:
    """简单移动平均线"""
    return series.rolling(window=period, min_periods=1).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """指数移动平均线"""
    return series.ewm(span=period, adjust=False).mean()


def macd(close: pd.Series, fast: int = 12, slow: int = 26,
         signal: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    MACD 指标
    返回: (DIF, DEA, Histogram)
    DIF = EMA(fast) - EMA(slow)
    DEA = EMA(DIF, signal)
    Histogram = 2 * (DIF - DEA)
    """
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    dif = ema_fast - ema_slow
    dea = ema(dif, signal)
    hist = 2 * (dif - dea)
    return dif, dea, hist


def bollinger_bands(close: pd.Series, period: int = 20,
                    std_mult: float = 2.0
                    ) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """
    布林带
    返回: (upper, middle, lower, bandwidth)
    bandwidth = (upper - lower) / middle
    """
    middle = sma(close, period)
    std = close.rolling(window=period, min_periods=1).std()
    upper = middle + std_mult * std
    lower = middle - std_mult * std
    bandwidth = (upper - lower) / middle.replace(0, np.nan)
    return upper, middle, lower, bandwidth


def adx(high: pd.Series, low: pd.Series, close: pd.Series,
        period: int = 14) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    ADX/DI 系统
    返回: (ADX, +DI, -DI)
    ADX > 25 表示有效趋势
    """
    # True Range
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Directional Movement
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low

    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0),
                                  up_move, 0.0), index=high.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0),
                                   down_move, 0.0), index=high.index)

    # Wilder 平滑
    atr_val = _wilder_smooth(tr, period)
    plus_di = 100 * _wilder_smooth(plus_dm, period) / atr_val.replace(0, np.nan)
    minus_di = 100 * _wilder_smooth(minus_dm, period) / atr_val.replace(0, np.nan)

    # ADX
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx_val = _wilder_smooth(dx, period)

    return adx_val, plus_di, minus_di


# ==============================================================
# 动量类指标
# ==============================================================

def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """
    RSI (Relative Strength Index)
    RSI = 100 - 100/(1+RS), RS = avg_gain / avg_loss
    """
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = _wilder_smooth(gain, period)
    avg_loss = _wilder_smooth(loss, period)
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def kdj(high: pd.Series, low: pd.Series, close: pd.Series,
        n: int = 9, m1: int = 3, m2: int = 3
        ) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    KDJ 指标
    返回: (K, D, J)
    J > 100 或 J < 0 为极端信号
    """
    lowest_low = low.rolling(window=n, min_periods=1).min()
    highest_high = high.rolling(window=n, min_periods=1).max()
    rsv = 100 * (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
    rsv = rsv.fillna(50)

    k = pd.Series(np.nan, index=close.index, dtype=float)
    d = pd.Series(np.nan, index=close.index, dtype=float)

    k.iloc[0] = 50.0
    d.iloc[0] = 50.0
    for i in range(1, len(close)):
        k.iloc[i] = (m1 - 1) / m1 * k.iloc[i - 1] + 1 / m1 * rsv.iloc[i]
        d.iloc[i] = (m2 - 1) / m2 * d.iloc[i - 1] + 1 / m2 * k.iloc[i]

    j = 3 * k - 2 * d
    return k, d, j


def cci(high: pd.Series, low: pd.Series, close: pd.Series,
        period: int = 20) -> pd.Series:
    """
    CCI (Commodity Channel Index)
    CCI = (TP - SMA(TP)) / (0.015 * Mean Deviation)
    ±100 为强弱分界
    """
    tp = (high + low + close) / 3
    sma_tp = sma(tp, period)
    mean_dev = tp.rolling(window=period, min_periods=1).apply(
        lambda x: np.abs(x - x.mean()).mean(), raw=True)
    return (tp - sma_tp) / (0.015 * mean_dev).replace(0, np.nan)


def roc(close: pd.Series, period: int = 10) -> pd.Series:
    """
    ROC (Rate of Change)
    ROC = (Close - Close_n) / Close_n * 100%
    """
    prev = close.shift(period)
    return ((close - prev) / prev.replace(0, np.nan)) * 100


# ==============================================================
# 成交量类指标
# ==============================================================

def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    OBV (On-Balance Volume)
    涨日 +Vol, 跌日 -Vol, 累积
    """
    direction = np.sign(close.diff())
    direction.iloc[0] = 0
    return (volume * direction).cumsum()


def mfi(high: pd.Series, low: pd.Series, close: pd.Series,
        volume: pd.Series, period: int = 14) -> pd.Series:
    """
    MFI (Money Flow Index) — 结合价格与成交量的 RSI 变体
    """
    tp = (high + low + close) / 3
    mf = tp * volume
    tp_diff = tp.diff()

    pos_mf = pd.Series(np.where(tp_diff > 0, mf, 0.0), index=close.index)
    neg_mf = pd.Series(np.where(tp_diff < 0, mf, 0.0), index=close.index)

    pos_sum = pos_mf.rolling(window=period, min_periods=1).sum()
    neg_sum = neg_mf.rolling(window=period, min_periods=1).sum()

    mr = pos_sum / neg_sum.replace(0, np.nan)
    return 100 - 100 / (1 + mr)


def volume_ma(volume: pd.Series, period: int = 20) -> pd.Series:
    """成交量移动平均"""
    return sma(volume, period)


def vwap(high: pd.Series, low: pd.Series, close: pd.Series,
         volume: pd.Series) -> pd.Series:
    """
    VWAP (Volume Weighted Average Price)
    VWAP = Σ(TP×Volume) / ΣVolume
    """
    tp = (high + low + close) / 3
    cum_tp_vol = (tp * volume).cumsum()
    cum_vol = volume.cumsum()
    return cum_tp_vol / cum_vol.replace(0, np.nan)


# ==============================================================
# 波动率类指标
# ==============================================================

def atr(high: pd.Series, low: pd.Series, close: pd.Series,
        period: int = 14) -> pd.Series:
    """
    ATR (Average True Range)
    Wilder 平滑的真波幅
    """
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return _wilder_smooth(tr, period)


def historical_volatility(close: pd.Series, period: int = 20) -> pd.Series:
    """
    历史波动率（年化）
    HV = Std(Log Returns) × √252
    """
    log_ret = np.log(close / close.shift(1))
    return log_ret.rolling(window=period, min_periods=1).std() * np.sqrt(252)


def max_drawdown(close: pd.Series) -> float:
    """
    最大回撤
    MaxDD = Max(Peak - Trough) / Peak
    """
    peak = close.cummax()
    dd = (close - peak) / peak.replace(0, np.nan)
    return float(dd.min()) if not dd.empty else 0.0


def max_drawdown_series(close: pd.Series) -> pd.Series:
    """滚动最大回撤序列"""
    peak = close.cummax()
    return (close - peak) / peak.replace(0, np.nan)


# ==============================================================
# 趋势类指标 - 补充
# ==============================================================

def supertrend(high: pd.Series, low: pd.Series, close: pd.Series,
               period: int = 10, multiplier: float = 3.0
               ) -> tuple[pd.Series, pd.Series]:
    """
    SuperTrend 指标
    返回: (supertrend_line, direction)
    direction: 1 = 上涨趋势, -1 = 下跌趋势
    """
    # ATR
    atr_val = atr(high, low, close, period)

    # 基础中轨 (HL/2)
    hl_avg = (high + low) / 2

    # 上轨和下轨
    upper_band = hl_avg + multiplier * atr_val
    lower_band = hl_avg - multiplier * atr_val

    # 计算 SuperTrend
    supertrend = pd.Series(np.nan, index=close.index, dtype=float)
    direction = pd.Series(1, index=close.index, dtype=int)

    # 初始化
    supertrend.iloc[0] = close.iloc[0]
    direction.iloc[0] = 1

    for i in range(1, len(close)):
        # 更新上轨下轨
        if close.iloc[i] > upper_band.iloc[i-1]:
            upper_band.iloc[i] = upper_band.iloc[i]
        else:
            upper_band.iloc[i] = min(upper_band.iloc[i], upper_band.iloc[i-1])

        if close.iloc[i] < lower_band.iloc[i-1]:
            lower_band.iloc[i] = lower_band.iloc[i]
        else:
            lower_band.iloc[i] = max(lower_band.iloc[i], lower_band.iloc[i-1])

        # 计算 SuperTrend
        prev_st = supertrend.iloc[i-1]
        prev_dir = direction.iloc[i-1]

        if prev_dir == 1:  # 上涨趋势
            if close.iloc[i] < lower_band.iloc[i]:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1
            else:
                supertrend.iloc[i] = lower_band.iloc[i]
                direction.iloc[i] = 1
        else:  # 下跌趋势
            if close.iloc[i] > upper_band.iloc[i]:
                supertrend.iloc[i] = lower_band.iloc[i]
                direction.iloc[i] = 1
            else:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1

    return supertrend, direction


def sar(high: pd.Series, low: pd.Series,
        acceleration: float = 0.02, maximum: float = 0.2
        ) -> pd.Series:
    """
    SAR (Stop and Reverse) 抛物线指标
    返回 SAR 序列
    """
    sar_val = pd.Series(np.nan, index=high.index, dtype=float)
    trend = pd.Series(1, index=high.index, dtype=int)

    # 初始化
    sar_val.iloc[0] = low.iloc[0]
    extreme_point = high.iloc[0]
    af = acceleration

    for i in range(1, len(high)):
        prev_sar = sar_val.iloc[i-1]
        prev_trend = trend.iloc[i-1]
        prev_extreme = extreme_point

        # 计算 SAR
        new_sar = prev_sar + af * (prev_extreme - prev_sar)

        if prev_trend == 1:  # 上涨趋势
            # 检查是否反转
            if low.iloc[i] < new_sar:
                # 反转为下跌
                trend.iloc[i] = -1
                sar_val.iloc[i] = prev_extreme
                extreme_point = low.iloc[i]
                af = acceleration
            else:
                # 保持上涨
                trend.iloc[i] = 1
                sar_val.iloc[i] = new_sar
                if high.iloc[i] > prev_extreme:
                    extreme_point = high.iloc[i]
                    af = min(af + acceleration, maximum)
        else:  # 下跌趋势
            # 检查是否反转
            if high.iloc[i] > new_sar:
                # 反转为上涨
                trend.iloc[i] = 1
                sar_val.iloc[i] = prev_extreme
                extreme_point = high.iloc[i]
                af = acceleration
            else:
                # 保持下跌
                trend.iloc[i] = -1
                sar_val.iloc[i] = new_sar
                if low.iloc[i] < prev_extreme:
                    extreme_point = low.iloc[i]
                    af = min(af + acceleration, maximum)

    return sar_val


def ichimoku(high: pd.Series, low: pd.Series, close: pd.Series,
             conversion_period: int = 9, base_period: int = 26,
             span_b_period: int = 52, displacement: int = 26
             ) -> dict[str, pd.Series]:
    """
    Ichimoku Cloud 一目均衡表
    返回: dict with keys:
        - tenkan_sen: 转换线 (Conversion Line)
        - kijun_sen: 基准线 (Base Line)
        - senkou_span_a: 先驱A (Leading Span A)
        - senkou_span_b: 先驱B (Leading Span B)
        - chikou_span: 延迟线 (Lagging Span)
    """
    # Tenkan-sen (转换线) = (9日最高价 + 9日最低价) / 2
    tenkan_sen = (high.rolling(window=conversion_period, min_periods=1).max() +
                  low.rolling(window=conversion_period, min_periods=1).min()) / 2

    # Kijun-sen (基准线) = (26日最高价 + 26日最低价) / 2
    kijun_sen = (high.rolling(window=base_period, min_periods=1).max() +
                 low.rolling(window=base_period, min_periods=1).min()) / 2

    # Senkou Span A (先驱A) = (转换线 + 基准线) / 2, 向后位移26天
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(displacement)

    # Senkou Span B (先驱B) = (52日最高价 + 52日最低价) / 2, 向后位移26天
    senkou_span_b = ((high.rolling(window=span_b_period, min_periods=1).max() +
                      low.rolling(window=span_b_period, min_periods=1).min()) / 2).shift(displacement)

    # Chikou Span (延迟线) = 收盘价向后位移26天
    chikou_span = close.shift(-displacement)

    return {
        "tenkan_sen": tenkan_sen,
        "kijun_sen": kijun_sen,
        "senkou_span_a": senkou_span_a,
        "senkou_span_b": senkou_span_b,
        "chikou_span": chikou_span,
    }


# ==============================================================
# 动量类指标 - 补充
# ==============================================================

def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
               k_period: int = 14, d_period: int = 3
               ) -> tuple[pd.Series, pd.Series]:
    """
    Stochastic 随机指标
    返回: (%K, %D)
    %K = (Close - Lowest Low) / (Highest High - Lowest Low) * 100
    %D = %K 的移动平均
    """
    lowest_low = low.rolling(window=k_period, min_periods=1).min()
    highest_high = high.rolling(window=k_period, min_periods=1).max()

    k_percent = 100 * (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
    d_percent = k_percent.rolling(window=d_period, min_periods=1).mean()

    return k_percent, d_percent


def williams_r(high: pd.Series, low: pd.Series, close: pd.Series,
               period: int = 14) -> pd.Series:
    """
    Williams %R 威廉指标
    %R = (Highest High - Close) / (Highest High - Lowest Low) * -100
    范围: -100 ~ 0, 超卖区: -80 ~ -100, 超买区: 0 ~ -20
    """
    highest_high = high.rolling(window=period, min_periods=1).max()
    lowest_low = low.rolling(window=period, min_periods=1).min()

    williams = -100 * (highest_high - close) / (highest_high - lowest_low).replace(0, np.nan)
    return williams


def mom(close: pd.Series, period: int = 10) -> pd.Series:
    """
    MOM (Momentum) 动量指标
    MOM = Close - Close_n
    正值表示上涨动量，负值表示下跌动量
    """
    return close - close.shift(period)


# ==============================================================
# 量价类指标 - 补充
# ==============================================================

def volume_profile(close: pd.Series, volume: pd.Series,
                   bins: int = 20) -> pd.Series:
    """
    Volume Profile 成交量分布
    返回每个价格区间的成交量总和
    """
    price_min = close.min()
    price_max = close.max()
    price_range = price_max - price_min

    if price_range == 0:
        return pd.Series(0, index=close.index)

    # 创建价格区间
    bin_size = price_range / bins
    bin_edges = [price_min + i * bin_size for i in range(bins + 1)]

    # 计算每个区间的成交量
    vp = pd.Series(0.0, index=close.index, dtype=float)

    for i in range(len(close)):
        price = close.iloc[i]
        vol = volume.iloc[i]

        for j in range(bins):
            if bin_edges[j] <= price < bin_edges[j + 1]:
                vp.iloc[i] += vol
                break

    return vp


def accumulation_distribution(high: pd.Series, low: pd.Series,
                               close: pd.Series, volume: pd.Series
                               ) -> pd.Series:
    """
    A/D (Accumulation/Distribution) 累积派发指标
    A/D = 前一日A/D + 今日资金流量
    资金流量 = ((Close - Low) - (High - Close)) / (High - Low) * Volume
    """
    # 资金流量乘数
    mf_multiplier = ((close - low) - (high - close)) / (high - low).replace(0, np.nan)
    mf_multiplier = mf_multiplier.fillna(0)

    # 资金流量
    money_flow = mf_multiplier * volume

    # 累积
    return money_flow.cumsum()


# ==============================================================
# 波动率类指标 - 补充
# ==============================================================

def keltner_channel(high: pd.Series, low: pd.Series, close: pd.Series,
                    ema_period: int = 20, atr_period: int = 10,
                    multiplier: float = 2.0
                    ) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Keltner Channel 肯特纳通道
    返回: (upper, middle, lower)
    Middle = EMA(close, ema_period)
    Upper = Middle + Multiplier * ATR
    Lower = Middle - Multiplier * ATR
    """
    middle = ema(close, ema_period)
    atr_val = atr(high, low, close, atr_period)

    upper = middle + multiplier * atr_val
    lower = middle - multiplier * atr_val

    return upper, middle, lower


def donchian_channel(high: pd.Series, low: pd.Series,
                      period: int = 20
                      ) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Donchian Channel 唐奇安通道
    返回: (upper, middle, lower)
    Upper = 最高价的最大值
    Lower = 最低价的最小值
    Middle = (Upper + Lower) / 2
    """
    upper = high.rolling(window=period, min_periods=1).max()
    lower = low.rolling(window=period, min_periods=1).min()
    middle = (upper + lower) / 2

    return upper, middle, lower


# ==============================================================
# 辅助函数
# ==============================================================

def _wilder_smooth(series: pd.Series, period: int) -> pd.Series:
    """Wilder 平滑（等价于 EMA with alpha = 1/period）"""
    return series.ewm(alpha=1.0 / period, adjust=False).mean()


def compute_all_indicators(df: pd.DataFrame, params: dict = None
                           ) -> dict[str, pd.Series | tuple]:
    """
    一次性计算所有技术指标。
    df 需包含: close, high, low, volume 列。
    返回 dict，key 为指标名，value 为 Series 或 tuple。
    """
    import config as _config
    p = params or _config.INDICATOR_PARAMS

    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    vol = df["volume"].astype(float)

    result = {}

    # 均线
    for period in p["ma_periods"]:
        result[f"sma_{period}"] = sma(close, period)
        result[f"ema_{period}"] = ema(close, period)

    # MACD
    mp = p["macd"]
    dif, dea, hist = macd(close, mp["fast"], mp["slow"], mp["signal"])
    result["macd_dif"] = dif
    result["macd_dea"] = dea
    result["macd_hist"] = hist

    # 布林带
    bp = p["bollinger"]
    bb_upper, bb_mid, bb_lower, bb_bw = bollinger_bands(
        close, bp["period"], bp["std_mult"])
    result["bb_upper"] = bb_upper
    result["bb_middle"] = bb_mid
    result["bb_lower"] = bb_lower
    result["bb_bandwidth"] = bb_bw

    # ADX
    adx_val, plus_di, minus_di = adx(high, low, close, p["adx_period"])
    result["adx"] = adx_val
    result["plus_di"] = plus_di
    result["minus_di"] = minus_di

    # RSI
    for period in p["rsi_periods"]:
        result[f"rsi_{period}"] = rsi(close, period)

    # KDJ
    kp = p["kdj"]
    k_val, d_val, j_val = kdj(high, low, close, kp["n"], kp["m1"], kp["m2"])
    result["kdj_k"] = k_val
    result["kdj_d"] = d_val
    result["kdj_j"] = j_val

    # CCI
    result["cci"] = cci(high, low, close, p["cci_period"])

    # ROC
    result["roc"] = roc(close, p["roc_period"])

    # OBV
    result["obv"] = obv(close, vol)

    # MFI
    result["mfi"] = mfi(high, low, close, vol, p["mfi_period"])

    # 成交量均线
    result["volume_ma"] = volume_ma(vol, p["volume_ma_period"])

    # VWAP
    result["vwap"] = vwap(high, low, close, vol)

    # ATR
    result["atr"] = atr(high, low, close, p["atr_period"])

    # 历史波动率
    result["hist_volatility"] = historical_volatility(close, p["volatility_period"])

    # ===== 补充指标 =====

    # SuperTrend
    st = p.get("supertrend", {"period": 10, "multiplier": 3.0})
    st_line, st_dir = supertrend(high, low, close, st["period"], st["multiplier"])
    result["supertrend_line"] = st_line
    result["supertrend_direction"] = st_dir

    # SAR
    sar_params = p.get("sar", {"acceleration": 0.02, "maximum": 0.2})
    result["sar"] = sar(high, low, sar_params["acceleration"], sar_params["maximum"])

    # Ichimoku
    ic = p.get("ichimoku", {
        "conversion_period": 9,
        "base_period": 26,
        "span_b_period": 52,
        "displacement": 26,
    })
    ichimoku_result = ichimoku(high, low, close,
                                ic["conversion_period"], ic["base_period"],
                                ic["span_b_period"], ic["displacement"])
    result["ichimoku_tenkan"] = ichimoku_result["tenkan_sen"]
    result["ichimoku_kijun"] = ichimoku_result["kijun_sen"]
    result["ichimoku_senkou_a"] = ichimoku_result["senkou_span_a"]
    result["ichimoku_senkou_b"] = ichimoku_result["senkou_span_b"]
    result["ichimoku_chikou"] = ichimoku_result["chikou_span"]

    # Stochastic
    stoch = p.get("stochastic", {"k_period": 14, "d_period": 3})
    k_pct, d_pct = stochastic(high, low, close, stoch["k_period"], stoch["d_period"])
    result["stoch_k"] = k_pct
    result["stoch_d"] = d_pct

    # Williams %R
    result["williams_r"] = williams_r(high, low, close, p.get("williams_r_period", 14))

    # MOM
    result["mom"] = mom(close, p.get("mom_period", 10))

    # Volume Profile
    result["volume_profile"] = volume_profile(close, vol, p.get("volume_profile_bins", 20))

    # A/D Accumulation/Distribution
    result["ad_line"] = accumulation_distribution(high, low, close, vol)

    # Keltner Channel
    kc = p.get("keltner", {"ema_period": 20, "atr_period": 10, "multiplier": 2.0})
    kc_upper, kc_mid, kc_lower = keltner_channel(high, low, close,
                                                  kc["ema_period"], kc["atr_period"],
                                                  kc["multiplier"])
    result["keltner_upper"] = kc_upper
    result["keltner_middle"] = kc_mid
    result["keltner_lower"] = kc_lower

    # Donchian Channel
    dc_upper, dc_mid, dc_lower = donchian_channel(high, low, p.get("donchian_period", 20))
    result["donchian_upper"] = dc_upper
    result["donchian_middle"] = dc_mid
    result["donchian_lower"] = dc_lower

    return result
