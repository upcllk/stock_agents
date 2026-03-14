"""搜索服务 DeepSeek 实现（占位：需配置 API 后接入联网搜索）。"""
from app.services.search.base import NewsItem, SearchService, SEARCH_PROMPT_TEMPLATE


class DeepSeekSearchService:
    """DeepSeek 联网搜索。需设置 DEEPSEEK_API_KEY 并安装对应 SDK 后实现具体请求。"""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key

    def search_news(self, company: str) -> list[NewsItem]:
        # 占位：未实现真实调用前返回空列表，避免阻塞 pipeline
        if not self._api_key:
            return []
        # TODO: 使用 SEARCH_PROMPT_TEMPLATE 调用 DeepSeek API，解析 JSON 为 NewsItem 列表
        return []
