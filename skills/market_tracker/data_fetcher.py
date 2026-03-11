"""
市场跟踪器 - 数据获取层
统一封装 AKShare，提供实时行情与历史K线获取，配合 db.py 做增量缓存
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

from .config import DEFAULT_HISTORY_DAYS
from .db import MarketDB


class MarketDataFetcher:
    """统一市场数据获取接口，封装 AKShare 各品种 API"""

    def __init__(self, db: MarketDB = None):
        self.db = db or MarketDB()

    # ==========================================================
    # 实时行情
    # ==========================================================
    def get_realtime_quote(self, code: str, asset_type: str) -> dict | None:
        """
        获取单个标的实时行情。
        返回 dict: {name, code, price, change_pct, volume, turnover, high, low, open, ...}
        """
        try:
            if asset_type == "stock":
                return self._realtime_stock(code)
            elif asset_type == "index":
                return self._realtime_index(code)
            elif asset_type == "etf":
                return self._realtime_etf(code)
            elif asset_type == "futures":
                return self._realtime_futures(code)
            elif asset_type == "gold":
                return self._realtime_gold(code)
            else:
                return None
        except Exception as e:
            return {"error": str(e), "code": code}

    def _realtime_stock(self, code: str) -> dict | None:
        df = ak.stock_zh_a_spot_em()
        row = df[df["代码"] == code]
        if row.empty:
            return None
        r = row.iloc[0]
        return {
            "name": r.get("名称", ""),
            "code": code,
            "price": _safe_float(r.get("最新价")),
            "change_pct": _safe_float(r.get("涨跌幅")),
            "change_amt": _safe_float(r.get("涨跌额")),
            "volume": _safe_float(r.get("成交量")),
            "turnover": _safe_float(r.get("成交额")),
            "high": _safe_float(r.get("最高")),
            "low": _safe_float(r.get("最低")),
            "open": _safe_float(r.get("今开")),
            "prev_close": _safe_float(r.get("昨收")),
            "amplitude": _safe_float(r.get("振幅")),
            "turnover_rate": _safe_float(r.get("换手率")),
        }

    def _realtime_index(self, code: str) -> dict | None:
        # 尝试各类指数列表
        for category in ["沪深重要指数", "上证系列指数", "深证系列指数", "中证系列指数"]:
            try:
                df = ak.stock_zh_index_spot_em(symbol=category)
                row = df[df["代码"] == code]
                if not row.empty:
                    r = row.iloc[0]
                    return {
                        "name": r.get("名称", ""),
                        "code": code,
                        "price": _safe_float(r.get("最新价")),
                        "change_pct": _safe_float(r.get("涨跌幅")),
                        "change_amt": _safe_float(r.get("涨跌额")),
                        "volume": _safe_float(r.get("成交量")),
                        "turnover": _safe_float(r.get("成交额")),
                        "high": _safe_float(r.get("最高")),
                        "low": _safe_float(r.get("最低")),
                        "open": _safe_float(r.get("今开")),
                    }
            except Exception:
                continue
        return None

    def _realtime_etf(self, code: str) -> dict | None:
        df = ak.fund_etf_spot_em()
        row = df[df["代码"] == code]
        if row.empty:
            return None
        r = row.iloc[0]
        return {
            "name": r.get("名称", ""),
            "code": code,
            "price": _safe_float(r.get("最新价")),
            "change_pct": _safe_float(r.get("涨跌幅")),
            "volume": _safe_float(r.get("成交量")),
            "turnover": _safe_float(r.get("成交额")),
            "high": _safe_float(r.get("最高")),
            "low": _safe_float(r.get("最低")),
            "open": _safe_float(r.get("今开")),
        }

    def _realtime_futures(self, code: str) -> dict | None:
        # 新浪期货实时行情 — 使用内盘行情
        try:
            df = ak.futures_zh_spot(symbol=code, market="CF")
        except Exception:
            try:
                df = ak.futures_zh_spot(symbol=code, market="FF")
            except Exception:
                return None
        if df is None or df.empty:
            return None
        r = df.iloc[0] if len(df) > 0 else None
        if r is None:
            return None
        return {
            "name": r.get("name", r.get("symbol", code)),
            "code": code,
            "price": _safe_float(r.get("last_price", r.get("current_price"))),
            "change_pct": _safe_float(r.get("change_percent")),
            "volume": _safe_float(r.get("volume")),
            "high": _safe_float(r.get("high")),
            "low": _safe_float(r.get("low")),
            "open": _safe_float(r.get("open")),
        }

    def _realtime_gold(self, code: str) -> dict | None:
        # 使用期货主力合约获取黄金实时数据
        return self._realtime_futures(code)

    # ==========================================================
    # 历史K线
    # ==========================================================
    def get_history_kline(self, code: str, asset_type: str,
                          period: str = "daily",
                          start_date: str = None,
                          end_date: str = None,
                          use_cache: bool = True) -> pd.DataFrame:
        """
        获取历史K线。优先从 SQLite 缓存读取，不足部分从 AKShare 增量拉取。
        返回 DataFrame: date, open, high, low, close, volume, turnover
        """
        today = datetime.now().strftime("%Y%m%d")
        if end_date is None:
            end_date = today
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=DEFAULT_HISTORY_DAYS)).strftime("%Y%m%d")

        # 标准化日期格式
        start_date = start_date.replace("-", "")
        end_date = end_date.replace("-", "")

        # 尝试从缓存获取
        if use_cache:
            cached_latest = self.db.get_latest_date(code)
            if cached_latest:
                cached_latest_clean = cached_latest.replace("-", "")
                if cached_latest_clean >= end_date:
                    # 缓存已覆盖请求范围
                    return self.db.load_kline(
                        code,
                        start_date=_fmt_date_dash(start_date),
                        end_date=_fmt_date_dash(end_date))
                else:
                    # 增量拉取：从缓存最新日期的下一天开始
                    incremental_start = (
                        datetime.strptime(cached_latest_clean, "%Y%m%d")
                        + timedelta(days=1)
                    ).strftime("%Y%m%d")
                    new_df = self._fetch_kline(
                        code, asset_type, period,
                        incremental_start, end_date)
                    if new_df is not None and not new_df.empty:
                        self.db.save_kline(code, new_df, asset_type)
                    return self.db.load_kline(
                        code,
                        start_date=_fmt_date_dash(start_date),
                        end_date=_fmt_date_dash(end_date))

        # 无缓存，全量拉取
        df = self._fetch_kline(code, asset_type, period, start_date, end_date)
        if df is not None and not df.empty:
            self.db.save_kline(code, df, asset_type)
        return self.db.load_kline(
            code,
            start_date=_fmt_date_dash(start_date),
            end_date=_fmt_date_dash(end_date))

    def _fetch_kline(self, code: str, asset_type: str,
                     period: str, start_date: str,
                     end_date: str) -> pd.DataFrame | None:
        """从 AKShare 获取K线原始数据"""
        try:
            if asset_type == "stock":
                return self._fetch_stock_kline(code, period, start_date, end_date)
            elif asset_type == "index":
                return self._fetch_index_kline(code, period, start_date, end_date)
            elif asset_type == "etf":
                return self._fetch_etf_kline(code, period, start_date, end_date)
            elif asset_type == "futures":
                return self._fetch_futures_kline(code, start_date, end_date)
            elif asset_type == "gold":
                return self._fetch_gold_kline(code, start_date, end_date)
            return None
        except Exception as e:
            print(f"⚠️ 获取 {code} K线数据失败: {e}")
            return None

    def _fetch_stock_kline(self, code, period, start_date, end_date):
        df = ak.stock_zh_a_hist(
            symbol=code, period=period,
            start_date=start_date, end_date=end_date, adjust="qfq")
        return _normalize_kline_df(df)

    def _fetch_index_kline(self, code, period, start_date, end_date):
        # 指数代码需要加市场前缀
        prefix = "sh" if code.startswith(("000", "950", "880")) else "sz"
        symbol = f"{prefix}{code}"
        df = ak.stock_zh_index_daily_em(symbol=symbol,
                                         start_date=start_date,
                                         end_date=end_date)
        return _normalize_kline_df(df)

    def _fetch_etf_kline(self, code, period, start_date, end_date):
        df = ak.fund_etf_hist_em(
            symbol=code, period=period,
            start_date=start_date, end_date=end_date, adjust="qfq")
        return _normalize_kline_df(df)

    def _fetch_futures_kline(self, code, start_date=None, end_date=None):
        kwargs = {"symbol": code}
        if start_date:
            kwargs["start_date"] = start_date
        if end_date:
            kwargs["end_date"] = end_date
        df = ak.futures_main_sina(**kwargs)
        return _normalize_kline_df(df)

    def _fetch_gold_kline(self, code, start_date=None, end_date=None):
        # 黄金使用上海金交所或期货主力
        try:
            df = ak.spot_hist_sge(symbol=code)
            df = _normalize_kline_df(df)
            # spot_hist_sge 不支持日期参数，获取后手动过滤
            if df is not None and not df.empty and "date" in df.columns:
                if start_date:
                    df = df[df["date"] >= _fmt_date_dash(start_date)]
                if end_date:
                    df = df[df["date"] <= _fmt_date_dash(end_date)]
            return df
        except Exception:
            return self._fetch_futures_kline(code, start_date, end_date)

    # ==========================================================
    # 市场概览
    # ==========================================================
    def get_market_overview(self) -> list[dict]:
        """获取主要指数概览（上证、深证、创业板、科创50等）"""
        overview = []
        try:
            df = ak.stock_zh_index_spot_em(symbol="沪深重要指数")
            key_indices = ["000001", "399001", "399006", "000688",
                           "000300", "000905"]
            for idx_code in key_indices:
                row = df[df["代码"] == idx_code]
                if not row.empty:
                    r = row.iloc[0]
                    overview.append({
                        "name": r.get("名称", ""),
                        "code": idx_code,
                        "price": _safe_float(r.get("最新价")),
                        "change_pct": _safe_float(r.get("涨跌幅")),
                        "volume": _safe_float(r.get("成交量")),
                        "turnover": _safe_float(r.get("成交额")),
                    })
        except Exception as e:
            overview.append({"error": str(e)})
        return overview


# ==============================================================
# 工具函数
# ==============================================================
def _normalize_kline_df(df: pd.DataFrame) -> pd.DataFrame | None:
    """统一各接口K线数据列名为: date, open, high, low, close, volume, turnover"""
    if df is None or df.empty:
        return None

    col_map = {
        "日期": "date", "开盘": "open", "最高": "high",
        "最低": "low", "收盘": "close", "成交量": "volume",
        "成交额": "turnover",
        # 英文列名可能已经是目标格式
        "date": "date", "open": "open", "high": "high",
        "low": "low", "close": "close", "volume": "volume",
        "turnover": "turnover",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # 尝试更多可能的列名
    alt_map = {
        "trade_date": "date", "vol": "volume", "amount": "turnover",
    }
    df = df.rename(columns={k: v for k, v in alt_map.items()
                            if k in df.columns and v not in df.columns})

    # 确保 date 列存在
    if "date" not in df.columns:
        # 可能用索引作为日期
        if df.index.name and "date" in df.index.name.lower():
            df = df.reset_index()
            df.rename(columns={df.columns[0]: "date"}, inplace=True)
        else:
            # 取第一列作为 date
            df = df.reset_index()
            if "index" in df.columns:
                df.rename(columns={"index": "date"}, inplace=True)

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    if "turnover" not in df.columns:
        df["turnover"] = 0.0

    return df


def _safe_float(val) -> float | None:
    """安全转换为 float"""
    if val is None or val == "" or val == "-":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _fmt_date_dash(date_str: str) -> str:
    """将 YYYYMMDD 转为 YYYY-MM-DD"""
    s = date_str.replace("-", "")
    if len(s) == 8:
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return date_str
