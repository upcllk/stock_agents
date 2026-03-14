"""分析服务：新闻 → 事件结构化。"""
from app.services.analysis.base import (
    ANALYSIS_PROMPT_TEMPLATE,
    ANALYSIS_SYSTEM_PROMPT,
    EventAnalysis,
    AnalysisService,
)
from app.services.analysis.mock import MockAnalysisService


def get_analysis_service() -> AnalysisService:
    """返回当前分析服务实现（后续可按 ANALYSIS_PROVIDER 扩展 deepseek 等）。"""
    return MockAnalysisService()


__all__ = [
    "EventAnalysis",
    "AnalysisService",
    "ANALYSIS_PROMPT_TEMPLATE",
    "ANALYSIS_SYSTEM_PROMPT",
    "MockAnalysisService",
    "get_analysis_service",
]
