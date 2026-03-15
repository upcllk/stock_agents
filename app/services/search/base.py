"""搜索服务：协议与公共类型。"""
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from config.settings import NEWS_SEARCH_MAX_ITEMS


# 搜索节点 System 提示模板，调用时传入 current_date 以便模型只搜近期新闻（HumanMessage 仅传公司名）
SEARCH_SYSTEM_PROMPT_TEMPLATE = f"""你是金融研究助手。

当前日期：{{current_date}}

任务：
根据用户给出的公司名，搜索**当前日期或最近 24 小时内**关于该公司的重要新闻。不要返回过时的旧闻（例如当前已是 {{current_date}} 时，不要返回 2024 年等往年新闻）。

要求：
1 只关注对股价可能有影响的信息
2 忽略无关媒体报道
3 最多{NEWS_SEARCH_MAX_ITEMS}条
4 用清晰可读的文本列出，每条包含：标题、来源、日期、链接、摘要。不必输出 JSON，自然段或列表即可。
"""

# 仅出 raw 文本的搜索 prompt（不要求 JSON，供两段式 搜索→解析 使用）
SEARCH_RAW_PROMPT_TEMPLATE = f"""你是金融研究助手。

任务：
搜索最近24小时关于公司 "{{company}}" 的重要新闻。

要求：
1 只关注对股价可能有影响的信息
2 忽略无关媒体报道
3 最多{NEWS_SEARCH_MAX_ITEMS}条
4 用清晰可读的文本列出，每条包含：标题、来源、日期、链接、摘要。不必输出 JSON，自然段或列表即可。
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
