"""LangGraph：搜索节点 → 解析节点 → 去重节点 → 保存节点，状态驱动。"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from config.settings import NEWS_SEARCH_MAX_ITEMS, SEARCH_PROVIDER, QWEN_MODEL
from app.services.search.base import NewsItem, SEARCH_SYSTEM_PROMPT_TEMPLATE
from app.services.parse.base import PARSE_SYSTEM_PROMPT
from app.schemas.news import NewsItemSchema, NewsListSchema
from app.tools.batch_save_news import batch_save_news
from app.utils.json_util import safe_json_loads
from app.services.dedup import get_dedup_service

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
    """图状态：公司名、raw 搜索输出、解析后的新闻列表；可选 ticker 有则 parse 后保存到 DB。"""
    company: str
    raw_search_output: str
    news_items: list[dict]
    ticker: NotRequired[str]


def _search_node(state: NewsSearchState, *, llm: ChatOpenAI) -> dict[str, Any]:
    """搜索节点：仅产出 raw 文本。注入当前日期到 system prompt，避免模型返回往年旧闻。"""
    company = (state.get("company") or "").strip()
    if not company:
        return {"raw_search_output": ""}
    current_date = datetime.now().strftime("%Y年%m月%d日")
    system_prompt = SEARCH_SYSTEM_PROMPT_TEMPLATE.format(current_date=current_date)
    try:
        resp = llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=company),
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
    try:
        resp = llm.invoke(
            [
                SystemMessage(content=PARSE_SYSTEM_PROMPT),
                HumanMessage(content=raw),
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
                for item in validated.items[:NEWS_SEARCH_MAX_ITEMS]
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
            for raw in raw_items[:NEWS_SEARCH_MAX_ITEMS]:
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


def _dedup_node(state: NewsSearchState) -> dict[str, Any]:
    """去重节点：在 parse 之后、save 之前执行，委托 DedupService 做精确/近重复去重。"""
    items = state.get("news_items") or []
    if not items:
        return {}
    ticker = (state.get("ticker") or "").strip() or None
    kept = get_dedup_service().filter_duplicates(items, ticker=ticker)
    return {"news_items": kept}


def _save_node(state: NewsSearchState) -> dict[str, Any]:
    """保存节点：若有 ticker 且 news_items 非空，将 news_items 转成 NewsListSchema 后调用 batch_save_news 落库。"""
    ticker = (state.get("ticker") or "PLACEHOLDER").strip()
    items = state.get("news_items") or []
    if not ticker or not items:
        return {}
    try:
        news_list = NewsListSchema(
            items=[
                NewsItemSchema(
                    title=_as_str(d.get("title", "")),
                    source=_as_str(d.get("source", "")),
                    date=_as_str(d.get("date", "")),
                    url=_as_str(d.get("url", "")),
                    summary=_as_str(d.get("summary", "")),
                )
                for d in items
                if isinstance(d, dict)
            ]
        )
        batch_save_news(ticker, news_list, None)
    except Exception as e:
        logging.getLogger(__name__).warning("保存节点 batch_save_news 失败: %s", e)
    return {}


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
    builder.add_node("dedup", _dedup_node)
    builder.add_node("save", _save_node)
    builder.add_edge(START, "search")
    builder.add_edge("search", "parse")
    builder.add_edge("parse", "dedup")
    builder.add_edge("dedup", "save")
    builder.add_edge("save", END)
    return builder


def invoke_news_search(
    company: str,
    api_key: str | None = None,
    ticker: str | None = None,
) -> list[NewsItem]:
    """
    执行搜索→解析图，返回 list[NewsItem]。
    api_key 为空时返回空列表（不建图、不调 API）。
    ticker 不为空时，parse 后会调用 batch_save_news 将新闻写入数据库。
    """
    if not (api_key or "").strip():
        return []
    company = (company or "").strip()
    if not company:
        return []
    initial: dict[str, Any] = {
        "company": company,
        "raw_search_output": "",
        "news_items": [],
    }
    if (ticker or "").strip():
        initial["ticker"] = ticker.strip()
    try:
        graph = _build_graph(api_key=api_key).compile()
        # run_name/tags 供 LangSmith 区分 trace（需设置 LANGSMITH_TRACING=true 与 LANGSMITH_API_KEY）
        tags: list[str] = ["news_search", f"company:{company}"]
        if ticker:
            tags.append(f"ticker:{ticker}")
        config: dict[str, Any] = {"run_name": "News Search", "tags": tags}
        result = graph.invoke(initial, config=config)
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

    company = "蔚来汽车"
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
