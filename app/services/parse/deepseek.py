"""解析服务 DeepSeek 实现：raw 文本 → JSON → list[NewsItem]。"""
from __future__ import annotations

import logging
from typing import Any

from app.services.search.base import NewsItem
from app.services.parse.base import ParseService, PARSE_NEWS_PROMPT_TEMPLATE
from app.utils.json_util import safe_json_loads


class DeepSeekParseService:
    """使用 DeepSeek Chat API，仅输出 JSON，抽取新闻列表。"""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key

    def parse_news_list(self, raw_text: str) -> list[NewsItem]:
        if not raw_text or not raw_text.strip():
            return []

        if not self._api_key:
            return []

        try:
            from openai import OpenAI
        except Exception as e:
            logging.getLogger(__name__).warning("openai SDK 未安装，无法使用 deepseek 解析：%s", e)
            return []

        prompt = PARSE_NEWS_PROMPT_TEMPLATE.format(raw_text=raw_text.strip())
        client = OpenAI(api_key=self._api_key, base_url="https://api.deepseek.com")
        logger = logging.getLogger(__name__)

        try:
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是信息抽取助手。只输出一个 JSON 对象，不要输出任何额外文本、markdown 或说明。"},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=4096,
                stream=False,
            )
        except Exception as e:
            logger.warning("DeepSeek 解析 API 调用失败：%s", e)
            return []

        content = getattr(resp.choices[0].message, "content", None) if getattr(resp, "choices", None) else None
        if not content or not str(content).strip():
            return []

        try:
            data = safe_json_loads(str(content))
        except Exception as e:
            logger.warning("DeepSeek 解析 JSON 解析异常: %s", e)
            return []

        if data is None:
            logger.warning("DeepSeek 解析返回内容无法解析为 JSON，content=%r", content)
            return []

        raw_items: Any
        if isinstance(data, list):
            raw_items = data
        elif isinstance(data, dict):
            # 兼容 items / news / data 等常见键名，避免 KeyError
            raw_items = data.get("items") or data.get("news") or data.get("data") or []
        else:
            raw_items = []

        if not isinstance(raw_items, list):
            return []

        items: list[NewsItem] = []
        for raw in raw_items[:10]:
            if not isinstance(raw, dict):
                continue
            try:
                items.append(
                    NewsItem(
                        title=self._as_str(raw.get("title", "")),
                        source=self._as_str(raw.get("source", "")),
                        date=self._as_str(raw.get("date", "")),
                        url=self._as_str(raw.get("url", "")),
                        summary=self._as_str(raw.get("summary", "")),
                    )
                )
            except Exception as e:
                logger.warning("NewsItem 构造失败，raw=%r err=%s", raw, e)
                continue
        return items

    @staticmethod
    def _as_str(v: Any) -> str:
        if v is None:
            return ""
        if isinstance(v, str):
            return v
        return str(v)
