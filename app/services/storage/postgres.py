"""存储服务 PostgreSQL 实现。"""
import hashlib

from app.db.database import get_connection
from app.services.analysis.base import EventAnalysis
from app.services.search.base import NewsItem


def _hash_news(title: str, source: str) -> str:
    return hashlib.sha256((title + source).encode()).hexdigest()


class PostgresStorageService:
    """使用 PostgreSQL 存储新闻与事件分析。"""

    def save_news(self, ticker: str, news: NewsItem) -> int:
        content_hash = _hash_news(news.title, news.source)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO news_event (ticker, title, source, url, publish_time, raw_summary)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        ticker,
                        news.title,
                        news.source,
                        news.url,
                        news.date if news.date else None,
                        news.summary,
                    ),
                )
                row = cur.fetchone()
                news_id = row[0]
                cur.execute(
                    "INSERT INTO news_hash (hash) VALUES (%s) ON CONFLICT (hash) DO NOTHING",
                    (content_hash,),
                )
                return news_id

    def save_analysis(self, news_id: int, analysis: EventAnalysis) -> None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO event_analysis (news_id, event_type, impact_direction, impact_strength, impact_horizon, confidence, reasoning)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        news_id,
                        analysis.event_type,
                        analysis.impact_direction,
                        analysis.impact_strength,
                        analysis.impact_horizon,
                        analysis.confidence,
                        analysis.reasoning,
                    ),
                )

    def exists_by_hash(self, content_hash: str) -> bool:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM news_hash WHERE hash = %s", (content_hash,))
                return cur.fetchone() is not None

