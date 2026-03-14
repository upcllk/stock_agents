"""解析服务：协议与 prompt（从 raw 文本抽取新闻列表 JSON）。"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.services.search.base import NewsItem

# 解析节点 System 提示（HumanMessage 仅传待解析的 raw 文本，供 LangGraph 等使用）
PARSE_SYSTEM_PROMPT = """你是信息抽取助手。

任务：
从用户给出的文本中提取新闻条目，严格按 JSON 格式输出。

要求：
1 每条新闻包含 title（标题）、source（来源）、date（日期）、url（链接）、summary（摘要）
2 缺失字段用空字符串 ""
3 最多返回 10 条

输出格式（只输出一个 JSON 对象，不要任何额外文本、markdown 或说明）：
{"items": [{"title": "", "source": "", "date": "", "url": "", "summary": ""}]}
"""

# 解析用 prompt：明确 schema（旧版整段模板，含占位 {raw_text}）
PARSE_NEWS_PROMPT_TEMPLATE = """你是信息抽取助手。从下面文本中提取新闻条目，严格按 JSON 格式输出，不要输出任何额外文字。

要求：
- 每条新闻包含：title（标题）、source（来源）、date（日期）、url（链接）、summary（摘要）。
- 缺失的字段用空字符串 ""。
- 最多返回 10 条。

输出格式（仅输出一个 JSON 对象）：
{{"items": [{{"title": "", "source": "", "date": "", "url": "", "summary": ""}}]}}

待抽取文本：
---
{raw_text}
---
"""


@runtime_checkable
class ParseService(Protocol):
    """解析服务协议：从 raw 文本抽取新闻列表。"""

    def parse_news_list(self, raw_text: str) -> list[NewsItem]:
        ...
