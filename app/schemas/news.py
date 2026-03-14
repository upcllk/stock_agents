"""新闻相关 Pydantic 模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class NewsItemSchema(BaseModel):
    """单条新闻 schema，与 app.services.search.base.NewsItem 对齐。"""
    title: str = Field(description="新闻标题")
    source: str = Field(description="新闻来源")
    date: str = Field(description="发布日期")
    url: str = Field(description="链接地址")
    summary: str = Field(description="新闻摘要")


class NewsListSchema(BaseModel):
    """新闻列表响应 schema。"""
    items: list[NewsItemSchema] = Field(description="新闻列表")
