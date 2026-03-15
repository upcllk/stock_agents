"""SimHash 近重复去重服务：与同 ticker 近期新闻比汉明距离，<= 阈值则剔除。"""
from __future__ import annotations

import logging
from typing import Any

from app.db.database import get_session
from app.db.repository import NewsEventRepository
from app.utils.simhash_util import clean_text_for_simhash, hamming_distance, simhash64, simhash64_to_db

# 汉明距离 <= 此阈值视为近重复（plans/3. news_hash_sql.md）
SIMHASH_NEAR_DUPLICATE_THRESHOLD = 3


def _as_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return str(v)


def _text_for_simhash(d: dict) -> str:
    """用于 SimHash 的文本：标题 + 摘要，与落库时一致。"""
    title = _as_str(d.get("title", ""))
    summary = _as_str(d.get("summary", ""))
    return clean_text_for_simhash(f"{title} {summary}".strip())


class SimHashDedupService:
    """
    近重复去重：与同 ticker 最近 30 天内的新闻 simhash 比较，
    汉明距离 <= SIMHASH_NEAR_DUPLICATE_THRESHOLD 则剔除。
    ticker 为空时不执行，原样返回。
    """

    def __init__(self, days: int = 30, threshold: int = SIMHASH_NEAR_DUPLICATE_THRESHOLD) -> None:
        self._days = days
        self._threshold = threshold

    def filter(self, items: list[dict], ticker: str | None = None) -> list[dict]:
        if not items or not (ticker or "").strip():
            return list(items)
        kept: list[dict] = []
        try:
            with get_session() as session:
                news_repo = NewsEventRepository(session)
                existing_simhashes = news_repo.list_simhashes_for_ticker(ticker.strip(), days=self._days)
            if not existing_simhashes:
                return list(items)
            for d in items:
                if not isinstance(d, dict):
                    kept.append(d)
                    continue
                text = _text_for_simhash(d)
                if not text:
                    kept.append(d)
                    continue
                sh = simhash64(text)
                if any(hamming_distance(sh, h) <= self._threshold for h in existing_simhashes):
                    continue
                kept.append(d)
        except Exception as e:
            logging.getLogger(__name__).warning("SimHashDedupService.filter 异常: %s", e)
            return list(items)
        return kept


if __name__ == "__main__":
    """测试 SimHash 近重复：插入带 simhash 的测试数据 → filter(ticker=TSLA) → 断言 → 删除测试数据，保证多次运行幂等。"""
    import os
    from pathlib import Path
    from dotenv import load_dotenv

    from app.db.repository import NewsEventRepository, NewsHashRepository
    from app.utils.hash_util import title_source_hash

    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
    if not os.getenv("DATABASE_URL"):
        print("请设置 DATABASE_URL，例如: postgresql://localhost:5432/stock_agents")
        exit(1)

    dup_url = "https://example.com/simhash-dedup-test"
    dup_title = "特斯拉 Q1 交付量公布"
    dup_summary = "摘要内容"
    dup_source = "Reuters"
    dup_simhash = simhash64_to_db(simhash64(f"{dup_title} {dup_summary}".strip()))
    dup_hash = title_source_hash(dup_title, dup_source)
    inserted_news_id: int | None = None

    try:
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
        print(f"已插入测试数据: news_id={inserted_news_id}, simhash={dup_simhash}")

        # 一条与库中同 title+summary（SimHash 近重复）、不同 source+url 避免被精确去重；一条全新
        items = [
            {"title": dup_title, "source": "OtherSource", "url": "https://other.com/near-dup", "date": "", "summary": dup_summary},
            {"title": "Apple 发布新机", "source": "Bloomberg", "url": "https://example.com/apple-1", "date": "", "summary": ""},
        ]
        print(f"输入 {len(items)} 条，期望 SimHash 去重后剩 1 条（仅 Apple）")

        kept = SimHashDedupService().filter(items, ticker="TSLA")
        print(f"去重后剩余 {len(kept)} 条:")
        for i, d in enumerate(kept, 1):
            print(f"  {i}. {d.get('title')!r} | {d.get('source')!r} | {d.get('url')!r}")

        if len(kept) != 1 or (kept and kept[0].get("title") != "Apple 发布新机"):
            print("预期: 仅保留 Apple 一条")
            exit(1)
        print("测试通过：SimHash 近重复去重正确。")
    finally:
        if inserted_news_id is not None:
            with get_session() as session:
                news_repo = NewsEventRepository(session)
                hash_repo = NewsHashRepository(session)
                news_repo.delete(inserted_news_id)
                hash_repo.delete(dup_hash)
            print("已清理测试数据。")
