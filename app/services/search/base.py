"""搜索服务：协议与公共类型。"""
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


# 真实实现时用此 prompt 调用 LLM 联网搜索并解析返回的 JSON（plans/agent1.md Step1）
SEARCH_PROMPT_TEMPLATE = """你是金融研究助手。

任务：
搜索最近24小时关于公司 "{company}" 的重要新闻。

要求：
1 只关注对股价可能有影响的信息
2 忽略无关媒体报道
3 返回最多10条

返回JSON：

[
{
"title": "",
"source": "",
"date": "",
"url": "",
"summary": ""
}
]
"""


@dataclass(frozen=True)
class NewsItem:
    """单条新闻，与文档及 news_event 表字段对齐。"""
    title: str
    source: str
    date: str
    url: str
    summary: str


@runtime_checkable
class SearchService(Protocol):
    """搜索服务协议：根据公司名返回新闻列表。无结果返回空列表；异常由实现方记录并可返回空列表。"""

    def search_news(self, company: str) -> list[NewsItem]:
        ...
