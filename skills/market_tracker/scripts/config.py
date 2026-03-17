"""
市场跟踪器 - 配置中心
资产类型映射、技术指标参数、决策权重、路径常量
"""

import os

# ============================================================
# 路径常量
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)  # market_tracker/
DB_PATH = os.path.join(BASE_DIR, "market_data.db")
WATCHLIST_PATH = os.path.join(BASE_DIR, "watchlist.json")
TEST_DATA_DIR = os.path.join(BASE_DIR, "test_data")

# ============================================================
# 资产类型
# ============================================================
ASSET_TYPES = ("stock", "index", "etf", "futures", "gold")

ASSET_TYPE_NAMES = {
    "stock": "A股个股",
    "index": "指数",
    "etf": "ETF基金",
    "futures": "期货",
    "gold": "黄金/贵金属",
}

# ============================================================
# 技术指标默认参数（参考 knowledge.md）
# ============================================================
INDICATOR_PARAMS = {
    # 均线周期
    "ma_periods": [5, 20, 60, 200],
    # MACD (fast, slow, signal)
    "macd": {"fast": 12, "slow": 26, "signal": 9},
    # RSI 周期
    "rsi_periods": [6, 14, 24],
    # KDJ (n, m1, m2)
    "kdj": {"n": 9, "m1": 3, "m2": 3},
    # 布林带 (period, std_multiplier)
    "bollinger": {"period": 20, "std_mult": 2},
    # ATR 周期
    "atr_period": 14,
    # ADX 周期
    "adx_period": 14,
    # CCI 周期
    "cci_period": 20,
    # ROC 周期
    "roc_period": 10,
    # MFI 周期
    "mfi_period": 14,
    # OBV 成交量均线
    "volume_ma_period": 20,
    # 历史波动率回看窗口
    "volatility_period": 20,

    # ===== 补充指标参数 =====

    # SuperTrend (period, multiplier)
    "supertrend": {"period": 10, "multiplier": 3.0},
    # SAR (acceleration, maximum)
    "sar": {"acceleration": 0.02, "maximum": 0.2},
    # Ichimoku (conversion, base, span_b, displacement)
    "ichimoku": {
        "conversion_period": 9,
        "base_period": 26,
        "span_b_period": 52,
        "displacement": 26,
    },
    # Stochastic (k_period, d_period)
    "stochastic": {"k_period": 14, "d_period": 3},
    # Williams %R (period)
    "williams_r_period": 14,
    # MOM (period)
    "mom_period": 10,
    # Volume Profile (bins)
    "volume_profile_bins": 20,
    # Keltner Channel (ema_period, atr_period, multiplier)
    "keltner": {"ema_period": 20, "atr_period": 10, "multiplier": 2.0},
    # Donchian Channel (period)
    "donchian_period": 20,
}

# ============================================================
# 决策引擎参数
# ============================================================
# Layer 1: 技术信号权重（各指标对最终信号的贡献）
SIGNAL_WEIGHTS = {
    "ma_alignment": 0.15,       # 均线多空排列
    "macd_cross": 0.15,         # MACD 金叉/死叉
    "rsi": 0.10,                # RSI 超买超卖
    "kdj": 0.10,                # KDJ 交叉
    "bollinger": 0.10,          # 布林带位置
    "adx_trend": 0.10,          # ADX 趋势强度
    "volume_price": 0.10,       # 量价配合
}

# Layer 2: 量化因子权重
FACTOR_WEIGHTS = {
    "momentum": 0.40,           # 动量因子
    "volatility": 0.30,         # 波动因子
    "volume_price": 0.30,       # 量价因子
}

# Layer 1 vs Layer 2 综合权重
LAYER_WEIGHTS = {
    "technical_signal": 0.6,    # 技术信号层权重
    "factor_score": 0.4,        # 因子评分层权重
}

# 决策阈值
DECISION_THRESHOLDS = {
    "strong_buy": 0.6,          # 综合得分 > 0.6 → 强烈买入
    "buy": 0.3,                 # > 0.3 → 买入
    "hold_upper": 0.3,          # -0.3 ~ 0.3 → 持有
    "hold_lower": -0.3,
    "sell": -0.3,               # < -0.3 → 卖出
    "strong_sell": -0.6,        # < -0.6 → 强烈卖出
}

# RSI 超买超卖阈值
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# ADX 有效趋势阈值
ADX_TREND_THRESHOLD = 25

# ============================================================
# 定时轮询
# ============================================================
DEFAULT_MONITOR_INTERVAL = 300  # 秒（5分钟）

# ============================================================
# 历史数据默认回看天数（用于首次拉取）
# ============================================================
DEFAULT_HISTORY_DAYS = 365

# ============================================================
# 支持的K线周期
# ============================================================
VALID_PERIODS = ("daily", "weekly", "monthly")
PERIOD_NAMES = {
    "daily": "日线",
    "weekly": "周线",
    "monthly": "月线",
}
# 仅支持日线的资产类型（AKShare 限制）
DAILY_ONLY_ASSET_TYPES = ("futures", "gold")

# ============================================================
# 量化因子参数
# ============================================================
FACTOR_PARAMS = {
    "momentum_windows": [20, 60, 120],   # 1月/3月/6月 交易日
    "volatility_window": 20,             # 波动率计算窗口
    "volume_corr_window": 20,            # 量价相关性窗口
}
