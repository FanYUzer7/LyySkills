# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This workspace contains custom skills for Claude Code, focused on financial market news analysis for Chinese domestic markets (A股, 期货, 黄金, etc.).

## Commands

### Running Financial News Analysis Skill

**搜索并分析金融市场资讯：**

1. 使用 minimax MCP 搜索资讯：
   ```
   使用 mcp__MiniMax__web_search 工具搜索
   - A股: "A股 今日行情", "A股 市场分析", "A股 板块轮动"
   - 期货: "期货 市场行情", "大宗商品 期货", "原油 期货"
   - 黄金: "黄金 沪金 行情", "金银 期货走势"
   ```

2. 调用分析器分析搜索结果：
   ```bash
   echo '<JSON搜索结果>' | python3 skills/finance_news/analyzer.py
   ```
   - 输入：通过 stdin 传递 JSON 格式的搜索结果
   - 输出：格式化市场分析报告（文本或 JSON）
   - 支持 `--format json` 输出结构化数据
   - 支持 `--file <path>` 从文件读取

### 测试分析器

```bash
# 使用测试数据测试分析器
python3 skills/finance_news/analyzer.py --file skills/finance_news/test_data.json
```

## Project Structure

```
MySkills/
├── CLAUDE.md                    # 本文件
└── skills/
    └── finance_news/
        ├── SKILL.md              # Skill定义和使用说明
        ├── analyzer.py           # 资讯分析器（核心）
        ├── config.py             # 搜索关键词配置
        ├── requirements.txt      # 依赖声明
        └── test_data.json        # 测试数据
```

## Architecture

### 资讯分析器 (analyzer.py)

核心组件，功能包括：
- **市场情绪分析** - 基于关键词统计判断偏多/偏空/震荡
- **关键事件提取** - 识别原油波动、科技股反弹、周期股回调、政策影响等地缘/市场事件
- **板块表现分析** - 分析科技成长、新能源、周期股、金融、消费、高端制造等板块
- **报告生成** - 输出格式化的分析报告

### 使用流程

1. 用户请求金融市场资讯
2. 使用 minimax MCP 搜索获取原始资讯
3. 将搜索结果（JSON格式）传给 analyzer.py
4. analyzer.py 输出分析报告
5. 展示给用户

### 依赖

- Python 3.9+（仅使用标准库，无第三方依赖）
- minimax MCP (用于网络搜索)

## Skill: 金融市场资讯分析

### 触发条件

当用户请求以下内容时触发：
- 获取金融市场资讯
- 分析A股/期货/黄金市场
- 了解今日市场行情
- 获取市场快讯/分析报告

### 分析维度

1. **市场情绪** - 整体偏多/偏空/震荡 + 置信度
2. **关键事件** - 影响市场的重大事件摘要
3. **板块表现** - 各行业板块涨跌分析
4. **分析总结** - 基于事实的投资参考建议

### 输出示例

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
   中性消息: 0 条

📌 【关键事件摘要】
   1. [科技股反弹] A股三大指数集体反弹...
   ...

📈 【板块表现分析】
   ⬆️ 科技成长: 偏多
   ⬇️ 周期股: 偏空

💡 【分析总结】
   市场情绪偏多，科技成长板块表现活跃...

⚠️ 【风险提示】
   本分析基于公开资讯，仅供参考...
============================================================
```
