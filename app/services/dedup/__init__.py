"""去重服务：对外暴露组合去重类，内部由精确去重 + SimHash 近重复组合。"""
from app.services.dedup.base import DedupService
from app.services.dedup.exact import ExactDedupService
from app.services.dedup.postgres import PostgresDedupService
from app.services.dedup.simhash_dedup import SimHashDedupService


def get_dedup_service() -> DedupService:
    """返回当前使用的去重实现（精确 + SimHash 组合）。"""
    return PostgresDedupService()


__all__ = [
    "DedupService",
    "ExactDedupService",
    "SimHashDedupService",
    "PostgresDedupService",
    "get_dedup_service",
]
