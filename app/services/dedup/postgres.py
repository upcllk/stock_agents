"""对外暴露的去重服务：组合精确去重 + SimHash 近重复。"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from app.db.database import get_session
from app.db.repository import NewsEventRepository, NewsHashRepository
from app.services.dedup.exact import ExactDedupService
from app.services.dedup.simhash_dedup import SimHashDedupService
from app.utils.hash_util import title_source_hash
from app.utils.simhash_util import simhash64, simhash64_to_db


class PostgresDedupService:
    """
    对外去重类：先精确去重，再 SimHash 近重复。
    组合 ExactDedupService 与 SimHashDedupService。
    """

    def __init__(
        self,
        exact_dedup: ExactDedupService | None = None,
        simhash_dedup: SimHashDedupService | None = None,
    ) -> None:
        self._exact = exact_dedup or ExactDedupService()
        self._simhash = simhash_dedup or SimHashDedupService()

    def filter_duplicates(self, items: list[dict], ticker: str | None = None) -> list[dict]:
        if not items:
            return []
        try:
            after_exact = self._exact.filter(items)
            return self._simhash.filter(after_exact, ticker=ticker)
        except Exception as e:
            logging.getLogger(__name__).warning("PostgresDedupService.filter_duplicates 异常: %s", e)
            return list(items)


if __name__ == "__main__":
    """测试重复：插入测试数据 → 跑去重 → 断言 → 删除测试数据，保证每次运行结果一致。"""
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

    dup_summary = "摘要"
    dup_simhash = simhash64_to_db(simhash64(f"{dup_title} {dup_summary}".strip()))

    try:
        # 1) 插入本次测试用的“已存在”新闻与 hash（含 simhash 供近重复测试）
        with get_session() as session:
            news_repo = NewsEventRepository(session)
            hash_repo = NewsHashRepository(session)
            row = news_repo.create(
                ticker="TSLA",
                title=dup_title,
                source=dup_source,
                url=dup_url,
                publish_time=None,
                raw_summary=dup_summary,
                simhash=dup_simhash,
            )
            inserted_news_id = row.id
            hash_repo.create_if_not_exists(dup_hash)
        print(f"已插入测试数据: news_id={inserted_news_id}, url={dup_url!r}, simhash={dup_simhash}")

        # 2) 构造输入：两条精确重复（同 url / 同 title+source）、一条仅 SimHash 近重复（同 title+summary 不同 source+url）、一条全新
        items = [
            {"title": dup_title, "source": dup_source, "url": dup_url, "date": "", "summary": dup_summary},
            {"title": dup_title, "source": dup_source, "url": "https://other.com/same-title-source", "date": "", "summary": dup_summary},
            {"title": dup_title, "source": "OtherSource", "url": "https://other.com/near-dup", "date": "", "summary": dup_summary},
            {"title": "Apple 发布新机", "source": "Bloomberg", "url": "https://example.com/apple-1", "date": "", "summary": ""},
        ]
        print(f"输入 {len(items)} 条，期望去重后剩 1 条（仅 Apple）")

        # 3) 去重（传 ticker 以启用 SimHash 近重复）
        service = PostgresDedupService()
        kept = service.filter_duplicates(items, ticker="TSLA")
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
