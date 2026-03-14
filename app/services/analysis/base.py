"""分析服务：协议与公共类型（新闻 → 事件结构化）。"""
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


# 真实实现时用此 prompt 调用 LLM（plans/agent1.md Step2）
ANALYSIS_PROMPT_TEMPLATE = """你是股票事件分析助手。

任务：
分析下面新闻对股价的影响。

新闻：
{news_text}

返回JSON：

{
"event_type":"",
"impact_direction":"",
"impact_strength":1-5,
"impact_horizon":"",
"confidence":0-1,
"reasoning":""
}

event_type可选：
earnings product order policy management risk other

impact_direction：bullish bearish neutral

impact_horizon：short_term mid_term long_term
"""


@dataclass(frozen=True)
class EventAnalysis:
    """单条新闻的事件分析结果，与 event_analysis 表对齐。"""
    event_type: str
    impact_direction: str
    impact_strength: int
    impact_horizon: str
    confidence: float
    reasoning: str


@runtime_checkable
class AnalysisService(Protocol):
    """分析服务协议：对单条新闻做事件分析。"""

    def analyze(self, news_text: str) -> EventAnalysis | None:
        ...


# 供 storage 等使用的新闻类型（与 search.NewsItem 一致，此处仅类型引用说明）
# 调用方传入 title + source + url + summary 等拼接的 news_text 即可
