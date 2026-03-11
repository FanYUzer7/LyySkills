# Skill: 实时市场跟踪与投资决策 (Market Tracker)

## 触发条件

当用户请求以下内容时触发此 skill：
- 添加/删除/查看自选股（自选列表/持仓跟踪）
- 分析某只股票/指数/ETF/期货/黄金的走势
- 获取实时行情或市场概览
- 请求投资决策建议
- 要求基于技术指标分析
- 定时监控市场

**关键词匹配**: 自选、持仓、跟踪、分析、行情、K线、技术指标、买卖信号、投资决策、市场概览、MACD、RSI、KDJ、布林带、均线

## 资产类型支持

| 类型 | --type 值 | 代码格式示例 |
|------|----------|-------------|
| A股个股 | stock | 600519, 000001 |
| 指数 | index | 000300, 399001 |
| ETF基金 | etf | 510300, 159915 |
| 期货 | futures | AU0, CU0, IF0 |
| 黄金/贵金属 | gold | AU0, Au99.99 |

## 执行流程

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

# JSON 格式（适合进一步处理）
python3 -m skills.market_tracker.tracker analyze --code 600519 --type stock --format json
```

### 3. 全自选批量分析

```bash
python3 -m skills.market_tracker.tracker analyze-all
python3 -m skills.market_tracker.tracker analyze-all --format json
```

### 4. 市场概览

```bash
python3 -m skills.market_tracker.tracker overview
```

### 5. 定时监控

```bash
# 每5分钟扫描一次（默认300秒）
python3 -m skills.market_tracker.tracker monitor --interval 300
```

## 分析维度

### Layer 1: 经典技术指标信号

| 指标 | 信号类型 | 说明 |
|------|---------|------|
| 均线排列 | 多/空头排列 | MA5/MA20/MA60 位置关系 |
| MACD | 金叉/死叉/柱状图 | DIF/DEA 交叉 + Histogram 方向 |
| RSI(14) | 超买/超卖/中性 | >70超买, <30超卖 |
| KDJ | 交叉/J值极端 | J>100或J<0为极端 |
| 布林带 | 轨道位置 | 突破上/下轨, 带宽变化 |
| ADX | 趋势强度 | >25有效趋势 |
| 量价配合 | 放量/缩量 | 量比 + 价格方向 |

### Layer 2: 量化因子评分

| 因子 | 算法 | 权重 |
|------|------|------|
| 动量因子 | 20/60/120日收益率综合 | 40% |
| 波动因子 | 历史波动率 + 最大回撤 | 30% |
| 量价因子 | 量价相关性 + 量能趋势 | 30% |

## 输出示例

```
============================================================
📊 投资决策分析报告
📅 2026-03-11 14:30:00 CST
🎯 标的: 贵州茅台 (600519) [A股个股]
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
   动量因子: +0.68 (20日收益=3.25%; 60日收益=8.12%; 120日收益=12.50%)
   波动因子: -0.12 (波动率=18.50%, 近20日最大回撤=-3.20%)
   量价因子: +0.45 (量价相关性=0.356, 量能趋势=+8.50%)
   综合得分: 72/100

💡 【投资决策】
   建议操作: 🟢 买入/加仓
   置信度: 68%  推荐仓位: 50-70%
   支撑位: ¥1,820.00  阻力位: ¥1,900.00

⚠️ 【风险提示】
   当前波动率: 中等 (ATR=28.50)
   近20日最大回撤: -3.2%
   ⚠ RSI=58.3 接近超买区, 注意短期回调

⚠️ 本分析基于技术指标与量化因子，仅供参考，不构成投资建议。
============================================================
```

## 与 finance_news skill 的配合

两个 skill 独立运行，互不冲突：
- **finance_news**: 基于新闻资讯的**市场情绪分析**（宏观面、事件驱动）
- **market_tracker**: 基于市场数据的**技术面+量化分析**（微观面、数据驱动）

**推荐组合使用方式**:
1. 先用 `finance_news` 了解今日市场新闻与情绪
2. 再用 `market_tracker` 对感兴趣的标的做技术面分析
3. 综合两者做出最终投资判断

## 数据存储

- **自选列表**: `watchlist.json` (JSON)
- **历史K线**: `market_data.db` (SQLite)
  - 支持增量更新，自动缓存已获取数据
  - 可用 pandas `read_sql()` 直接查询
- **数据源**: AKShare (MIT协议, 免费开源)

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
