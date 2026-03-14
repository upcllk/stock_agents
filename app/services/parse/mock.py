"""解析服务 Mock 实现：不请求外网。"""
from app.services.search.base import NewsItem
from app.services.parse.base import ParseService


class MockParseService:
    """不请求外网：raw 为空返回 []，否则返回 1～2 条固定 NewsItem。"""

    def parse_news_list(self, raw_text: str) -> list[NewsItem]:
        if not raw_text or not raw_text.strip():
            return []
        return [
            NewsItem(
                title="Mock 解析标题",
                source="Mock Parse Source",
                date="2025-03-14T10:00:00",
                url="https://example.com/parsed-1",
                summary="从 raw 文本解析出的模拟摘要。",
            ),
            NewsItem(
                title="Mock 解析标题 2",
                source="Mock Parse Source 2",
                date="2025-03-14T09:00:00",
                url="https://example.com/parsed-2",
                summary="第二条模拟摘要。",
            ),
        ][:2]
