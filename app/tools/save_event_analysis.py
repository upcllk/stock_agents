"""
单条事件分析落库 tool：入参为 news_id + EventAnalysisSchema（Pydantic），
通过 EventAnalysisRepository 写入 event_analysis 表。news_id=-1 时也落库（暂未实现占位）。
"""
from __future__ import annotations

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.db.database import get_session
from app.db.repository import EventAnalysisRepository
from app.schemas.analysis import EventAnalysisSchema


def save_event_analysis(news_id: int, analysis: EventAnalysisSchema) -> None:
    """
    将单条事件分析写入 event_analysis 表。news_id=-1 时也落库（占位，后续接入真实 news_id）。
    """
    with get_session() as session:
        repo = EventAnalysisRepository(session)
        repo.create(
            news_id=news_id,
            event_type=analysis.event_type,
            impact_direction=analysis.impact_direction,
            impact_strength=analysis.impact_strength,
            impact_horizon=analysis.impact_horizon,
            confidence=analysis.confidence,
            reasoning=analysis.reasoning,
        )


class SaveEventAnalysisInput(BaseModel):
    """LLM tool 入参：单条事件分析落库。"""

    news_id: int = Field(description="关联的新闻 ID（news_event.id），暂未实现时可传 -1")
    analysis: EventAnalysisSchema = Field(description="事件分析结果")


@tool(args_schema=SaveEventAnalysisInput)
def save_event_analysis_tool(args: SaveEventAnalysisInput) -> dict:
    """
    将单条事件分析写入数据库。传入 news_id 和事件分析结果（event_type、impact_direction 等）。
    """
    save_event_analysis(args.news_id, args.analysis)
    return {"ok": True}
