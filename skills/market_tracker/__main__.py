"""Market Tracker - 实时市场跟踪与投资决策"""
import sys


def _check_dependencies():
    """检查必需依赖是否已安装，缺失时给出友好提示"""
    missing = []
    for pkg, import_name in [("akshare", "akshare"), ("pandas", "pandas"), ("numpy", "numpy")]:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"❌ 缺少依赖: {', '.join(missing)}")
        print(f"   请运行: pip install {' '.join(missing)}")
        print(f"   或执行: pip install -r requirements.txt")
        sys.exit(1)


_check_dependencies()

from .tracker import main

if __name__ == "__main__":
    main()
