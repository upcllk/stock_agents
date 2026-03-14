"""搜索服务 Mock 实现：不请求外网。"""
from app.services.search.base import NewsItem, SearchService


class MockSearchService:
    """不请求外网，返回 0～2 条假数据，用于本地联调与测试。"""

    def search_news(self, company: str) -> list[NewsItem]:
        if not company or not company.strip():
            return []
        items = [
            NewsItem(
                title=f"{company.strip()} 近期业务动态",
                source="Mock Source",
                date="2025-03-14T10:00:00",
                url="https://example.com/mock-1",
                summary=f"关于 {company} 的模拟摘要，用于测试 search_service 与 news_agent 流程。",
            ),
            NewsItem(
                title=f"{company.strip()} 市场相关消息",
                source="Mock Finance",
                date="2025-03-14T08:00:00",
                url="https://example.com/mock-2",
                summary=f"模拟财经新闻摘要（{company}）。",
            ),
        ]
        return items[:2]
