"""Tools 包：供 graph 等调用的可复用工具（如批量保存新闻、单条分析落库）。"""
from app.tools.batch_save_news import (
    BatchSaveNewsInput,
    BatchSaveNewsResult,
    batch_save_news,
    batch_save_news_tool,
)
from app.tools.save_event_analysis import (
    SaveEventAnalysisInput,
    save_event_analysis,
    save_event_analysis_tool,
)

__all__ = [
    "batch_save_news",
    "batch_save_news_tool",
    "BatchSaveNewsInput",
    "BatchSaveNewsResult",
    "save_event_analysis",
    "save_event_analysis_tool",
    "SaveEventAnalysisInput",
]
