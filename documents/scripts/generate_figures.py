#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技术指标可视化图表生成脚本
用于 technical_indicators_guide.md 的配图
"""

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from matplotlib import rcParams
import warnings
warnings.filterwarnings('ignore')

# 设置图表样式（必须先设置样式）
plt.style.use('seaborn-whitegrid')

# 设置中文字体 - 使用系统中安装的Noto字体
chinese_font_path = '/usr/share/fonts/font/NotoSerifSC-Regular.otf'
fm.fontManager.addfont(chinese_font_path)
plt.rcParams['font.family'] = 'Noto Serif SC'
plt.rcParams['axes.unicode_minus'] = False

def generate_sample_data(days=120, seed=42):
    """生成模拟的股票数据"""
    np.random.seed(seed)
    dates = pd.date_range(start='2024-01-01', periods=days)

    # 生成模拟价格趋势
    trend = np.linspace(100, 130, days)
    seasonal = 5 * np.sin(np.linspace(0, 8 * np.pi, days))
    noise = np.random.normal(0, 2, days)

    close = trend + seasonal + noise

    # 生成OHLC数据
    high = close + np.random.uniform(1, 3, days)
    low = close - np.random.uniform(1, 3, days)
    open_price = np.roll(close, 1)
    open_price[0] = close[0]
    volume = np.random.uniform(1000000, 5000000, days)

    return pd.DataFrame({
        'date': dates,
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    })


def calculate_sma(data, period):
    """计算简单移动平均"""
    return data['close'].rolling(window=period).mean()


def calculate_ema(data, period):
    """计算指数移动平均"""
    return data['close'].ewm(span=period, adjust=False).mean()


def calculate_bollinger_bands(data, period=20, num_std=2):
    """计算布林带"""
    sma = data['close'].rolling(window=period).mean()
    std = data['close'].rolling(window=period).std()
    upper = sma + num_std * std
    lower = sma - num_std * std
    return sma, upper, lower


def calculate_macd(data, fast=12, slow=26, signal=9):
    """计算MACD"""
    ema_fast = data['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = data['close'].ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    macd = 2 * (dif - dea)
    return dif, dea, macd


def calculate_rsi(data, period=14):
    """计算RSI"""
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_kdj(data, n=9, m1=3, m2=3):
    """计算KDJ"""
    low_n = data['low'].rolling(window=n).min()
    high_n = data['high'].rolling(window=n).max()

    rsv = (data['close'] - low_n) / (high_n - low_n) * 100
    rsv = rsv.fillna(50)

    k = rsv.ewm(alpha=1/m1, adjust=False).mean()
    d = k.ewm(alpha=1/m2, adjust=False).mean()
    j = 3 * k - 2 * d

    return k, d, j


def calculate_obv(data):
    """计算OBV"""
    obv = [0]
    for i in range(1, len(data)):
        if data['close'].iloc[i] > data['close'].iloc[i-1]:
            obv.append(obv[-1] + data['volume'].iloc[i])
        elif data['close'].iloc[i] < data['close'].iloc[i-1]:
            obv.append(obv[-1] - data['volume'].iloc[i])
        else:
            obv.append(obv[-1])
    return pd.Series(obv, index=data.index)


def calculate_atr(data, period=14):
    """计算ATR"""
    high_low = data['high'] - data['low']
    high_close = np.abs(data['high'] - data['close'].shift())
    low_close = np.abs(data['low'] - data['close'].shift())

    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


# ============ 图1: K线图示例 ============
def plot_candlestick():
    """绘制K线图示例"""
    # 生成更规整的数据用于展示
    np.random.seed(42)
    days = 30
    base_price = 100

    opens = [base_price]
    closes = []
    highs = []
    lows = []

    for i in range(1, days):
        change = np.random.normal(0.5, 2)
        close = opens[-1] + change
        opens.append(opens[-1] + np.random.normal(0, 0.5))

        high = max(opens[-1], close) + abs(np.random.normal(0, 1))
        low = min(opens[-1], close) - abs(np.random.normal(0, 1))

        closes.append(close)
        highs.append(high)
        lows.append(low)

    closes = closes[1:] + [closes[-1] + np.random.normal(0.5, 1)]

    fig, ax = plt.subplots(figsize=(14, 8))

    # 绘制K线
    width = 0.6
    width2 = 0.1

    for i in range(min(20, days-1)):
        if closes[i] >= opens[i]:
            color = '#FF4136'  # 阳线红色
            body_bottom = opens[i]
            body_height = closes[i] - opens[i]
        else:
            color = '#2ECC40'  # 阴线绿色
            body_bottom = closes[i]
            body_height = opens[i] - closes[i]

        # 画实体
        ax.add_patch(plt.Rectangle(
            (i - width/2, body_bottom), width, body_height,
            facecolor=color, edgecolor=color, linewidth=1
        ))

        # 画上下影线
        ax.plot([i, i], [lows[i], highs[i]], color=color, linewidth=1)

    # 设置图表
    ax.set_xlim(-1, 20)
    ax.set_ylim(95, 110)
    ax.set_xlabel('交易日', fontsize=12)
    ax.set_ylabel('价格 (元)', fontsize=12)
    ax.set_title('K线图（蜡烛图）示例\n红色=阳线（上涨） 绿色=阴线（下跌）', fontsize=14, fontweight='bold')

    # 添加图例
    red_patch = mpatches.Patch(color='#FF4136', label='阳线（收盘价 > 开盘价）')
    green_patch = mpatches.Patch(color='#2ECC40', label='阴线（收盘价 < 开盘价）')
    ax.legend(handles=[red_patch, green_patch], loc='upper left', fontsize=10)

    # 添加标注
    ax.annotate('上影线\n(最高价)', xy=(3, 107), xytext=(5, 108.5),
                fontsize=10, ha='center',
                arrowprops=dict(arrowstyle='->', color='gray'))
    ax.annotate('下影线\n(最低价)', xy=(8, 97), xytext=(10, 95.5),
                fontsize=10, ha='center',
                arrowprops=dict(arrowstyle='->', color='gray'))
    ax.annotate('实体\n(开盘-收盘)', xy=(12, 102.5), xytext=(14, 104),
                fontsize=10, ha='center',
                arrowprops=dict(arrowstyle='->', color='gray'))

    plt.tight_layout()
    plt.savefig('../images/figure_kline.png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print("图1: K线图示例 已保存")


# ============ 图2: 移动平均线 ============
def plot_moving_average():
    """绘制移动平均线"""
    data = generate_sample_data(120)
    data['SMA20'] = calculate_sma(data, 20)
    data['SMA60'] = calculate_sma(data, 60)
    data['EMA20'] = calculate_ema(data, 20)

    fig, ax = plt.subplots(figsize=(14, 7))

    ax.plot(data['close'], label='收盘价', color='#333333', linewidth=1.5, alpha=0.8)
    ax.plot(data['SMA20'], label='SMA20 (简单移动平均)', color='#FF6B6B', linewidth=2)
    ax.plot(data['SMA60'], label='SMA60 (长期均线)', color='#4ECDC4', linewidth=2)
    ax.plot(data['EMA20'], label='EMA20 (指数移动平均)', color='#9B59B6', linewidth=2, linestyle='--')

    # 标注金叉死叉区域
    ax.axvline(x=60, color='orange', linestyle=':', alpha=0.7, label='均线交叉区域')
    ax.axvline(x=90, color='orange', linestyle=':', alpha=0.7)

    # 添加说明框
    textstr = '金叉: 短期均线从下向上穿过长期均线 → 买入信号\n死叉: 短期均线从上向下穿过长期均线 → 卖出信号'
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
    ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=props)

    ax.set_xlabel('交易日', fontsize=12)
    ax.set_ylabel('价格 (元)', fontsize=12)
    ax.set_title('移动平均线 (MA) 示例\nSMA vs EMA', fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('../images/figure_ma.png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print("图2: 移动平均线 已保存")


# ============ 图3: MACD指标 ============
def plot_macd():
    """绘制MACD指标"""
    data = generate_sample_data(120)
    dif, dea, macd = calculate_macd(data)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9), gridspec_kw={'height_ratios': [2, 1]})

    # 上半部分：价格走势
    ax1.plot(data['close'], label='收盘价', color='#333333', linewidth=1.5)
    ax1.set_ylabel('价格 (元)', fontsize=11)
    ax1.set_title('MACD指标示例', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)

    # 下半部分：MACD
    ax2.plot(dif, label='DIF (快线)', color='#2196F3', linewidth=1.5)
    ax2.plot(dea, label='DEA (信号线)', color='#FF9800', linewidth=1.5)

    # MACD柱状图
    colors = ['#FF4136' if m >= 0 else '#2ECC40' for m in macd]
    ax2.bar(range(len(macd)), macd, color=colors, alpha=0.7, width=0.8, label='MACD柱')

    ax2.axhline(y=0, color='gray', linestyle='-', linewidth=0.8)
    ax2.set_xlabel('交易日', fontsize=11)
    ax2.set_ylabel('MACD值', fontsize=11)
    ax2.legend(loc='upper left', fontsize=10)
    ax2.grid(True, alpha=0.3)

    # 标注金叉死叉
    ax2.annotate('金叉\n(DIF上穿DEA)', xy=(30, dif.iloc[30]-0.5), xytext=(35, -2),
                fontsize=9, ha='center',
                arrowprops=dict(arrowstyle='->', color='red'),
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

    ax2.annotate('死叉\n(DIF下穿DEA)', xy=(80, dif.iloc[80]+0.5), xytext=(75, 2.5),
                fontsize=9, ha='center',
                arrowprops=dict(arrowstyle='->', color='green'),
                bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))

    plt.tight_layout()
    plt.savefig('../images/figure_macd.png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print("图3: MACD指标 已保存")


# ============ 图4: 布林带 ============
def plot_bollinger():
    """绘制布林带"""
    data = generate_sample_data(120)
    sma, upper, lower = calculate_bollinger_bands(data, 20, 2)

    fig, ax = plt.subplots(figsize=(14, 7))

    # 绘制价格
    ax.plot(data['close'], label='收盘价', color='#333333', linewidth=1.5)

    # 绘制布林带
    ax.plot(sma, label='中轨 (SMA20)', color='#2196F3', linewidth=1.5)
    ax.plot(upper, label='上轨 (+2σ)', color='#FF5722', linewidth=1.5, linestyle='--')
    ax.plot(lower, label='下轨 (-2σ)', color='#4CAF50', linewidth=1.5, linestyle='--')

    # 填充布林带区域
    ax.fill_between(range(len(data)), lower, upper, alpha=0.1, color='blue')

    # 标注超买超卖区域
    ax.annotate('超买区域\n(价格触及上轨)', xy=(25, upper.iloc[25]), xytext=(35, upper.iloc[25]+3),
                fontsize=10, ha='center',
                arrowprops=dict(arrowstyle='->', color='red'),
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

    ax.annotate('超卖区域\n(价格触及下轨)', xy=(85, lower.iloc[85]), xytext=(75, lower.iloc[85]-3),
                fontsize=10, ha='center',
                arrowprops=dict(arrowstyle='->', color='green'),
                bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))

    ax.set_xlabel('交易日', fontsize=12)
    ax.set_ylabel('价格 (元)', fontsize=12)
    ax.set_title('布林带 (Bollinger Bands) 示例', fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('../images/figure_bollinger.png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print("图4: 布林带 已保存")


# ============ 图5: RSI指标 ============
def plot_rsi():
    """绘制RSI指标"""
    data = generate_sample_data(120)
    rsi = calculate_rsi(data)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={'height_ratios': [2, 1]})

    # 上半部分：价格
    ax1.plot(data['close'], label='收盘价', color='#333333', linewidth=1.5)
    ax1.set_ylabel('价格 (元)', fontsize=11)
    ax1.set_title('RSI 相对强弱指标示例', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)

    # 下半部分：RSI
    ax2.plot(rsi, label='RSI(14)', color='#9C27B0', linewidth=1.5)

    # 超买超卖区域
    ax2.axhline(y=70, color='red', linestyle='--', linewidth=1, alpha=0.7)
    ax2.axhline(y=30, color='green', linestyle='--', linewidth=1, alpha=0.7)
    ax2.axhline(y=50, color='gray', linestyle='-', linewidth=0.8, alpha=0.5)

    ax2.fill_between(range(len(rsi)), 70, 100, alpha=0.15, color='red')
    ax2.fill_between(range(len(rsi)), 0, 30, alpha=0.15, color='green')

    ax2.set_xlabel('交易日', fontsize=11)
    ax2.set_ylabel('RSI值', fontsize=11)
    ax2.set_ylim(0, 100)
    ax2.legend(loc='upper left', fontsize=10)
    ax2.grid(True, alpha=0.3)

    # 标注
    ax2.annotate('超买区 (RSI>70)\n警惕回调风险', xy=(95, 75), xytext=(105, 75),
                fontsize=9, ha='left',
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

    ax2.annotate('超卖区 (RSI<30)\n关注反弹机会', xy=(95, 25), xytext=(105, 25),
                fontsize=9, ha='left',
                bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))

    plt.tight_layout()
    plt.savefig('../images/figure_rsi.png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print("图5: RSI指标 已保存")


# ============ 图6: KDJ指标 ============
def plot_kdj():
    """绘制KDJ指标"""
    data = generate_sample_data(120)
    k, d, j = calculate_kdj(data)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={'height_ratios': [2, 1]})

    # 上半部分：价格
    ax1.plot(data['close'], label='收盘价', color='#333333', linewidth=1.5)
    ax1.set_ylabel('价格 (元)', fontsize=11)
    ax1.set_title('KDJ 随机指标示例', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)

    # 下半部分：KDJ
    ax2.plot(k, label='K值', color='#2196F3', linewidth=1.5)
    ax2.plot(d, label='D值', color='#FF9800', linewidth=1.5)
    ax2.plot(j, label='J值', color='#E91E63', linewidth=1.5, linestyle='--')

    # 超买超卖区域
    ax2.axhline(y=80, color='red', linestyle='--', linewidth=1, alpha=0.7)
    ax2.axhline(y=20, color='green', linestyle='--', linewidth=1, alpha=0.7)

    ax2.fill_between(range(len(k)), 80, 100, alpha=0.15, color='red')
    ax2.fill_between(range(len(k)), 0, 20, alpha=0.15, color='green')

    ax2.set_xlabel('交易日', fontsize=11)
    ax2.set_ylabel('KDJ值', fontsize=11)
    ax2.set_ylim(-10, 110)
    ax2.legend(loc='upper left', fontsize=10)
    ax2.grid(True, alpha=0.3)

    # 标注
    ax2.annotate('金叉: K上穿D → 买入', xy=(30, k.iloc[30]), xytext=(45, 20),
                fontsize=9, ha='center',
                arrowprops=dict(arrowstyle='->', color='blue'),
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))

    ax2.annotate('J>100 超买极端', xy=(j.idxmax(), 100), xytext=(j.idxmax()+10, 105),
                fontsize=9, ha='center',
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

    plt.tight_layout()
    plt.savefig('../images/figure_kdj.png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print("图6: KDJ指标 已保存")


# ============ 图7: OBV指标 ============
def plot_obv():
    """绘制OBV指标"""
    data = generate_sample_data(120)
    obv = calculate_obv(data)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={'height_ratios': [2, 1]})

    # 上半部分：价格和OBV趋势
    ax1.plot(data['close'], label='收盘价', color='#333333', linewidth=1.5)
    ax1.set_ylabel('价格 (元)', fontsize=11)
    ax1.set_title('OBV 能量潮指标示例', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)

    # 下半部分：OBV
    ax2.plot(obv, label='OBV', color='#4CAF50', linewidth=1.5)
    ax2.fill_between(range(len(obv)), obv, alpha=0.3, color='#4CAF50')

    # 计算OBV的移动平均
    obv_ma = obv.rolling(window=10).mean()
    ax2.plot(obv_ma, label='OBV10均线', color='#FF9800', linewidth=1.5, linestyle='--')

    ax2.set_xlabel('交易日', fontsize=11)
    ax2.set_ylabel('OBV值', fontsize=11)
    ax2.legend(loc='upper left', fontsize=10)
    ax2.grid(True, alpha=0.3)

    # 标注量价关系
    ax2.annotate('OBV上升 + 价格上涨\n= 量价齐升 (可靠上涨)', xy=(30, obv.iloc[30]), xytext=(30, obv.max()*0.7),
                fontsize=9, ha='center',
                bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))

    plt.tight_layout()
    plt.savefig('../images/figure_obv.png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print("图7: OBV指标 已保存")


# ============ 图8: ATR和止损 ============
def plot_atr():
    """绘制ATR指标和止损应用"""
    data = generate_sample_data(120)
    data['SMA20'] = calculate_sma(data, 20)
    atr = calculate_atr(data)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={'height_ratios': [2, 1]})

    # 模拟买入点
    buy_price = data['close'].iloc[80]
    stop_loss = buy_price - 2 * atr.iloc[80]

    # 上半部分：价格和止损位
    ax1.plot(data['close'], label='收盘价', color='#333333', linewidth=1.5)
    ax1.plot(data['SMA20'], label='SMA20', color='#2196F3', linewidth=1.5, linestyle='--')

    ax1.scatter([80], [buy_price], color='red', s=150, zorder=5, marker='^', label='买入点')
    ax1.axhline(y=buy_price, color='red', linestyle=':', alpha=0.5)
    ax1.axhline(y=stop_loss, color='green', linestyle='--', linewidth=2, label=f'止损位 (买入价-2×ATR)')
    ax1.fill_between(range(80, 120), stop_loss, buy_price, alpha=0.2, color='red')

    ax1.set_ylabel('价格 (元)', fontsize=11)
    ax1.set_title('ATR 平均真实波幅与动态止损示例', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left', fontsize=9)
    ax1.grid(True, alpha=0.3)

    # 下半部分：ATR
    ax2.plot(atr, label='ATR(14)', color='#9C27B0', linewidth=1.5)
    ax2.fill_between(range(len(atr)), atr, alpha=0.3, color='#9C27B0')

    ax2.set_xlabel('交易日', fontsize=11)
    ax2.set_ylabel('ATR值', fontsize=11)
    ax2.legend(loc='upper left', fontsize=10)
    ax2.grid(True, alpha=0.3)

    # 标注
    ax1.annotate(f'买入价: {buy_price:.1f}', xy=(80, buy_price), xytext=(65, buy_price+5),
                fontsize=10, ha='center',
                arrowprops=dict(arrowstyle='->', color='red'),
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

    ax1.annotate(f'止损位: {stop_loss:.1f}\n(2×ATR保护)', xy=(80, stop_loss), xytext=(95, stop_loss-3),
                fontsize=10, ha='center',
                arrowprops=dict(arrowstyle='->', color='green'),
                bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))

    plt.tight_layout()
    plt.savefig('../images/figure_atr.png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print("图8: ATR指标 已保存")


# ============ 图9: 综合指标面板 ============
def plot_dashboard():
    """绘制综合指标面板"""
    data = generate_sample_data(120)
    data['SMA20'] = calculate_sma(data, 20)
    dif, dea, macd = calculate_macd(data)
    rsi = calculate_rsi(data)
    k, d, j = calculate_kdj(data)

    fig, axes = plt.subplots(4, 1, figsize=(14, 16))

    # 1. 价格 + 均线
    axes[0].plot(data['close'], label='收盘价', color='#333333', linewidth=1.2)
    axes[0].plot(data['SMA20'], label='SMA20', color='#2196F3', linewidth=1.5)
    axes[0].set_ylabel('价格', fontsize=10)
    axes[0].set_title('综合技术指标面板', fontsize=14, fontweight='bold')
    axes[0].legend(loc='upper left', fontsize=9)
    axes[0].grid(True, alpha=0.3)

    # 2. MACD
    axes[1].plot(dif, label='DIF', color='#2196F3', linewidth=1.2)
    axes[1].plot(dea, label='DEA', color='#FF9800', linewidth=1.2)
    colors = ['#FF4136' if m >= 0 else '#2ECC40' for m in macd]
    axes[1].bar(range(len(macd)), macd, color=colors, alpha=0.7, width=0.8)
    axes[1].axhline(y=0, color='gray', linestyle='-', linewidth=0.8)
    axes[1].set_ylabel('MACD', fontsize=10)
    axes[1].legend(loc='upper left', fontsize=9)
    axes[1].grid(True, alpha=0.3)

    # 3. RSI
    axes[2].plot(rsi, label='RSI', color='#9C27B0', linewidth=1.2)
    axes[2].axhline(y=70, color='red', linestyle='--', linewidth=0.8, alpha=0.7)
    axes[2].axhline(y=30, color='green', linestyle='--', linewidth=0.8, alpha=0.7)
    axes[2].fill_between(range(len(rsi)), 70, 100, alpha=0.1, color='red')
    axes[2].fill_between(range(len(rsi)), 0, 30, alpha=0.1, color='green')
    axes[2].set_ylabel('RSI', fontsize=10)
    axes[2].set_ylim(0, 100)
    axes[2].legend(loc='upper left', fontsize=9)
    axes[2].grid(True, alpha=0.3)

    # 4. KDJ
    axes[3].plot(k, label='K', color='#2196F3', linewidth=1.2)
    axes[3].plot(d, label='D', color='#FF9800', linewidth=1.2)
    axes[3].plot(j, label='J', color='#E91E63', linewidth=1.2, linestyle='--')
    axes[3].axhline(y=80, color='red', linestyle='--', linewidth=0.8, alpha=0.7)
    axes[3].axhline(y=20, color='green', linestyle='--', linewidth=0.8, alpha=0.7)
    axes[3].set_ylabel('KDJ', fontsize=10)
    axes[3].set_xlabel('交易日', fontsize=10)
    axes[3].legend(loc='upper left', fontsize=9)
    axes[3].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('../images/figure_dashboard.png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print("图9: 综合指标面板 已保存")


if __name__ == '__main__':
    print("开始生成技术指标图表...")
    print("=" * 50)

    plot_candlestick()
    plot_moving_average()
    plot_macd()
    plot_bollinger()
    plot_rsi()
    plot_kdj()
    plot_obv()
    plot_atr()
    plot_dashboard()

    print("=" * 50)
    print("所有图表生成完成！")
    print("生成的图表文件:")
    print("  - figure_kline.png (K线图)")
    print("  - figure_ma.png (移动平均线)")
    print("  - figure_macd.png (MACD)")
    print("  - figure_bollinger.png (布林带)")
    print("  - figure_rsi.png (RSI)")
    print("  - figure_kdj.png (KDJ)")
    print("  - figure_obv.png (OBV)")
    print("  - figure_atr.png (ATR)")
    print("  - figure_dashboard.png (综合面板)")
