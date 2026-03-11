"""
市场跟踪器 - 技术指标计算库
纯 numpy/pandas 实现，覆盖趋势/动量/成交量/波动率四大类指标
参考 knowledge.md 中的指标体系
"""

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
    from .config import INDICATOR_PARAMS
    p = params or INDICATOR_PARAMS

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

    return result
