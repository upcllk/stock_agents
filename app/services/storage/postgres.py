"""存储服务 PostgreSQL 实现。通过 app.db.repository 进行 CRUD，不直接写 SQL。"""
import hashlib

from app.db.database import get_session
from app.db.repository import EventAnalysisRepository, NewsEventRepository, NewsHashRepository
from app.services.analysis.base import EventAnalysis
from app.services.search.base import NewsItem


def _hash_news(title: str, source: str) -> str:
    return hashlib.sha256((title + source).encode()).hexdigest()


class PostgresStorageService:
    """使用 PostgreSQL 存储新闻与事件分析。"""

    def save_news(self, ticker: str, news: NewsItem) -> int:
        content_hash = _hash_news(news.title, news.source)
        with get_session() as session:
            news_repo = NewsEventRepository(session)
            hash_repo = NewsHashRepository(session)
            row = news_repo.create(
                ticker=ticker,
                title=news.title,
                source=news.source,
                url=news.url,
                publish_time=None,  # 可选：从 news.date 解析为 datetime
                raw_summary=news.summary,
            )
            news_id = row.id
            hash_repo.create_if_not_exists(content_hash)
        return news_id

    def save_analysis(self, news_id: int, analysis: EventAnalysis) -> None:
        with get_session() as session:
            analysis_repo = EventAnalysisRepository(session)
            analysis_repo.create(
                news_id=news_id,
                event_type=analysis.event_type,
                impact_direction=analysis.impact_direction,
                impact_strength=analysis.impact_strength,
                impact_horizon=analysis.impact_horizon,
                confidence=analysis.confidence,
                reasoning=analysis.reasoning,
            )

    def exists_by_hash(self, content_hash: str) -> bool:
        with get_session() as session:
            hash_repo = NewsHashRepository(session)
            return hash_repo.exists(content_hash)

