"""
市场跟踪器 - SQLite 数据库管理
封装 sqlite3 + pandas 交互，管理历史K线数据的存储与增量更新
"""

import sqlite3
import os
from datetime import datetime

import pandas as pd

from .config import DB_PATH


class MarketDB:
    """SQLite 数据库管理器，存储历史K线数据"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._ensure_tables()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _ensure_tables(self):
        """创建表结构（如不存在）"""
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS kline_daily (
                    code       TEXT    NOT NULL,
                    date       TEXT    NOT NULL,
                    open       REAL,
                    high       REAL,
                    low        REAL,
                    close      REAL,
                    volume     REAL,
                    turnover   REAL,
                    asset_type TEXT,
                    PRIMARY KEY (code, date)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_kline_code_date
                ON kline_daily (code, date)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS kline_meta (
                    code          TEXT PRIMARY KEY,
                    asset_type    TEXT,
                    last_update   TEXT,
                    earliest_date TEXT,
                    latest_date   TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS decisions (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    code       TEXT    NOT NULL,
                    asset_type TEXT,
                    timestamp  TEXT    NOT NULL,
                    action     TEXT,
                    score      REAL,
                    price      REAL,
                    stop_loss  REAL,
                    take_profit REAL,
                    period     TEXT DEFAULT 'daily'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_decisions_code_ts
                ON decisions (code, timestamp)
            """)
            conn.commit()

    # ----------------------------------------------------------
    # 写入
    # ----------------------------------------------------------
    def save_kline(self, code: str, df: pd.DataFrame, asset_type: str = "stock"):
        """
        写入K线数据到 SQLite。自动去重（INSERT OR REPLACE）。
        df 需要包含列: date, open, high, low, close, volume
        可选列: turnover
        """
        if df is None or df.empty:
            return

        df = df.copy()
        # 统一列名
        col_map = {
            "日期": "date", "开盘": "open", "最高": "high",
            "最低": "low", "收盘": "close", "成交量": "volume",
            "成交额": "turnover",
        }
        df.rename(columns={k: v for k, v in col_map.items() if k in df.columns},
                  inplace=True)

        required = ["date", "open", "high", "low", "close", "volume"]
        for col in required:
            if col not in df.columns:
                raise ValueError(f"DataFrame 缺少必需列: {col}")

        if "turnover" not in df.columns:
            df["turnover"] = 0.0

        df["code"] = code
        df["asset_type"] = asset_type
        df["date"] = df["date"].astype(str)

        cols = ["code", "date", "open", "high", "low", "close",
                "volume", "turnover", "asset_type"]
        save_df = df[cols]

        with self._get_conn() as conn:
            # INSERT OR REPLACE 去重
            save_df.to_sql("kline_daily", conn, if_exists="append",
                           index=False, method=_insert_or_replace)
            # 更新 meta
            dates = save_df["date"]
            conn.execute("""
                INSERT OR REPLACE INTO kline_meta
                (code, asset_type, last_update, earliest_date, latest_date)
                VALUES (?, ?, ?, ?, ?)
            """, (
                code, asset_type,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                str(dates.min()), str(dates.max()),
            ))
            conn.commit()

    # ----------------------------------------------------------
    # 读取
    # ----------------------------------------------------------
    def load_kline(self, code: str, start_date: str = None,
                   end_date: str = None) -> pd.DataFrame:
        """
        从 SQLite 加载K线数据，返回 DataFrame。
        可选 start_date / end_date 过滤日期范围。
        """
        query = "SELECT * FROM kline_daily WHERE code = ?"
        params: list = [code]

        if start_date:
            query += " AND date >= ?"
            params.append(str(start_date))
        if end_date:
            query += " AND date <= ?"
            params.append(str(end_date))

        query += " ORDER BY date ASC"

        with self._get_conn() as conn:
            df = pd.read_sql(query, conn, params=params)

        if not df.empty:
            numeric_cols = ["open", "high", "low", "close", "volume", "turnover"]
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    def get_latest_date(self, code: str) -> str | None:
        """获取某标的已缓存的最新日期"""
        with self._get_conn() as conn:
            cur = conn.execute(
                "SELECT latest_date FROM kline_meta WHERE code = ?", (code,))
            row = cur.fetchone()
        return row[0] if row else None

    def delete_kline(self, code: str):
        """删除某标的全部历史数据"""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM kline_daily WHERE code = ?", (code,))
            conn.execute("DELETE FROM kline_meta WHERE code = ?", (code,))
            conn.commit()

    def list_cached_codes(self) -> pd.DataFrame:
        """列出所有已缓存的标的"""
        with self._get_conn() as conn:
            return pd.read_sql("SELECT * FROM kline_meta ORDER BY code", conn)

    # ----------------------------------------------------------
    # 决策追踪
    # ----------------------------------------------------------
    def save_decision(self, code: str, asset_type: str, timestamp: str,
                      action: str, score: float, price: float,
                      stop_loss: float = 0, take_profit: float = 0,
                      period: str = "daily"):
        """记录一次分析决策"""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO decisions
                (code, asset_type, timestamp, action, score, price,
                 stop_loss, take_profit, period)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (code, asset_type, timestamp, action, score, price,
                  stop_loss, take_profit, period))
            conn.commit()

    def load_decisions(self, code: str = None,
                       limit: int = 50) -> pd.DataFrame:
        """查询决策历史"""
        query = "SELECT * FROM decisions"
        params: list = []
        if code:
            query += " WHERE code = ?"
            params.append(code)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        with self._get_conn() as conn:
            return pd.read_sql(query, conn, params=params)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def _insert_or_replace(table, conn, keys, data_iter):
    """pandas to_sql 的自定义 method，实现 INSERT OR REPLACE"""
    cols = ", ".join(keys)
    placeholders = ", ".join(["?"] * len(keys))
    sql = f"INSERT OR REPLACE INTO {table.name} ({cols}) VALUES ({placeholders})"
    data = list(data_iter)
    conn.executemany(sql, data)
