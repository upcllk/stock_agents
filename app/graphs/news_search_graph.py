"""LangGraph：搜索节点 → 解析节点，状态驱动。"""
from __future__ import annotations

import logging
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from config.settings import SEARCH_PROVIDER, QWEN_MODEL
from app.services.search.base import NewsItem, SEARCH_RAW_PROMPT_TEMPLATE
from app.services.parse.base import PARSE_NEWS_PROMPT_TEMPLATE
from app.schemas.news import NewsListSchema
from app.utils.json_util import safe_json_loads

# 一个 provider 对应一套 base_url + model
LLM_PROVIDER_CONFIG: dict[str, dict[str, str]] = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
    },
}


class NewsSearchState(TypedDict):
    """图状态：公司名、raw 搜索输出、解析后的新闻列表（dict 列表便于 state 传递）。"""
    company: str
    raw_search_output: str
    news_items: list[dict]


def _search_node(state: NewsSearchState, *, llm: ChatOpenAI) -> dict[str, Any]:
    """搜索节点：仅产出 raw 文本。"""
    company = (state.get("company") or "").strip()
    if not company:
        return {"raw_search_output": ""}
    prompt = SEARCH_RAW_PROMPT_TEMPLATE.format(company=company)
    try:
        resp = llm.invoke(
            [
                SystemMessage(content="你是金融研究助手。用清晰可读的文本列出新闻，每条包含标题、来源、日期、链接、摘要。"),
                HumanMessage(content=prompt),
            ]
        )
        content = getattr(resp, "content", None) or ""
        raw = (content if isinstance(content, str) else str(content)).strip()
        return {"raw_search_output": raw}
    except Exception as e:
        logging.getLogger(__name__).warning("搜索节点 LLM 调用失败: %s", e)
        return {"raw_search_output": ""}


def _parse_node(state: NewsSearchState, *, llm: ChatOpenAI) -> dict[str, Any]:
    """解析节点：raw 文本 → JSON → list[dict]。"""
    raw = (state.get("raw_search_output") or "").strip()
    if not raw:
        return {"news_items": []}
    prompt = PARSE_NEWS_PROMPT_TEMPLATE.format(raw_text=raw)
    try:
        resp = llm.invoke(
            [
                SystemMessage(content="你是信息抽取助手。只输出一个 JSON 对象，格式为 {\"items\": [{\"title\": \"新闻标题\", \"source\": \"新闻来源\", \"date\": \"发布日期\", \"url\": \"链接地址\", \"summary\": \"新闻摘要\"}]}，不要输出任何额外文本、markdown 或说明。"),
                HumanMessage(content=prompt),
            ]
        )
        content = getattr(resp, "content", None) or ""
        text = (content if isinstance(content, str) else str(content)).strip()
        data = safe_json_loads(text)
        if data is None:
            logging.getLogger(__name__).warning("解析节点 JSON 解析失败，content=%r", text[:200])
            return {"news_items": []}
        try:
            validated = NewsListSchema.model_validate(data)
            items: list[dict] = [
                {
                    "title": item.title,
                    "source": item.source,
                    "date": item.date,
                    "url": item.url,
                    "summary": item.summary,
                }
                for item in validated.items
            ]
        except Exception:
            raw_items: Any
            if isinstance(data, list):
                raw_items = data
            elif isinstance(data, dict):
                raw_items = data.get("items") or data.get("news") or data.get("data") or []
            else:
                raw_items = []
            if not isinstance(raw_items, list):
                raw_items = []
            items = []
            for raw in raw_items[:10]:
                if not isinstance(raw, dict):
                    continue
                items.append({
                    "title": _as_str(raw.get("title", "")),
                    "source": _as_str(raw.get("source", "")),
                    "date": _as_str(raw.get("date", "")),
                    "url": _as_str(raw.get("url", "")),
                    "summary": _as_str(raw.get("summary", "")),
                })
        return {"news_items": items}
    except Exception as e:
        logging.getLogger(__name__).warning("解析节点异常: %s", e)
        return {"news_items": []}


def _as_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return str(v)


def _build_graph(api_key: str) -> StateGraph:
    """构建图（供 invoke 使用）。base_url 与 model 由 SEARCH_PROVIDER + LLM_PROVIDER_CONFIG 解析。"""
    config = LLM_PROVIDER_CONFIG.get(SEARCH_PROVIDER) or LLM_PROVIDER_CONFIG["deepseek"]
    base_url = config["base_url"]
    model = config.get("model", "deepseek-chat")
    if SEARCH_PROVIDER == "qwen":
        model = QWEN_MODEL or config.get("model", "qwen-plus")
    llm = ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        max_tokens=4096,
    )
    builder = StateGraph(NewsSearchState)

    def search_node(state: NewsSearchState) -> dict[str, Any]:
        return _search_node(state, llm=llm)

    def parse_node(state: NewsSearchState) -> dict[str, Any]:
        return _parse_node(state, llm=llm)

    builder.add_node("search", search_node)
    builder.add_node("parse", parse_node)
    builder.add_edge(START, "search")
    builder.add_edge("search", "parse")
    builder.add_edge("parse", END)
    return builder


def invoke_news_search(company: str, api_key: str | None = None) -> list[NewsItem]:
    """
    执行搜索→解析图，返回 list[NewsItem]。
    api_key 为空时返回空列表（不建图、不调 API）。
    """
    if not (api_key or "").strip():
        return []
    company = (company or "").strip()
    if not company:
        return []
    try:
        graph = _build_graph(api_key=api_key).compile()
        result = graph.invoke({
            "company": company,
            "raw_search_output": "",
            "news_items": [],
        })
    except Exception as e:
        logging.getLogger(__name__).warning("invoke_news_search 图执行失败: %s", e)
        return []
    raw_list = result.get("news_items") or []
    return [
        NewsItem(
            title=_as_str(d.get("title", "")),
            source=_as_str(d.get("source", "")),
            date=_as_str(d.get("date", "")),
            url=_as_str(d.get("url", "")),
            summary=_as_str(d.get("summary", "")),
        )
        for d in raw_list
        if isinstance(d, dict)
    ]


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("请设置 DASHSCOPE_API_KEY 环境变量")
        exit(1)

    company = "Tesla"
    print(f"测试搜索公司: {company}")
    print("-" * 50)

    try:
        results = invoke_news_search(company, api_key)
        print(f"共获取 {len(results)} 条新闻:")
        print()
        for i, item in enumerate(results, 1):
            print(f"{i}. {item.title}")
            print(f"   来源: {item.source}")
            print(f"   日期: {item.date}")
            print(f"   链接: {item.url}")
            print(f"   摘要: {item.summary}")
            print()
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
