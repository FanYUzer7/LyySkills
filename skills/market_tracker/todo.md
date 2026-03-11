# Market Tracker Skill - 功能增强 TODO

> Code Review 后的功能完备性建议，按优先级排序
> 
> **✅ 全部 11 项功能已实现并提交 (2026-03-11)**

## 高优先级

### ✅ 1. 离线测试模式 (`--test` / `--dry-run`) — commit 6013d6c
- `analyze --code 600519 --type stock --test` 从 test_data 加载数据

### ✅ 2. 依赖检查/自动安装 — commit 1b9662a
- `__main__.py` 入口自动检查 akshare/pandas/numpy，缺失时提示安装命令

### ✅ 3. 错误处理增强 — commit 5fd2f0e
- `errors.py` 统一错误码体系，区分网络/API/代码无效/数据不足等场景

## 中优先级

### ✅ 4. 模拟实盘回测 — commit 257af70
- `backtest` 命令，固定仓位模型，输出总收益/年化/最大回撤/夏普/胜率/盈亏比

### ✅ 5. 多周期分析 — commit 4519675
- `--period daily/weekly/monthly` 参数，期货/黄金自动回退到日线

### ✅ 6. 基于 ATR 的动态止损/止盈 — commit 7933412
- `close - 2×ATR` 止损，`close + 3×ATR` 止盈

### ✅ 7. 信号变化检测 (monitor 增强) — commit d956dad
- monitor 模式对比上次信号，仅在变化时高亮提醒

## 低优先级

### ✅ 8. 历史决策追踪 — commit 0242ae4
- SQLite `decisions` 表，`history` 命令查询历史决策

### ✅ 9. 数据导出 CSV — commit c81c2de
- `export --code CODE --type TYPE` 导出含全部技术指标的 CSV

### ✅ 10. CLI 参数覆盖指标配置 — commit 3b23786
- `--rsi-period`, `--macd-fast/slow/signal`, `--kdj-period`, `--bb-period/std` 等

### ✅ 11. 与 finance_news skill 联动 — commit 1603698
- `full-report` 命令，技术分析 + 资讯情绪分析合并报告
