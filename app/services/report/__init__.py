"""报告服务：每日公司动态报告。"""
import os

from app.services.report.base import ReportService
from app.services.report.mock import MockReportService


def get_report_service() -> ReportService:
    """根据 REPORT_PROVIDER 返回实现（默认 mock）。"""
    if os.getenv("REPORT_PROVIDER", "mock") == "mock":
        return MockReportService()
    return MockReportService()


__all__ = [
    "ReportService",
    "MockReportService",
    "get_report_service",
]
