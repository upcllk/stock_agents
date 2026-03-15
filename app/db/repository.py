"""
数据访问层：对表进行 CRUD，直接使用 SQLAlchemy Session 与 app.db.models 实体。
业务层（如 StorageService）应通过本层访问数据库，避免手写 SQL。
"""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CompanyWatchlist, EventAnalysis, NewsEvent, NewsHash


class CompanyWatchlistRepository:
    """company_watchlist 表 CRUD。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_enabled(self) -> list[CompanyWatchlist]:
        """返回所有 enabled=True 的公司。"""
        stmt = select(CompanyWatchlist).where(CompanyWatchlist.enabled == True)
        return list(self._session.scalars(stmt).all())

    def get_by_id(self, id: int) -> Optional[CompanyWatchlist]:
        """按主键查询。"""
        return self._session.get(CompanyWatchlist, id)

    def create(
        self,
        *,
        ticker: Optional[str] = None,
        company_name: Optional[str] = None,
        market: Optional[str] = None,
        enabled: bool = True,
    ) -> CompanyWatchlist:
        """插入一条记录，返回实体。"""
        row = CompanyWatchlist(
            ticker=ticker,
            company_name=company_name,
            market=market,
            enabled=enabled,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def update(
        self,
        id: int,
        *,
        ticker: Optional[str] = None,
        company_name: Optional[str] = None,
        market: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> Optional[CompanyWatchlist]:
        """按主键更新，返回更新后的实体。"""
        row = self._session.get(CompanyWatchlist, id)
        if row is None:
            return None
        if ticker is not None:
            row.ticker = ticker
        if company_name is not None:
            row.company_name = company_name
        if market is not None:
            row.market = market
        if enabled is not None:
            row.enabled = enabled
        self._session.flush()
        return row

    def delete(self, id: int) -> bool:
        """按主键删除，返回是否删除了记录。"""
        row = self._session.get(CompanyWatchlist, id)
        if row is None:
            return False
        self._session.delete(row)
        return True


class NewsEventRepository:
    """news_event 表 CRUD。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, id: int) -> Optional[NewsEvent]:
        """按主键查询。"""
        return self._session.get(NewsEvent, id)

    def exists_by_url(self, url: str) -> bool:
        """精确去重用：判断该 url 是否已在 news_event 中存在。url 为空则返回 False。"""
        if not (url or "").strip():
            return False
        stmt = select(NewsEvent.id).where(NewsEvent.url == url.strip()).limit(1)
        return self._session.scalar(stmt) is not None

    def list_simhashes_for_ticker(self, ticker: str, days: int = 30) -> list[int]:
        """近重复去重用：返回该 ticker 最近 days 天内已落库新闻的 simhash 列表（仅非空）。"""
        if not (ticker or "").strip():
            return []
        since = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(NewsEvent.simhash)
            .where(NewsEvent.ticker == ticker.strip(), NewsEvent.created_at >= since, NewsEvent.simhash.isnot(None))
        )
        return [r for r in self._session.scalars(stmt).all() if r is not None]

    def create(
        self,
        *,
        ticker: str,
        title: str,
        source: str,
        url: Optional[str] = None,
        publish_time: Optional[datetime] = None,
        raw_summary: Optional[str] = None,
        simhash: Optional[int] = None,
    ) -> NewsEvent:
        """插入一条新闻，返回实体（含 id）。"""
        row = NewsEvent(
            ticker=ticker,
            title=title,
            source=source,
            url=url,
            publish_time=publish_time,
            raw_summary=raw_summary,
            simhash=simhash,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def update(
        self,
        id: int,
        *,
        ticker: Optional[str] = None,
        title: Optional[str] = None,
        source: Optional[str] = None,
        url: Optional[str] = None,
        publish_time: Optional[datetime] = None,
        raw_summary: Optional[str] = None,
        simhash: Optional[int] = None,
    ) -> Optional[NewsEvent]:
        """按主键更新。"""
        row = self._session.get(NewsEvent, id)
        if row is None:
            return None
        if ticker is not None:
            row.ticker = ticker
        if title is not None:
            row.title = title
        if source is not None:
            row.source = source
        if url is not None:
            row.url = url
        if publish_time is not None:
            row.publish_time = publish_time
        if raw_summary is not None:
            row.raw_summary = raw_summary
        if simhash is not None:
            row.simhash = simhash
        self._session.flush()
        return row

    def delete(self, id: int) -> bool:
        """按主键删除。"""
        row = self._session.get(NewsEvent, id)
        if row is None:
            return False
        self._session.delete(row)
        return True


class EventAnalysisRepository:
    """event_analysis 表 CRUD。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, id: int) -> Optional[EventAnalysis]:
        """按主键查询。"""
        return self._session.get(EventAnalysis, id)

    def create(
        self,
        *,
        news_id: int,
        event_type: str,
        impact_direction: str,
        impact_strength: int,
        impact_horizon: str,
        confidence: float,
        reasoning: str,
    ) -> EventAnalysis:
        """插入一条分析，返回实体。"""
        row = EventAnalysis(
            news_id=news_id,
            event_type=event_type,
            impact_direction=impact_direction,
            impact_strength=impact_strength,
            impact_horizon=impact_horizon,
            confidence=confidence,
            reasoning=reasoning,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def delete(self, id: int) -> bool:
        """按主键删除。"""
        row = self._session.get(EventAnalysis, id)
        if row is None:
            return False
        self._session.delete(row)
        return True


class NewsHashRepository:
    """news_hash 表 CRUD（去重用）。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def exists(self, content_hash: str) -> bool:
        """判断 hash 是否已存在。"""
        row = self._session.get(NewsHash, content_hash)
        return row is not None

    def create(self, content_hash: str) -> NewsHash:
        """插入一条 hash；若已存在会冲突，调用方可用 exists 先判重或捕获唯一约束。"""
        row = NewsHash(hash=content_hash)
        self._session.add(row)
        self._session.flush()
        return row

    def create_if_not_exists(self, content_hash: str) -> bool:
        """若不存在则插入，返回是否执行了插入。"""
        if self.exists(content_hash):
            return False
        self.create(content_hash)
        return True

    def delete(self, content_hash: str) -> bool:
        """按 hash 主键删除，返回是否删除了记录。"""
        row = self._session.get(NewsHash, content_hash)
        if row is None:
            return False
        self._session.delete(row)
        return True
