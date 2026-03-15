"""新闻去重用 hash：与 news_hash 表、精确去重逻辑一致。"""
from __future__ import annotations

import hashlib
import re


def normalize_title(title: str) -> str:
    """标题标准化：去首尾空白、多空白合并、转小写，用于精确去重。"""
    if not title:
        return ""
    s = re.sub(r"\s+", " ", (title or "").strip())
    return s.lower()


def title_source_hash(title: str, source: str) -> str:
    """sha256(normalized_title + source)，与 news_hash 表一致。"""
    key = normalize_title(title) + (source or "")
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
