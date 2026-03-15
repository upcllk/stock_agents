"""
数据库实体定义，与 scripts/init_db.sql 表结构一致。
使用 SQLAlchemy 2.x Declarative 映射：company_watchlist、news_event、event_analysis、news_hash。
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类。"""
    pass


class CompanyWatchlist(Base):
    """公司关注列表，用于定时抓取的公司/标的。表：company_watchlist。"""
    __tablename__ = "company_watchlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    market: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"CompanyWatchlist(id={self.id}, ticker={self.ticker}, company_name={self.company_name!r})"


class NewsEvent(Base):
    """新闻事件表，存储抓取到的公司相关新闻。表：news_event。"""
    __tablename__ = "news_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    publish_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    raw_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    simhash: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    analyses: Mapped[list["EventAnalysis"]] = relationship(
        "EventAnalysis", back_populates="news", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"NewsEvent(id={self.id}, ticker={self.ticker}, title={self.title[:30]!r}...)"


class EventAnalysis(Base):
    """事件分析表，LLM 对新闻的影响分析结果。表：event_analysis。"""
    __tablename__ = "event_analysis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    news_id: Mapped[int] = mapped_column(Integer, ForeignKey("news_event.id"), nullable=False)
    event_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    impact_direction: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    impact_strength: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    impact_horizon: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    news: Mapped["NewsEvent"] = relationship("NewsEvent", back_populates="analyses")

    def __repr__(self) -> str:
        return f"EventAnalysis(id={self.id}, news_id={self.news_id}, event_type={self.event_type!r})"


class NewsHash(Base):
    """新闻去重表，hash = sha256(title + source) 避免重复抓取。表：news_hash。"""
    __tablename__ = "news_hash"

    hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"NewsHash(hash={self.hash[:16]!r}...)"
