#!/usr/bin/env python3
"""
金融市场资讯分析工具
用于分析中国金融市场的实时资讯，并提供带有事实依据的分析
"""

import json
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional


class FinancialNewsAnalyzer:
    """金融市场资讯分析器"""

    def __init__(self):
        self.news_data: List[Dict[str, Any]] = []

    def load_news(self, news_json: str):
        """加载新闻数据"""
        try:
            data = json.loads(news_json)
            # 处理搜索结果格式
            if isinstance(data, dict) and 'organic' in data:
                self.news_data = data['organic']
            elif isinstance(data, list):
                self.news_data = data
            else:
                self.news_data = [data]
        except json.JSONDecodeError:
            # 如果是字符串列表
            if isinstance(news_json, str) and news_json.startswith('['):
                self.news_data = json.loads(news_json)
            else:
                self.news_data = []

    def analyze_market_sentiment(self) -> Dict[str, Any]:
        """分析市场情绪"""
        if not self.news_data:
            return {"sentiment": "unknown", "confidence": 0, "details": []}

        # 积极关键词：价格涨跌 + 业绩增长 + 政策支持 + 回购
        positive_keywords = [
            '涨', '大涨', '反弹', '上涨', '普涨', '回暖', '涨幅', '收涨', '飙升', '创新高',
            '增长', '同比增长', '净利润增长', '业绩增长', '扭亏', '盈利',
            '支持', '利好', '发展', '改革', '创新',
            '回购', '增持', '定增', '并购', '重组',
            '申购', '发行', '上市'
        ]
        # 消极关键词
        negative_keywords = [
            '跌', '大跌', '下跌', '回调', '走弱', '跌幅', '收跌', '暴跌', '创新低',
            '减少', '下降', '下滑', '亏损', '减持', '解禁',
            '风险', '利空', '制裁', '冲突', '战争'
        ]

        positive_count = 0
        negative_count = 0
        neutral_count = 0

        details = []

        for news in self.news_data:
            title = news.get('title', '')
            snippet = news.get('snippet', '')
            text = title + ' ' + snippet

            pos = sum(1 for kw in positive_keywords if kw in text)
            neg = sum(1 for kw in negative_keywords if kw in text)

            if pos > neg:
                positive_count += 1
                sentiment_type = "利好"
            elif neg > pos:
                negative_count += 1
                sentiment_type = "利空"
            else:
                neutral_count += 1
                sentiment_type = "中性"

            details.append({
                "title": title[:50] + "..." if len(title) > 50 else title,
                "sentiment": sentiment_type,
                "date": news.get('date', '')
            })

        total = len(self.news_data)
        if positive_count > negative_count and positive_count > neutral_count:
            sentiment = "偏多"
            confidence = positive_count / total
        elif negative_count > positive_count and negative_count > neutral_count:
            sentiment = "偏空"
            confidence = negative_count / total
        else:
            sentiment = "震荡"
            confidence = max(positive_count, negative_count) / total if total > 0 else 0

        return {
            "sentiment": sentiment,
            "confidence": round(confidence, 2),
            "positive": positive_count,
            "negative": negative_count,
            "neutral": neutral_count,
            "details": details[:5]  # 返回前5条详情
        }

    def extract_key_events(self) -> List[Dict[str, Any]]:
        """提取关键事件"""
        events = []

        # 定义关键事件模式
        event_patterns = {
            '原油波动': ['原油', '油价', '石油', 'WTI', '布伦特'],
            '科技股反弹': ['科技', '半导体', 'AI', '算力', '创业板', '科创'],
            '周期股回调': ['煤炭', '油气', '化工', '周期'],
            '政策影响': ['宏观', '政策', '央行', '美联储'],
            '地缘政治': ['伊朗', '中东', '地缘', '冲突', '战争'],
        }

        for news in self.news_data:
            text = news.get('title', '') + ' ' + news.get('snippet', '')

            for event_type, keywords in event_patterns.items():
                if any(kw in text for kw in keywords):
                    events.append({
                        "type": event_type,
                        "title": news.get('title', '')[:60],
                        "date": news.get('date', ''),
                        "source": news.get('link', '')
                    })
                    break

        return events[:8]  # 返回前8个关键事件

    def _extract_sector_sentiment(self, text: str, sector_keywords: List[str]) -> str:
        """从文本中提取特定板块的情绪"""
        # 找到板块关键词第一次出现的位置
        first_pos = len(text)
        for kw in sector_keywords:
            pos = text.find(kw)
            if pos != -1 and pos < first_pos:
                first_pos = pos

        if first_pos == len(text):
            return "neutral"

        # 只获取板块关键词之后的文本（最多80个字符），因为新闻通常是"XX板块涨/跌"
        after_sector = text[first_pos:first_pos + 80]

        # 在板块后面的文本中查找涨跌关键词
        positive_kw = ['涨', '大涨', '上涨', '反弹', '飙升', '收涨', '涨幅', '创新高', '拉升', '走强']
        negative_kw = ['跌', '大跌', '下跌', '回调', '走弱', '收跌', '跌幅', '暴跌', '创新低', '下挫']

        pos_count = sum(1 for kw in positive_kw if kw in after_sector)
        neg_count = sum(1 for kw in negative_kw if kw in after_sector)

        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        else:
            return "neutral"

    def analyze_sector_performance(self) -> Dict[str, Any]:
        """分析板块表现"""
        sectors = {
            '科技成长': ['科技', '半导体', 'AI', '算力', '电子', '通信', '计算机', '创业板', '科创', '芯片', '软件'],
            '新能源': ['光伏', '锂电', '新能源', '电池', '电动车', '汽车', '储能'],
            '周期股': ['煤炭', '油气', '石油', '化工', '有色', '钢铁', '建材', 'PTA'],
            '金融': ['银行', '保险', '证券', '金融', '地产'],
            '消费': ['消费', '食品', '饮料', '家电', '医药', '旅游', '零售'],
            '高端制造': ['制造', '机器人', '航天', '航空', '设备', '工程'],
        }

        sector_performance = {}

        for news in self.news_data:
            title = news.get('title', '')
            snippet = news.get('snippet', '')
            text = title + ' ' + snippet

            # 提取该条新闻中涉及的板块
            news_sectors = set()
            for sector, keywords in sectors.items():
                if any(kw in text for kw in keywords):
                    news_sectors.add(sector)

            # 判断该条新闻中每个板块的情绪
            for sector in news_sectors:
                if sector not in sector_performance:
                    sector_performance[sector] = {"mentions": 0, "positive": 0, "negative": 0}

                sector_performance[sector]["mentions"] += 1

                # 使用上下文分析方法判断板块情绪
                sentiment = self._extract_sector_sentiment(text, sectors[sector])
                if sentiment == "positive":
                    sector_performance[sector]["positive"] += 1
                elif sentiment == "negative":
                    sector_performance[sector]["negative"] += 1

        # 计算每个板块的情绪
        for sector, data in sector_performance.items():
            if data["mentions"] > 0:
                if data["positive"] > data["negative"]:
                    data["sentiment"] = "偏多"
                elif data["negative"] > data["positive"]:
                    data["sentiment"] = "偏空"
                else:
                    data["sentiment"] = "震荡"
            else:
                data["sentiment"] = "未提及"

        return sector_performance

    def generate_analysis_report(self) -> str:
        """生成分析报告"""
        if not self.news_data:
            return "暂无资讯数据可供分析"

        sentiment = self.analyze_market_sentiment()
        events = self.extract_key_events()
        sectors = self.analyze_sector_performance()

        report = []
        report.append("=" * 60)
        report.append(f"📊 金融市场资讯分析报告")
        report.append(f"📅 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"📰 资讯来源: {len(self.news_data)} 条")
        report.append("=" * 60)

        # 市场情绪
        report.append("\n🌡️ 【市场情绪分析】")
        report.append(f"   整体情绪: {sentiment['sentiment']} (置信度: {sentiment['confidence']*100:.0f}%)")
        report.append(f"   利好消息: {sentiment['positive']} 条")
        report.append(f"   利空消息: {sentiment['negative']} 条")
        report.append(f"   中性消息: {sentiment['neutral']} 条")

        # 关键事件
        if events:
            report.append("\n📌 【关键事件摘要】")
            for i, event in enumerate(events[:5], 1):
                report.append(f"   {i}. [{event['type']}] {event['title']}")
                report.append(f"      时间: {event['date']}")

        # 板块表现
        if sectors:
            report.append("\n📈 【板块表现分析】")
            # 按提及次数排序
            sorted_sectors = sorted(
                [(k, v) for k, v in sectors.items() if v["mentions"] > 0],
                key=lambda x: x[1]["mentions"],
                reverse=True
            )
            for sector, data in sorted_sectors[:6]:
                emoji = "⬆️" if data["sentiment"] == "偏多" else "⬇️" if data["sentiment"] == "偏空" else "➡️"
                report.append(f"   {emoji} {sector}: {data['sentiment']} (提及{data['mentions']}次, 利好{data['positive']}次, 利空{data['negative']}次)")

        # 分析总结
        report.append("\n💡 【分析总结】")

        # 基于情绪和分析给出总结
        if sentiment['sentiment'] == "偏多":
            report.append("   市场情绪偏多，科技成长板块表现活跃，")
            if sectors.get('科技成长', {}).get('sentiment') == '偏多':
                report.append("建议关注科技成长板块的机会。")
        elif sentiment['sentiment'] == "偏空":
            report.append("   市场情绪偏空，周期股回调明显，")
            if sectors.get('周期股', {}).get('sentiment') == '偏空':
                report.append("注意风险回避。")
        else:
            report.append("   市场呈现震荡格局，板块分化明显，")
            report.append("建议关注业绩确定性和政策导向。")

        # 风险提示
        report.append("\n⚠️ 【风险提示】")
        report.append("   本分析基于公开资讯，仅供参考，不构成投资建议。")
        report.append("   投资有风险，入市需谨慎。")

        report.append("\n" + "=" * 60)

        return "\n".join(report)


def main():
    """主函数"""
    # 从命令行参数或stdin获取数据
    if len(sys.argv) > 1:
        # 从文件读取
        if sys.argv[1] == '--file':
            with open(sys.argv[2], 'r', encoding='utf-8') as f:
                news_json = f.read()
        else:
            news_json = sys.argv[1]
    else:
        # 从stdin读取
        news_json = sys.stdin.read()

    if not news_json.strip():
        print("Error: No news data provided", file=sys.stderr)
        sys.exit(1)

    analyzer = FinancialNewsAnalyzer()
    analyzer.load_news(news_json)
    report = analyzer.generate_analysis_report()
    print(report)


if __name__ == "__main__":
    main()
