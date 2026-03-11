# Skill: 实时市场跟踪与投资决策 (Market Tracker)

## 环境要求与安装

### 前置条件
- **Python >= 3.10**（代码使用了 `str | dict` 等联合类型语法）
- pip 包管理器

### 安装依赖

```bash
pip install -r skills/market_tracker/requirements.txt
```

> 启动时会自动检查 akshare/pandas/numpy 是否安装，缺失时打印安装命令提示。

### 工作目录

所有命令需在包含 `skills/` 目录的**父目录**下执行，确保 Python 能正确解析 `skills.market_tracker` 包路径。

```bash
# 假设目录结构如下:
# /path/to/workspace/
# └── skills/
#     └── market_tracker/
#         ├── __init__.py
#         ├── tracker.py
#         └── ...

cd /path/to/workspace
python3 -m skills.market_tracker.tracker <command>
```

### 快速验证安装

```bash
# 离线测试模式（无需网络，使用内置测试数据）
python3 -m skills.market_tracker.tracker analyze --code 600519 --type stock --test

# 查看帮助
python3 -m skills.market_tracker.tracker
```

## 触发条件

当用户请求以下内容时触发此 skill：
- 添加/删除/查看自选股（自选列表/持仓跟踪）
- 分析某只股票/指数/ETF/期货/黄金的走势
- 获取实时行情或市场概览
- 请求投资决策建议
- 要求基于技术指标分析
- 回测策略、查看历史决策、导出数据
- 技术面+资讯面综合分析
- 定时监控市场

**关键词匹配**: 自选、持仓、跟踪、分析、行情、K线、技术指标、买卖信号、投资决策、市场概览、MACD、RSI、KDJ、布林带、均线、回测、止损、止盈、导出、综合报告

## 资产类型支持

| 类型 | --type 值 | 代码格式示例 |
|------|----------|-------------|
| A股个股 | stock | 600519, 000001 |
| 指数 | index | 000300, 399001 |
| ETF基金 | etf | 510300, 159915 |
| 期货 | futures | AU0, CU0, IF0 |
| 黄金/贵金属 | gold | AU0, Au99.99 |

## 命令参考

### 通用选项

| 选项 | 说明 | 适用命令 |
|------|------|---------|
| `--format json` | JSON 格式输出（默认 text） | analyze, analyze-all, overview, backtest, history, full-report |
| `--test` | 离线测试模式，使用本地测试数据 | analyze, backtest, export, full-report |
| `--period PERIOD` | K线周期: daily(默认)/weekly/monthly | analyze, backtest, export, full-report |

> 期货/黄金仅支持日线，指定其他周期时自动回退至 daily。

### 指标参数覆盖（可选，适用于所有分析命令）

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--rsi-period N` | RSI 周期 | 14 |
| `--macd-fast N` | MACD 快线 | 12 |
| `--macd-slow N` | MACD 慢线 | 26 |
| `--macd-signal N` | MACD 信号线 | 9 |
| `--atr-period N` | ATR 周期 | 14 |
| `--adx-period N` | ADX 周期 | 14 |
| `--bb-period N` | 布林带周期 | 20 |
| `--ma-periods 5,20,60` | 均线周期列表（逗号分隔） | 5,20,60 |

### 1. 自选列表管理

```bash
# 添加到自选
python3 -m skills.market_tracker.tracker watchlist add --code 600519 --name 贵州茅台 --type stock --group 核心持仓

# 移除
python3 -m skills.market_tracker.tracker watchlist remove --code 600519

# 查看全部
python3 -m skills.market_tracker.tracker watchlist list

# 按组/类型过滤
python3 -m skills.market_tracker.tracker watchlist list --group 核心持仓
python3 -m skills.market_tracker.tracker watchlist list --type futures
```

### 2. 单标的分析

```bash
# 文本格式报告
python3 -m skills.market_tracker.tracker analyze --code 600519 --type stock

# JSON 格式
python3 -m skills.market_tracker.tracker analyze --code 600519 --type stock --format json

# 周线分析
python3 -m skills.market_tracker.tracker analyze --code 600519 --type stock --period weekly

# 离线测试模式
python3 -m skills.market_tracker.tracker analyze --code 600519 --type stock --test

# 自定义指标参数
python3 -m skills.market_tracker.tracker analyze --code 600519 --type stock --rsi-period 7 --macd-fast 10
```

### 3. 全自选批量分析

```bash
python3 -m skills.market_tracker.tracker analyze-all
python3 -m skills.market_tracker.tracker analyze-all --format json
```

### 4. 市场概览

```bash
python3 -m skills.market_tracker.tracker overview
python3 -m skills.market_tracker.tracker overview --format json
```

### 5. 定时监控（含信号变化检测）

```bash
# 每5分钟扫描一次（默认300秒）
python3 -m skills.market_tracker.tracker monitor --interval 300
```

> 自动对比上轮扫描结果，信号变化时高亮提醒（如"从持有变为买入"）。

### 6. 策略回测

```bash
# 基于历史K线回测决策信号
python3 -m skills.market_tracker.tracker backtest --code 600519 --type stock

# 使用测试数据回测
python3 -m skills.market_tracker.tracker backtest --code 600519 --type stock --test

# JSON 输出
python3 -m skills.market_tracker.tracker backtest --code 600519 --type stock --format json
```

回测采用固定仓位模型（信号买入 → 下一日开盘价成交），输出指标：
- 总收益率、年化收益率
- 最大回撤
- 夏普比率
- 胜率、盈亏比
- 逐笔交易明细

### 7. 历史决策查询

```bash
# 查看所有标的的决策记录（默认最近20条）
python3 -m skills.market_tracker.tracker history

# 按标的过滤
python3 -m skills.market_tracker.tracker history --code 600519

# 指定条数
python3 -m skills.market_tracker.tracker history --code 600519 --limit 50

# JSON 输出
python3 -m skills.market_tracker.tracker history --format json
```

> 每次 `analyze` 执行（非测试模式）会自动将决策结果（操作/得分/价格/止损/止盈）记录到 SQLite。

### 8. 数据导出 CSV

```bash
# 导出K线 + 全部技术指标到 CSV
python3 -m skills.market_tracker.tracker export --code 600519 --type stock

# 指定输出文件
python3 -m skills.market_tracker.tracker export --code 600519 --type stock --output my_data.csv

# 导出周线数据
python3 -m skills.market_tracker.tracker export --code 600519 --type stock --period weekly

# 导出测试数据
python3 -m skills.market_tracker.tracker export --code 600519 --type stock --test
```

> 默认文件名: `{code}_{period}.csv`，包含 OHLCV + 所有技术指标列。

### 9. 综合报告（技术面 + 资讯面）

```bash
# 仅技术分析
python3 -m skills.market_tracker.tracker full-report --code 600519 --type stock

# 结合 finance_news 资讯分析
python3 -m skills.market_tracker.tracker full-report --code 600519 --type stock --news-file news.json

# JSON 输出
python3 -m skills.market_tracker.tracker full-report --code 600519 --type stock --news-file news.json --format json
```

综合报告包含：
- 完整技术分析报告（指标信号 + 量化因子 + 决策建议）
- 资讯情绪分析（市场情绪、关键事件、板块情绪）
- **技术面 + 消息面共振判断**（如"技术面与消息面共振偏多，信号较强"）

`--news-file` 接受 finance_news skill 的 JSON 搜索结果文件。典型工作流：
1. 用 minimax MCP 搜索市场资讯，保存为 JSON
2. 执行 `full-report --news-file` 获取综合分析

## 分析维度

### Layer 1: 经典技术指标信号（权重 60%）

| 指标 | 信号类型 | 说明 |
|------|---------|------|
| 均线排列 | 多/空头排列 | MA5/MA20/MA60 位置关系 |
| MACD | 金叉/死叉/柱状图 | DIF/DEA 交叉 + Histogram 方向 |
| RSI | 超买/超卖/中性 | >70超买, <30超卖（周期可配置） |
| KDJ | 交叉/J值极端 | J>100或J<0为极端 |
| 布林带 | 轨道位置 | 突破上/下轨, 带宽变化 |
| ADX | 趋势强度 | >25有效趋势 |
| 量价配合 | 放量/缩量 | 量比 + 价格方向 |

### Layer 2: 量化因子评分（权重 40%）

| 因子 | 算法 | 权重 |
|------|------|------|
| 动量因子 | 20/60/120日收益率综合 | 40% |
| 波动因子 | 历史波动率 + 最大回撤 | 30% |
| 量价因子 | 量价相关性 + 量能趋势 | 30% |

### 止损/止盈

基于 ATR（Average True Range）动态计算：
- **止损位**: `当前价 - 2 × ATR`
- **止盈位**: `当前价 + 3 × ATR`

## 输出示例

### 分析报告

```
============================================================
📊 投资决策分析报告
📅 2026-03-11 14:30:00 CST
🎯 标的: 贵州茅台 (600519) [A股个股]
📈 K线周期: 日线
============================================================

📈 【实时行情】
   当前价: ¥1,856.00  涨跌幅: +1.25%
   成交量: 2.3万手  成交额: 42.7亿

🔍 【技术指标信号】
   趋势: ⬆️ 多头排列 (MA5>MA20>MA60)
   MACD: 🟢 金叉, 柱状图放大
   RSI: RSI=58.3 中性偏多
   KDJ: KDJ偏多 (K=65, D=58, J=79)
   布林: 中轨上方, 带宽=0.0523
   ADX: ADX=32 有效上升趋势
   量价: 🔥 放量上涨 (量比=1.65)
   市场状态: 上升趋势

📊 【量化因子评分】
   动量因子: +0.68 (20日收益=3.25%)
   波动因子: -0.12 (波动率=18.50%, 近20日最大回撤=-3.20%)
   量价因子: +0.45 (量价相关性=0.356, 量能趋势=+8.50%)
   综合得分: 72/100

💡 【投资决策】
   建议操作: 🟢 买入/加仓
   置信度: 68%  推荐仓位: 50-70%
   支撑位: ¥1,820.00  阻力位: ¥1,900.00
   🛑 止损位: ¥1,799.00 (ATR×2)  🎯 止盈位: ¥1,941.50 (ATR×3)

⚠️ 【风险提示】
   当前波动率: 中等 (ATR=28.50)
   近20日最大回撤: -3.2%
   ⚠ RSI=58.3 接近超买区, 注意短期回调

⚠️ 本分析基于技术指标与量化因子，仅供参考，不构成投资建议。
============================================================
```

### 综合报告（技术 + 资讯）

```
[...技术分析部分同上...]

============================================================
📰 【资讯情绪分析】
============================================================
   市场情绪: 偏多 (置信度: 65%)
   资讯数量: 7 条

📌 【关键事件】
   1. [科技股反弹] A股三大指数集体反弹 科技成长板块领涨
   2. [原油波动] 原油期货价格大幅波动 布伦特原油跌破70美元
   3. [黄金走强] 沪金期货续创新高 避险情绪升温

📈 【板块情绪】
   科技成长: 偏多
   周期股: 偏空
   新能源: 偏空

🔗 【技术面 + 消息面综合】
   ✅ 技术面与消息面共振偏多，信号较强

⚠️ 本综合报告基于技术指标和公开资讯，仅供参考，不构成投资建议。
============================================================
```

## 错误处理

统一错误码体系，区分以下场景：

| 错误码 | 含义 | 典型原因 |
|--------|------|---------|
| NETWORK_ERROR | 网络请求失败 | 无网络连接或超时 |
| API_CHANGED | 数据接口变更 | akshare 版本过旧 |
| INVALID_CODE | 代码无效 | 输入了不存在的证券代码 |
| DATA_INSUFFICIENT | 数据不足 | 新股/新上市标的数据不足20日 |
| DATA_NOT_FOUND | 未找到数据 | 停牌或退市标的 |
| FILE_NOT_FOUND | 文件不存在 | 测试数据文件缺失 |

## 与 finance_news skill 的配合

两个 skill 可独立或联合使用：
- **finance_news**: 基于新闻资讯的**市场情绪分析**（宏观面、事件驱动）
- **market_tracker**: 基于市场数据的**技术面+量化分析**（微观面、数据驱动）

**推荐组合使用方式**:
1. 用 minimax MCP 搜索市场资讯 → 保存为 JSON 文件
2. 执行 `full-report --code CODE --type TYPE --news-file news.json` 获取综合报告
3. 综合报告自动判断技术面与消息面是否共振，辅助投资决策

也可分步使用：
1. 先用 `finance_news` 了解今日市场新闻与情绪
2. 再用 `market_tracker analyze` 对感兴趣的标的做技术面分析

## 数据存储

- **自选列表**: `watchlist.json` (JSON)
- **历史K线**: `market_data.db` (SQLite)
  - 支持增量更新，自动缓存已获取数据
  - 按 `{code}:{period}` 独立缓存不同周期的数据
  - 可用 pandas `read_sql()` 直接查询
- **决策记录**: `market_data.db` 中的 `decisions` 表
  - 字段: code, asset_type, timestamp, action, score, price, stop_loss, take_profit, period
  - 通过 `history` 命令查询
- **数据源**: AKShare (MIT协议, 免费开源, 要求 `>=1.14.0,<2.0.0`)

## 依赖

```
akshare    # 市场数据获取
pandas     # 数据处理
numpy      # 数值计算
```

## 风险免责

⚠️ **本 skill 输出的所有分析和建议仅基于技术指标与量化因子的机械计算，不构成任何投资建议。**
- 技术指标存在滞后性
- 单一指标或因子不足以完全反映市场
- 投资决策需结合基本面、宏观环境、个人风险承受力
- 市场有风险，投资需谨慎
