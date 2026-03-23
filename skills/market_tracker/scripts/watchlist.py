"""
市场跟踪器 - 自选列表管理
支持添加/删除/查询/分组，JSON 持久化

支持独立运行:
    python scripts/watchlist.py add --code 600519 --name 茅台 --type stock
    python scripts/watchlist.py list
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
from datetime import datetime

import config
from utils import parse_args

ASSET_TYPES = config.ASSET_TYPES
ASSET_TYPE_NAMES = config.ASSET_TYPE_NAMES
WATCHLIST_PATH = config.WATCHLIST_PATH


class Watchlist:
    """自选列表管理器"""

    def __init__(self, path: str = WATCHLIST_PATH):
        self.path = path
        self.items: dict[str, dict] = {}
        self.load()

    # ----------------------------------------------------------
    # CRUD
    # ----------------------------------------------------------
    def add(self, code: str, name: str, asset_type: str,
            group: str = "默认") -> dict:
        """
        添加资产到自选列表。
        :param code: 资产代码（如 600519、000300、AU0 等）
        :param name: 名称（如 贵州茅台）
        :param asset_type: stock/index/etf/futures/gold
        :param group: 分组名称（默认: "默认"）
        :return: 添加的条目
        """
        if asset_type not in ASSET_TYPES:
            raise ValueError(
                f"不支持的资产类型 '{asset_type}'，"
                f"可选: {', '.join(ASSET_TYPES)}")

        code = code.strip()
        entry = {
            "code": code,
            "name": name.strip(),
            "asset_type": asset_type,
            "group": group.strip(),
            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.items[code] = entry
        self.save()
        return entry

    def remove(self, code: str) -> bool:
        """移除资产，返回是否成功"""
        code = code.strip()
        if code in self.items:
            del self.items[code]
            self.save()
            return True
        return False

    def clear_all(self) -> int:
        """
        清空整个跟踪列表，返回清空的标的数量。
        """
        count = len(self.items)
        self.items.clear()
        self.save()
        return count

    def get(self, code: str) -> dict | None:
        """获取单个资产信息"""
        return self.items.get(code.strip())

    def list_all(self, group: str = None,
                 asset_type: str = None) -> list[dict]:
        """
        列出自选，可按分组和/或资产类型过滤。
        """
        result = list(self.items.values())
        if group:
            result = [i for i in result if i["group"] == group]
        if asset_type:
            result = [i for i in result if i["asset_type"] == asset_type]
        return result

    def list_groups(self) -> list[str]:
        """列出所有分组名称"""
        return sorted({i["group"] for i in self.items.values()})

    def count(self) -> int:
        return len(self.items)

    # ----------------------------------------------------------
    # 持久化
    # ----------------------------------------------------------
    def save(self):
        """保存到 JSON 文件"""
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        data = {
            "version": 1,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "items": self.items,
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self):
        """从 JSON 文件加载"""
        if not os.path.exists(self.path):
            self.items = {}
            return
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.items = data.get("items", {})

    # ----------------------------------------------------------
    # 格式化输出
    # ----------------------------------------------------------
    def format_table(self, items: list[dict] = None) -> str:
        """格式化为表格文本"""
        if items is None:
            items = self.list_all()
        if not items:
            return "  (空)"

        lines = []
        lines.append(f"  {'代码':<12}{'名称':<14}{'类型':<10}{'分组':<10}{'添加时间'}")
        lines.append("  " + "-" * 65)
        for i in items:
            type_name = ASSET_TYPE_NAMES.get(i["asset_type"], i["asset_type"])
            lines.append(
                f"  {i['code']:<12}{i['name']:<14}{type_name:<10}"
                f"{i['group']:<10}{i.get('added_at', '')}")
        return "\n".join(lines)


# ============================================================
# CLI 入口
# ============================================================
def _cli():
    """命令行入口: python -m skills.market_tracker.watchlist <command> [args]"""
    if len(sys.argv) < 2:
        print("用法:")
        print("  python -m skills.market_tracker.watchlist add --code CODE --name NAME --type TYPE [--group GROUP]")
        print("  python -m skills.market_tracker.watchlist remove --code CODE")
        print("  python -m skills.market_tracker.watchlist list [--group GROUP] [--type TYPE]")
        sys.exit(1)

    wl = Watchlist()
    cmd = sys.argv[1]
    args = parse_args(sys.argv[2:])

    if cmd == "add":
        code = args.get("code", "")
        name = args.get("name", "")
        asset_type = args.get("type", "stock")
        group = args.get("group", "默认")
        if not code or not name:
            print("错误: --code 和 --name 为必填参数")
            sys.exit(1)
        entry = wl.add(code, name, asset_type, group)
        print(f"✅ 已添加: {entry['name']} ({entry['code']}) [{ASSET_TYPE_NAMES.get(asset_type, asset_type)}]")

    elif cmd == "remove":
        code = args.get("code", "")
        if not code:
            print("错误: --code 为必填参数")
            sys.exit(1)
        if wl.remove(code):
            print(f"✅ 已移除: {code}")
        else:
            print(f"⚠️ 未找到: {code}")

    elif cmd == "list":
        group = args.get("group")
        asset_type = args.get("type")
        items = wl.list_all(group=group, asset_type=asset_type)
        print(f"📋 自选列表 ({len(items)} 个)")
        print(wl.format_table(items))

    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    _cli()
