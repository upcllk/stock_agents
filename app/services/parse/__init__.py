"""解析服务：raw 文本 → list[NewsItem]。"""
import os

from config.settings import SEARCH_PROVIDER

from app.services.parse.base import ParseService, PARSE_NEWS_PROMPT_TEMPLATE
from app.services.parse.deepseek import DeepSeekParseService
from app.services.parse.mock import MockParseService


def get_parse_service() -> ParseService:
    """根据 SEARCH_PROVIDER 返回对应实现（与搜索同源，暂不单独 PARSE_PROVIDER）。"""
    if SEARCH_PROVIDER == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        return DeepSeekParseService(api_key=api_key or None)
    return MockParseService()


__all__ = [
    "ParseService",
    "PARSE_NEWS_PROMPT_TEMPLATE",
    "MockParseService",
    "DeepSeekParseService",
    "get_parse_service",
]
