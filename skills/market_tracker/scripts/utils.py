"""
市场跟踪器 - 共享工具函数
提取自多个模块的公共功能：参数解析、格式化函数、JSON序列化等
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ============================================================
# 参数解析
# ============================================================

def parse_args(argv: list[str]) -> dict:
    """
    解析命令行参数，支持 --key value 和 --flag 两种格式。

    Examples:
        parse_args(["--code", "600519", "--verbose", "--type", "stock"])
        # -> {"code": "600519", "verbose": True, "type": "stock"}
    """
    result = {}
    i = 0
    while i < len(argv):
        if argv[i].startswith("--"):
            key = argv[i][2:]
            # Next arg exists and is not another flag -> key-value pair
            if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                result[key] = argv[i + 1]
                i += 2
            else:
                # Boolean flag
                result[key] = True
                i += 1
        else:
            i += 1
    return result


# ============================================================
# 格式化函数
# ============================================================

def fmt_num(val) -> str:
    """格式化数字，保留2位小数"""
    if val is None:
        return "--"
    try:
        return f"{float(val):,.2f}"
    except (ValueError, TypeError):
        return str(val)


def fmt_pct(val) -> str:
    """格式化百分比，带正负号"""
    if val is None:
        return "--"
    try:
        v = float(val)
        sign = "+" if v > 0 else ""
        return f"{sign}{v:.2f}%"
    except (ValueError, TypeError):
        return str(val)


def fmt_vol(val) -> str:
    """格式化成交量（手）"""
    if val is None:
        return "--"
    try:
        v = float(val)
        if v >= 1e8:
            return f"{v / 1e8:.2f}亿手"
        elif v >= 1e4:
            return f"{v / 1e4:.1f}万手"
        return f"{v:.0f}手"
    except (ValueError, TypeError):
        return str(val)


def fmt_money(val) -> str:
    """格式化金额（元）"""
    if val is None:
        return "--"
    try:
        v = float(val)
        if v >= 1e8:
            return f"{v / 1e8:.2f}亿"
        elif v >= 1e4:
            return f"{v / 1e4:.1f}万"
        return f"{v:.0f}"
    except (ValueError, TypeError):
        return str(val)


def fmt_date_dash(date_str: str) -> str:
    """将 YYYYMMDD 转为 YYYY-MM-DD"""
    s = date_str.replace("-", "")
    if len(s) == 8:
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return date_str


def fmt_date_compact(date_str: str) -> str:
    """将 YYYY-MM-DD 转为 YYYYMMDD"""
    return date_str.replace("-", "")


# ============================================================
# JSON 序列化
# ============================================================

def serialize(obj):
    """
    将结果转为 JSON-safe dict，处理 NaN、特殊类型等。
    """
    if isinstance(obj, dict):
        return {k: serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize(i) for i in obj]
    if isinstance(obj, float):
        if obj != obj:  # NaN
            return None
        return round(obj, 6)
    return obj


# ============================================================
# 错误处理辅助
# ============================================================

def safe_float(val) -> float | None:
    """安全转换为 float"""
    if val is None or val == "" or val == "-":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def safe_int(val) -> int | None:
    """安全转换为 int"""
    if val is None or val == "" or val == "-":
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None
