"""LangGraph：新闻文本 → 分析节点（Qwen）→ 解析节点，产出 EventAnalysis。仅 Qwen，不落库、无 tools。"""
from __future__ import annotations

import logging
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from config.settings import QWEN_MODEL
from app.services.analysis.base import EventAnalysis
from app.schemas.analysis import EventAnalysisSchema
from app.utils.json_util import safe_json_loads


QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class NewsAnalysisState(TypedDict):
    """图状态：新闻文本、LLM 原始输出、解析后的事件分析（dict）。"""
    news_text: str
    raw_analysis_output: str
    event_analysis: dict | None


def _analysis_node(state: NewsAnalysisState, *, llm: ChatOpenAI) -> dict[str, Any]:
    """分析节点：调用 Qwen 产出结构化 JSON 文本。"""
    news_text = (state.get("news_text") or "").strip()
    if not news_text:
        return {"raw_analysis_output": ""}
    try:
        resp = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "你是股票事件分析助手。任务：分析下面新闻对股价的影响。\n\n"
                        "只输出一个 JSON 对象，不要输出任何额外文本、markdown 或说明。格式：\n"
                        '{"event_type":"", "impact_direction":"", "impact_strength":1-5, "impact_horizon":"", "confidence":0-1, "reasoning":""}\n\n'
                        "约束：event_type 可选 earnings, product, order, policy, management, risk, other；"
                        "impact_direction 可选 bullish, bearish, neutral；"
                        "impact_horizon 可选 short_term, mid_term, long_term。"
                    )
                ),
                HumanMessage(content=news_text),
            ]
        )
        content = getattr(resp, "content", None) or ""
        raw = (content if isinstance(content, str) else str(content)).strip()
        return {"raw_analysis_output": raw}
    except Exception as e:
        logging.getLogger(__name__).warning("分析节点 LLM 调用失败: %s", e)
        return {"raw_analysis_output": ""}


def _as_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return str(v)


def _as_int(v: Any, default: int = 0) -> int:
    if v is None:
        return default
    if isinstance(v, int):
        return v
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _as_float(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _parse_node(state: NewsAnalysisState) -> dict[str, Any]:
    """解析节点：raw JSON 文本 → 校验/兜底 → event_analysis dict。"""
    raw = (state.get("raw_analysis_output") or "").strip()
    if not raw:
        return {"event_analysis": None}
    data = safe_json_loads(raw)
    if data is None:
        logging.getLogger(__name__).warning("解析节点 JSON 解析失败，content=%r", raw[:200])
        return {"event_analysis": None}
    try:
        validated = EventAnalysisSchema.model_validate(data)
        return {"event_analysis": validated.model_dump()}
    except Exception:
        pass
    if not isinstance(data, dict):
        return {"event_analysis": None}
    try:
        fallback = {
            "event_type": _as_str(data.get("event_type", "")),
            "impact_direction": _as_str(data.get("impact_direction", "")),
            "impact_strength": _as_int(data.get("impact_strength"), 0),
            "impact_horizon": _as_str(data.get("impact_horizon", "")),
            "confidence": _as_float(data.get("confidence"), 0.0),
            "reasoning": _as_str(data.get("reasoning", "")),
        }
        EventAnalysisSchema.model_validate(fallback)
        return {"event_analysis": fallback}
    except Exception as e:
        logging.getLogger(__name__).warning("解析节点兜底校验失败: %s", e)
        return {"event_analysis": None}


def _build_graph(api_key: str) -> StateGraph:
    """构建图。仅 Qwen：base_url、model 固定为 DashScope。"""
    llm = ChatOpenAI(
        model=QWEN_MODEL or "qwen-plus",
        api_key=api_key,
        base_url=QWEN_BASE_URL,
        max_tokens=2048,
    )
    builder = StateGraph(NewsAnalysisState)

    def analysis_node(state: NewsAnalysisState) -> dict[str, Any]:
        return _analysis_node(state, llm=llm)

    builder.add_node("analysis", analysis_node)
    builder.add_node("parse", _parse_node)
    builder.add_edge(START, "analysis")
    builder.add_edge("analysis", "parse")
    builder.add_edge("parse", END)
    return builder


def invoke_news_analysis(news_text: str, api_key: str | None = None) -> EventAnalysis | None:
    """
    执行新闻分析图，返回 EventAnalysis。
    api_key 为空或 news_text 为空时返回 None。
    """
    if not (api_key or "").strip():
        return None
    news_text = (news_text or "").strip()
    if not news_text:
        return None
    try:
        graph = _build_graph(api_key=api_key).compile()
        result = graph.invoke({
            "news_text": news_text,
            "raw_analysis_output": "",
            "event_analysis": None,
        })
    except Exception as e:
        logging.getLogger(__name__).warning("invoke_news_analysis 图执行失败: %s", e)
        return None
    ev = result.get("event_analysis")
    if not ev or not isinstance(ev, dict):
        return None
    try:
        return EventAnalysis(
            event_type=_as_str(ev.get("event_type", "")),
            impact_direction=_as_str(ev.get("impact_direction", "")),
            impact_strength=_as_int(ev.get("impact_strength"), 0),
            impact_horizon=_as_str(ev.get("impact_horizon", "")),
            confidence=_as_float(ev.get("confidence"), 0.0),
            reasoning=_as_str(ev.get("reasoning", "")),
        )
    except Exception as e:
        logging.getLogger(__name__).warning("EventAnalysis 构造失败: %s", e)
        return None


if __name__ == "__main__":
    import os
    from pathlib import Path
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("请设置 DASHSCOPE_API_KEY 环境变量")
        exit(1)

    news_text = (
        "特斯拉今日发布 2024 年第一季度交付数据，全球交付约 38.7 万辆，低于市场预期。"
        "公司称部分工厂停产升级影响产能，预计第二季度将恢复增长。"
    )
    print("测试分析新闻（写死输入）")
    print("-" * 50)
    print("新闻内容:", news_text[:80], "...")
    print("-" * 50)

    try:
        result = invoke_news_analysis(news_text, api_key)
        if result is None:
            print("分析结果: None（解析失败或未得到有效输出）")
        else:
            print("分析结果:")
            print("  event_type:", result.event_type)
            print("  impact_direction:", result.impact_direction)
            print("  impact_strength:", result.impact_strength)
            print("  impact_horizon:", result.impact_horizon)
            print("  confidence:", result.confidence)
            print("  reasoning:", result.reasoning)
    except Exception as e:
        print("测试失败:", e)
        import traceback
        traceback.print_exc()
