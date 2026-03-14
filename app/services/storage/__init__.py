"""存储服务：新闻与事件分析入库、去重。"""
import os

from app.services.storage.base import StorageService
from app.services.storage.mock import MockStorageService
from app.services.storage.postgres import PostgresStorageService


def get_storage_service() -> StorageService:
    """根据 STORAGE_PROVIDER 返回实现（默认 postgres，测试可设为 mock）。"""
    provider = os.getenv("STORAGE_PROVIDER", "postgres")
    if provider == "mock":
        return MockStorageService()
    return PostgresStorageService()


__all__ = [
    "StorageService",
    "MockStorageService",
    "PostgresStorageService",
    "get_storage_service",
]
