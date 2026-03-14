"""事件分析 Pydantic 模型，与 event_analysis 表及 EventAnalysis 对齐。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class EventAnalysisSchema(BaseModel):
    """单条事件分析 schema，与 app.services.analysis.base.EventAnalysis 对齐。"""
    event_type: str = Field(description="事件类型")
    impact_direction: str = Field(description="影响方向")
    impact_strength: int = Field(description="影响强度 1-5")
    impact_horizon: str = Field(description="影响周期")
    confidence: float = Field(description="置信度 0-1")
    reasoning: str = Field(description="分析理由")
