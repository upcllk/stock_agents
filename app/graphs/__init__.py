"""LangGraph 图：搜索→解析、新闻分析等。"""
from app.graphs.news_search_graph import invoke_news_search
from app.graphs.news_analysis_graph import invoke_news_analysis

__all__ = ["invoke_news_search", "invoke_news_analysis"]
