"""分析服务 Mock 实现。"""
from app.services.analysis.base import AnalysisService, EventAnalysis


class MockAnalysisService:
    """返回固定中性分析，用于联调与测试。"""

    def analyze(self, news_text: str) -> EventAnalysis | None:
        if not news_text or not news_text.strip():
            return None
        return EventAnalysis(
            event_type="other",
            impact_direction="neutral",
            impact_strength=2,
            impact_horizon="short_term",
            confidence=0.5,
            reasoning="Mock 分析结果，用于测试 pipeline。",
        )
