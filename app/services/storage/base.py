"""存储服务：协议与职责（新闻与事件分析入库、去重）。"""
from typing import Protocol, runtime_checkable

# 使用 search.NewsItem 与 analysis.EventAnalysis 作为入参类型，避免循环依赖时可使用 str 注解
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.search.base import NewsItem
    from app.services.analysis.base import EventAnalysis


@runtime_checkable
class StorageService(Protocol):
    """存储服务协议：保存新闻、保存分析、按 hash 判重。"""

    def save_news(self, ticker: str, news: "NewsItem") -> int:
        """写入新闻表，返回 news_event.id。"""
        ...

    def save_analysis(self, news_id: int, analysis: "EventAnalysis") -> None:
        """写入 event_analysis 表。"""
        ...

    def exists_by_hash(self, content_hash: str) -> bool:
        """根据 sha256(title+source) 判断是否已存在，避免重复抓取。"""
        ...
