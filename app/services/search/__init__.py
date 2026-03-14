"""搜索服务：输入公司名，输出新闻列表。"""
import os

from config.settings import SEARCH_PROVIDER

from app.services.search.base import NewsItem, SearchService, SEARCH_PROMPT_TEMPLATE
from app.services.search.deepseek import DeepSeekSearchService
from app.services.search.mock import MockSearchService
from app.services.search.qwen import QwenSearchService


def get_search_service() -> SearchService:
    """根据 SEARCH_PROVIDER 返回对应实现。"""
    if SEARCH_PROVIDER == "mock":
        return MockSearchService()
    if SEARCH_PROVIDER == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        return DeepSeekSearchService(api_key=api_key or None)
    if SEARCH_PROVIDER == "qwen":
        api_key = os.getenv("DASHSCOPE_API_KEY", "")
        return QwenSearchService(api_key=api_key or None)
    return MockSearchService()


__all__ = [
    "NewsItem",
    "SearchService",
    "SEARCH_PROMPT_TEMPLATE",
    "MockSearchService",
    "DeepSeekSearchService",
    "QwenSearchService",
    "get_search_service",
]
