"""去重服务 PostgreSQL 实现：精确去重（url + title+source hash），后续可在此组合近重复（SimHash）。"""
from __future__ import annotations

import logging
from typing import Any

from app.db.database import get_session
from app.db.repository import NewsEventRepository, NewsHashRepository
from app.utils.hash_util import title_source_hash


def _as_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return str(v)


class PostgresDedupService:
    """
    使用 news_event、news_hash 做精确去重。
    规则：1) url 已存在则剔除；2) sha256(normalized_title+source) 已存在则剔除。
    后续可在此类内增加近重复（SimHash）逻辑，与精确去重组合。
    """

    def filter_duplicates(self, items: list[dict]) -> list[dict]:
        if not items:
            return []
        kept: list[dict] = []
        try:
            with get_session() as session:
                news_repo = NewsEventRepository(session)
                hash_repo = NewsHashRepository(session)
                for d in items:
                    if not isinstance(d, dict):
                        continue
                    title = _as_str(d.get("title", ""))
                    source = _as_str(d.get("source", ""))
                    url = _as_str(d.get("url", ""))
                    if url and news_repo.exists_by_url(url):
                        continue
                    content_hash = title_source_hash(title, source)
                    if hash_repo.exists(content_hash):
                        continue
                    kept.append(d)
        except Exception as e:
            logging.getLogger(__name__).warning("PostgresDedupService.filter_duplicates 异常: %s", e)
            return list(items)
        return kept


if __name__ == "__main__":
    """测试重复：插入测试数据 → 跑去重 → 断言 → 删除测试数据，保证每次运行结果一致。"""
    import os
    from pathlib import Path
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
    if not os.getenv("DATABASE_URL"):
        print("请设置 DATABASE_URL，例如: postgresql://localhost:5432/stock_agents")
        exit(1)

    dup_url = "https://example.com/dedup-test-dup"
    dup_title = "Tesla Q1 交付量公布"
    dup_source = "Reuters"
    dup_hash = title_source_hash(dup_title, dup_source)
    inserted_news_id: int | None = None

    try:
        # 1) 插入本次测试用的“已存在”新闻与 hash
        with get_session() as session:
            news_repo = NewsEventRepository(session)
            hash_repo = NewsHashRepository(session)
            row = news_repo.create(
                ticker="TSLA",
                title=dup_title,
                source=dup_source,
                url=dup_url,
                publish_time=None,
                raw_summary="摘要",
            )
            inserted_news_id = row.id
            hash_repo.create_if_not_exists(dup_hash)
        print(f"已插入测试数据: news_id={inserted_news_id}, url={dup_url!r}")

        # 2) 构造输入：两条与库中重复（同 url / 同 title+source），一条全新
        items = [
            {"title": dup_title, "source": dup_source, "url": dup_url, "date": "", "summary": ""},
            {"title": dup_title, "source": dup_source, "url": "https://other.com/same-title-source", "date": "", "summary": ""},
            {"title": "Apple 发布新机", "source": "Bloomberg", "url": "https://example.com/apple-1", "date": "", "summary": ""},
        ]
        print(f"输入 {len(items)} 条，期望去重后剩 1 条（仅 Apple）")

        # 3) 去重
        service = PostgresDedupService()
        kept = service.filter_duplicates(items)
        print(f"去重后剩余 {len(kept)} 条:")
        for i, d in enumerate(kept, 1):
            print(f"  {i}. {d.get('title')!r} | {d.get('source')!r} | {d.get('url')!r}")

        if len(kept) != 1 or (kept and kept[0].get("title") != "Apple 发布新机"):
            print("预期: 仅保留 Apple 一条，请检查去重逻辑或 DB 状态")
            exit(1)
        print("测试通过：重复项已正确剔除。")
    finally:
        # 4) 删除本次插入的测试数据，保证下次运行结果一致
        if inserted_news_id is not None:
            with get_session() as session:
                news_repo = NewsEventRepository(session)
                hash_repo = NewsHashRepository(session)
                news_repo.delete(inserted_news_id)
                hash_repo.delete(dup_hash)
            print("已清理测试数据。")
