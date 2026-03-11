"""
市场跟踪器 - 统一错误处理
定义错误码和用户友好的错误消息
"""


class MarketTrackerError:
    """统一错误结构"""

    # 错误码常量
    NETWORK_ERROR = "NETWORK_ERROR"
    API_CHANGED = "API_CHANGED"
    INVALID_CODE = "INVALID_CODE"
    DATA_INSUFFICIENT = "DATA_INSUFFICIENT"
    DATA_NOT_FOUND = "DATA_NOT_FOUND"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    UNKNOWN = "UNKNOWN"

    # 用户友好消息模板
    _MESSAGES = {
        NETWORK_ERROR: "网络请求失败，请检查网络连接",
        API_CHANGED: "数据接口可能已变更，请更新 akshare 版本",
        INVALID_CODE: "资产代码无效或不存在",
        DATA_INSUFFICIENT: "历史数据不足（至少需要20个交易日）",
        DATA_NOT_FOUND: "未找到该标的数据",
        FILE_NOT_FOUND: "文件不存在",
        UNKNOWN: "未知错误",
    }

    @classmethod
    def make(cls, code: str, error_code: str, detail: str = "") -> dict:
        """
        构造统一错误 dict。
        :param code: 资产代码
        :param error_code: 错误码常量
        :param detail: 详细错误信息（技术细节）
        """
        msg = cls._MESSAGES.get(error_code, cls._MESSAGES[cls.UNKNOWN])
        return {
            "error": msg,
            "error_code": error_code,
            "code": code,
            "detail": detail,
        }

    @classmethod
    def classify_exception(cls, e: Exception) -> str:
        """根据异常类型推断错误码"""
        err_str = str(e).lower()

        # 网络错误
        if any(kw in type(e).__name__.lower() for kw in
               ("connection", "timeout", "url", "http", "ssl")):
            return cls.NETWORK_ERROR
        if any(kw in err_str for kw in
               ("connection", "timeout", "timed out", "网络", "unreachable")):
            return cls.NETWORK_ERROR

        # API 变更
        if any(kw in err_str for kw in
               ("keyerror", "column", "参数", "deprecated", "该接口")):
            return cls.API_CHANGED
        if isinstance(e, KeyError):
            return cls.API_CHANGED

        # 数据未找到
        if any(kw in err_str for kw in ("empty", "no data", "not found", "无数据")):
            return cls.DATA_NOT_FOUND

        return cls.UNKNOWN


def format_error_for_display(err: dict) -> str:
    """将错误 dict 转为用户友好的显示文本"""
    msg = err.get("error", "未知错误")
    code = err.get("code", "")
    error_code = err.get("error_code", "")
    detail = err.get("detail", "")

    lines = [f"⚠️ {msg}"]
    if code:
        lines[0] += f" [{code}]"
    if detail:
        lines.append(f"   详情: {detail}")
    if error_code:
        lines.append(f"   错误码: {error_code}")
    return "\n".join(lines)
