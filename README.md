# LyySkills

Claude Code 自定义技能集，专注于中国金融市场分析（A 股、期货、黄金等）。

## 功能概述

本项目包含两个核心技能：

### 1. 金融市场资讯分析 (finance_news)

- 实时搜索并分析 A 股、期货、黄金市场资讯
- 市场情绪分析（偏多/偏空/震荡）
- 关键事件提取（政策影响、原油波动、科技股异动等）
- 板块表现分析

### 2. 实时市场跟踪与投资决策 (market_tracker)

- 自选股管理（添加、删除、查看）
- 技术指标分析（MACD、RSI、KDJ、布林带、均线等）
- 量化因子评分（动量、波动、量价因子）
- 投资决策建议（买入/卖出/持有）
- 策略回测
- 数据导出（CSV）

## 项目结构

```
LyySkills/
├── CLAUDE.md              # Claude Code 项目配置
├── README.md              # 本文件
├── experience.md          # 使用体验报告
├── knowledge.md           # 知识库
└── skills/
    ├── __init__.py
    ├── finance_news/     # 资讯分析技能
    │   ├── SKILL.md
    │   ├── analyzer.py
    │   ├── config.py
    │   ├── requirements.txt
    │   └── test_data.json
    └── market_tracker/    # 市场跟踪技能
        ├── SKILL.md
        ├── tracker.py
        ├── indicators.py
        ├── requirements.txt
        └── ...
```

## 快速开始

### 环境要求

- Python 3.10+
- minimax MCP（用于网络搜索）

### 安装依赖

```bash
# market_tracker 依赖
pip install -r skills/market_tracker/requirements.txt

# finance_news 仅需 Python 标准库，无需额外安装
```

### 使用方法

#### 金融市场资讯分析

```bash
# 1. 使用 minimax MCP 搜索资讯
# 搜索关键词：A 股 今日行情、期货 市场行情、黄金 沪金 行情

# 2. 分析搜索结果
python3 skills/finance_news/analyzer.py --file search_results.json

# 或输出 JSON 格式
python3 skills/finance_news/analyzer.py --file search_results.json --format json
```

#### 市场跟踪分析

```bash
# 进入项目根目录
cd /path/to/LyySkills

# 分析股票
python3 -m skills.market_tracker.tracker analyze --code 600519 --type stock

# 添加自选
python3 -m skills.market_tracker.tracker watchlist add --code 600519 --name 贵州茅台 --type stock

# 查看自选列表
python3 -m skills.market_tracker.tracker watchlist list

# 市场概览
python3 -m skills.market_tracker.tracker overview

# 导出 K 线数据
python3 -m skills.market_tracker.tracker export --code 600519 --type stock --output data.csv
```

## 资产类型支持

| 类型 | --type 值 | 示例代码 |
|------|----------|---------|
| A 股个股 | stock | 600519, 000001 |
| 指数 | index | 000300, 399001 |
| ETF 基金 | etf | 510300, 159915 |
| 期货 | futures | AU0, CU0, IF0 |
| 黄金/贵金属 | gold | AU0, Au99.99 |

## 输出示例

### 投资决策分析报告

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

📊 【量化因子评分】
   动量因子: +0.68
   综合得分: 72/100

💡 【投资决策】
   建议操作: 🟢 买入/加仓
   置信度: 68%  推荐仓位: 50-70%
   🛑 止损位: ¥1,799.00 (ATR×2)

⚠️ 本分析基于技术指标与量化因子，仅供参考，不构成投资建议。
============================================================
```

### 金融市场资讯分析报告

```
============================================================
📊 金融市场资讯分析报告
📅 生成时间: 2026-03-11 10:00:00
📰 资讯来源: 5 条
============================================================

🌡️ 【市场情绪分析】
   整体情绪: 偏多 (置信度: 60%)
   利好消息: 3 条
   利空消息: 2 条

📌 【关键事件摘要】
   1. [科技股反弹] A股三大指数集体反弹...

📈 【板块表现分析】
   ⬆️ 科技成长: 偏多
   ⬇️ 周期股: 偏空

⚠️ 本分析基于公开资讯，仅供参考，不构成投资建议。
============================================================
```

## 技术栈

- **数据获取**: [AKShare](https://akshare.akfamily.xyz/) - 免费开源的中国金融市场数据接口
- **数据处理**: Pandas, NumPy
- **搜索**: MiniMax MCP
- **存储**: SQLite + JSON

## 注意事项

⚠️ **风险提示**

- 本项目输出的所有分析和建议仅基于技术指标、量化因子或公开资讯
- 不构成任何投资建议，投资决策需结合基本面、宏观环境、个人风险承受力
- 市场有风险，投资需谨慎

## 许可证

MIT License

## 作者

FanYUzer7
