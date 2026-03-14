"""Tools 包：供 graph 等调用的可复用工具（如批量保存新闻）。"""
from app.tools.batch_save_news import (
    BatchSaveNewsInput,
    BatchSaveNewsResult,
    batch_save_news,
    batch_save_news_tool,
)

__all__ = [
    "batch_save_news",
    "batch_save_news_tool",
    "BatchSaveNewsInput",
    "BatchSaveNewsResult",
]
