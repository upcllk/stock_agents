"""搜索服务通义千问实现：通过 LangGraph 搜索→解析图。"""

from __future__ import annotations

from app.services.search.base import NewsItem


class QwenSearchService:
    """通义千问搜索：委托给 LangGraph 搜索→解析图。base_url 与 model 由图内按 SEARCH_PROVIDER 解析。"""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key

    def search_news(self, company: str) -> list[NewsItem]:
        from app.graphs.news_search_graph import invoke_news_search
        return invoke_news_search(company, api_key=self._api_key)
