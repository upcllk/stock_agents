"""
批量保存新闻 tool：入参为 Pydantic（NewsListSchema + 可选 EventAnalysisSchema 列表），
将 date 解析为 publish_time，通过 Repository 写入 news_event 与 event_analysis。
本期不做去重（留作后续代办）。提供 @tool 装饰的 batch_save_news_tool 供 LLM 调用。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.db.database import get_session
from app.db.repository import EventAnalysisRepository, NewsEventRepository
from app.schemas.analysis import EventAnalysisSchema
from app.schemas.news import NewsListSchema


def _parse_publish_time(date_str: str) -> Optional[datetime]:
    """将日期字符串解析为 datetime，解析失败返回 None。支持 ISO 格式。"""
    if not (date_str or "").strip():
        return None
    s = date_str.strip()
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        pass
    # 尝试仅日期部分 YYYY-MM-DD
    if len(s) >= 10:
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d")
        except ValueError:
            pass
    return None


class BatchSaveNewsResult(BaseModel):
    """批量保存新闻的返回结果。"""
    saved_count: int = Field(description="本次插入的新闻条数")
    inserted_news_ids: list[int] = Field(description="本次插入的 news_event.id，与 items 顺序一致")


def batch_save_news(
    ticker: str,
    news_list: NewsListSchema,
    analyses: Optional[list[EventAnalysisSchema]] = None,
) -> BatchSaveNewsResult:
    """
    批量保存新闻及可选的事件分析。不做去重；date 解析为 publish_time 写入。

    入参：
        ticker: 股票代码
        news_list: 新闻列表（Pydantic）
        analyses: 可选，与 news_list.items 按下标对应，为每条新闻写入一条 event_analysis

    返回：
        BatchSaveNewsResult（saved_count, inserted_news_ids）
    """
    inserted_news_ids: list[int] = []
    items = news_list.items

    with get_session() as session:
        news_repo = NewsEventRepository(session)
        analysis_repo = EventAnalysisRepository(session)

        for i, item in enumerate(items):
            publish_time = _parse_publish_time(item.date)
            row = news_repo.create(
                ticker=ticker,
                title=item.title,
                source=item.source,
                url=item.url or None,
                publish_time=publish_time,
                raw_summary=item.summary or None,
            )
            inserted_news_ids.append(row.id)

            if analyses is not None and i < len(analyses):
                a = analyses[i]
                analysis_repo.create(
                    news_id=row.id,
                    event_type=a.event_type,
                    impact_direction=a.impact_direction,
                    impact_strength=a.impact_strength,
                    impact_horizon=a.impact_horizon,
                    confidence=a.confidence,
                    reasoning=a.reasoning,
                )

    return BatchSaveNewsResult(
        saved_count=len(inserted_news_ids),
        inserted_news_ids=inserted_news_ids,
    )


class BatchSaveNewsInput(BaseModel):
    """LLM tool 入参：批量保存新闻。"""

    ticker: str = Field(description="股票代码，如 AAPL、TSLA")
    news_list: NewsListSchema = Field(description="新闻列表，每条含 title、source、date、url、summary")
    analyses: Optional[list[EventAnalysisSchema]] = Field(
        default=None,
        description="可选，与 news_list.items 按下标一一对应的事件分析列表",
    )


@tool(args_schema=BatchSaveNewsInput)
def batch_save_news_tool(args: BatchSaveNewsInput) -> dict:
    """
    批量保存新闻到数据库。传入股票代码和新闻列表（及可选的事件分析），
    将每条新闻写入 news_event 表，若有 analyses 则按顺序写入 event_analysis 表。
    """
    result = batch_save_news(args.ticker, args.news_list, args.analyses)
    return result.model_dump()
