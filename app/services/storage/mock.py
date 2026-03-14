"""存储服务 Mock：内存存储，用于联调与测试。"""
import hashlib

from app.services.search.base import NewsItem
from app.services.analysis.base import EventAnalysis


def _hash_news(title: str, source: str) -> str:
    return hashlib.sha256((title + source).encode()).hexdigest()


class MockStorageService:
    """内存保存，返回自增 id；不落库。"""

    def __init__(self) -> None:
        self._news_id = 0
        self._hashes: set[str] = set()

    def save_news(self, ticker: str, news: NewsItem) -> int:
        self._news_id += 1
        self._hashes.add(_hash_news(news.title, news.source))
        return self._news_id

    def save_analysis(self, news_id: int, analysis: EventAnalysis) -> None:
        pass

    def exists_by_hash(self, content_hash: str) -> bool:
        return content_hash in self._hashes
