"""
金融市场资讯 Skill — 搜索关键词配置

供 Agent 或 analyzer.py 使用的关键词与辅助函数。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, List


# ---- 搜索关键词 ----

SEARCH_KEYWORDS: Dict[str, List[str]] = {
    "a股": [
        "A股 今日行情",
        "A股 市场分析 今日",
        "A股 板块轮动 今日",
        "创业板 科创板 今日行情",
        "A股 今日 快讯",
    ],
    "期货": [
        "期货 市场行情 今日",
        "大宗商品 期货 原油",
        "PTA 燃料油 期货走势",
    ],
    "黄金": [
        "黄金 沪金 行情 今日",
        "金银 期货 走势",
        "现货黄金 期货黄金",
    ],
    "综合": [
        "金融 市场 快讯 今日",
        "宏观经济 市场 分析",
        "A股 机构 观点",
    ],
}

MARKET_DISPLAY_NAMES: Dict[str, str] = {
    "a股": "A股市场",
    "期货": "期货市场",
    "黄金": "黄金市场",
    "综合": "金融市场",
}


def build_search_queries(market_type: str = "a股", time_range: str = "今日") -> List[str]:
    """根据市场类型和时间范围构建搜索关键词列表。"""
    time_kw = {"今日": "今日", "本周": "本周", "本月": "本月"}.get(time_range, "")

    if market_type == "综合":
        base = (
            SEARCH_KEYWORDS["a股"][:2]
            + SEARCH_KEYWORDS["期货"][:1]
            + SEARCH_KEYWORDS["黄金"][:1]
            + SEARCH_KEYWORDS["综合"]
        )
    else:
        base = SEARCH_KEYWORDS.get(market_type, SEARCH_KEYWORDS["a股"])

    return [f"{q} {time_kw}".strip() if time_kw not in q else q for q in base]
