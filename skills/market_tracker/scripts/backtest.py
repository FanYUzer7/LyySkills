"""
市场跟踪器 - 回测引擎
基于历史K线回放决策信号，统计策略表现
简单固定仓位模型：信号买入 → 下一日开盘价成交
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
from datetime import datetime

import decision_engine
import config

InvestmentDecision = decision_engine.InvestmentDecision
DECISION_THRESHOLDS = config.DECISION_THRESHOLDS


class BacktestEngine:
    """策略回测引擎"""

    def __init__(self, initial_capital: float = 1_000_000,
                 min_lookback: int = 20):
        """
        :param initial_capital: 初始资金
        :param min_lookback: 决策引擎需要的最小历史数据量（默认20，与决策引擎一致）
        """
        self.initial_capital = initial_capital
        self.min_lookback = min_lookback
        self.engine = InvestmentDecision()

    def run(self, df: pd.DataFrame) -> dict:
        """
        执行回测。
        :param df: 完整历史K线 DataFrame (date, open, high, low, close, volume)
        :return: 回测结果 dict
        """
        df = df.copy().reset_index(drop=True)
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        if len(df) < self.min_lookback + 10:
            return {"error": f"数据不足: 需要至少 {self.min_lookback + 10} 条，"
                    f"当前 {len(df)} 条"}

        trades = []
        signals = []
        position = 0       # 0=空仓, 1=持仓
        entry_price = 0.0
        capital = self.initial_capital
        equity_curve = []

        buy_threshold = DECISION_THRESHOLDS["buy"]
        sell_threshold = DECISION_THRESHOLDS["sell"]

        for i in range(self.min_lookback, len(df) - 1):
            window = df.iloc[:i + 1]
            today = df.iloc[i]
            tomorrow = df.iloc[i + 1]
            date_str = str(today["date"])

            # 用滚动窗口生成信号
            result = self.engine.analyze(window)
            score = result.get("final_score", 0)
            action_label = result.get("action", {}).get("action", "")

            signals.append({
                "date": date_str,
                "close": float(today["close"]),
                "score": score,
                "action": action_label,
                "position": position,
            })

            # 交易逻辑：下一日开盘价成交
            next_open = float(tomorrow["open"])

            if position == 0 and score >= buy_threshold:
                # 买入
                position = 1
                entry_price = next_open
                trades.append({
                    "type": "buy",
                    "date": str(tomorrow["date"]),
                    "price": next_open,
                    "score": score,
                })
            elif position == 1 and score <= sell_threshold:
                # 卖出
                position = 0
                pnl_pct = (next_open - entry_price) / entry_price
                capital *= (1 + pnl_pct)
                trades.append({
                    "type": "sell",
                    "date": str(tomorrow["date"]),
                    "price": next_open,
                    "entry_price": entry_price,
                    "pnl_pct": pnl_pct,
                    "score": score,
                })
                entry_price = 0.0

            # 记录权益曲线
            if position == 1:
                unrealized = (float(today["close"]) - entry_price) / entry_price
                equity = capital * (1 + unrealized)
            else:
                equity = capital
            equity_curve.append({
                "date": date_str,
                "equity": equity,
            })

        # 如果最后一天还持仓，按收盘价平仓
        if position == 1:
            last_close = float(df.iloc[-1]["close"])
            pnl_pct = (last_close - entry_price) / entry_price
            capital *= (1 + pnl_pct)
            trades.append({
                "type": "sell(close)",
                "date": str(df.iloc[-1]["date"]),
                "price": last_close,
                "entry_price": entry_price,
                "pnl_pct": pnl_pct,
                "score": 0,
            })

        return self._compute_metrics(trades, equity_curve, df)

    def _compute_metrics(self, trades: list, equity_curve: list,
                         df: pd.DataFrame) -> dict:
        """计算回测统计指标"""
        # 基本信息
        start_date = str(df.iloc[self.min_lookback]["date"])
        end_date = str(df.iloc[-1]["date"])

        # 权益曲线
        equities = pd.Series([e["equity"] for e in equity_curve])
        if equities.empty:
            return {"error": "回测期间无有效数据"}

        final_capital = float(equities.iloc[-1])
        total_return = (final_capital - self.initial_capital) / self.initial_capital

        # 年化收益
        trading_days = len(equities)
        annual_return = (1 + total_return) ** (252 / max(trading_days, 1)) - 1

        # 最大回撤
        peak = equities.cummax()
        drawdown = (equities - peak) / peak
        max_drawdown = float(drawdown.min())

        # 交易统计
        sell_trades = [t for t in trades if t["type"] in ("sell", "sell(close)")]
        total_trades = len(sell_trades)
        wins = [t for t in sell_trades if t.get("pnl_pct", 0) > 0]
        losses = [t for t in sell_trades if t.get("pnl_pct", 0) <= 0]
        win_rate = len(wins) / total_trades if total_trades > 0 else 0

        avg_win = np.mean([t["pnl_pct"] for t in wins]) if wins else 0
        avg_loss = np.mean([abs(t["pnl_pct"]) for t in losses]) if losses else 0
        pnl_ratio = avg_win / avg_loss if avg_loss > 0 else float("inf")

        # 夏普比率 (简化: 用日收益率)
        daily_returns = equities.pct_change().dropna()
        sharpe = 0.0
        if len(daily_returns) > 1 and daily_returns.std() > 0:
            sharpe = float(daily_returns.mean() / daily_returns.std() * np.sqrt(252))

        return {
            "backtest_period": f"{start_date} ~ {end_date}",
            "trading_days": trading_days,
            "initial_capital": self.initial_capital,
            "final_capital": round(final_capital, 2),
            "total_return": total_return,
            "annual_return": annual_return,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe,
            "total_trades": total_trades,
            "win_rate": win_rate,
            "avg_win": float(avg_win),
            "avg_loss": float(avg_loss),
            "pnl_ratio": pnl_ratio,
            "trades": trades,
        }


def format_backtest_report(result: dict, code: str = "",
                           name: str = "") -> str:
    """格式化回测报告"""
    if "error" in result:
        return f"⚠️ 回测失败: {result['error']}"

    sep = "=" * 60
    lines = [sep]
    lines.append("📊 策略回测报告")
    if code:
        lines.append(f"🎯 标的: {name} ({code})" if name else f"🎯 标的: {code}")
    lines.append(f"📅 回测区间: {result['backtest_period']}")
    lines.append(f"📈 交易天数: {result['trading_days']}")
    lines.append(sep)

    lines.append("")
    lines.append("💰 【收益概览】")
    lines.append(f"   初始资金: ¥{result['initial_capital']:,.0f}")
    lines.append(f"   最终资金: ¥{result['final_capital']:,.2f}")
    tr = result['total_return']
    ar = result['annual_return']
    lines.append(f"   总收益率: {'+' if tr > 0 else ''}{tr:.2%}")
    lines.append(f"   年化收益: {'+' if ar > 0 else ''}{ar:.2%}")
    lines.append(f"   最大回撤: {result['max_drawdown']:.2%}")
    lines.append(f"   夏普比率: {result['sharpe_ratio']:.2f}")

    lines.append("")
    lines.append("📋 【交易统计】")
    lines.append(f"   总交易次数: {result['total_trades']}")
    lines.append(f"   胜率: {result['win_rate']:.1%}")
    lines.append(f"   平均盈利: {result['avg_win']:.2%}")
    lines.append(f"   平均亏损: {result['avg_loss']:.2%}")
    pr = result['pnl_ratio']
    lines.append(f"   盈亏比: {pr:.2f}" if pr != float("inf") else "   盈亏比: ∞")

    # 最近几笔交易
    trades = result.get("trades", [])
    sell_trades = [t for t in trades if t["type"] in ("sell", "sell(close)")]
    if sell_trades:
        lines.append("")
        lines.append("📝 【最近交易记录】")
        for t in sell_trades[-5:]:
            pnl = t.get("pnl_pct", 0)
            icon = "🟢" if pnl > 0 else "🔴"
            lines.append(
                f"   {icon} {t['date']}  "
                f"买入={t.get('entry_price', 0):.2f} → 卖出={t['price']:.2f}  "
                f"收益={pnl:+.2%}")

    lines.append("")
    lines.append("⚠️ 回测结果基于历史数据，不代表未来收益，仅供参考。")
    lines.append(sep)
    return "\n".join(lines)
