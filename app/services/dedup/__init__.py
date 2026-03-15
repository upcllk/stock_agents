"""去重服务：精确去重 + 近重复去重（在 service 内组合）。"""
from app.services.dedup.base import DedupService
from app.services.dedup.postgres import PostgresDedupService


def get_dedup_service() -> DedupService:
    """返回当前使用的去重实现（目前为 PostgreSQL 精确去重）。"""
    return PostgresDedupService()


__all__ = [
    "DedupService",
    "PostgresDedupService",
    "get_dedup_service",
]
