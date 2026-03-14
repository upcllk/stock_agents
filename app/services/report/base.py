"""报告服务：协议与职责（每日公司动态报告）。"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class ReportService(Protocol):
    """报告服务协议：按日/按公司生成动态报告。"""

    def generate_daily_report(self, report_date: str | None = None) -> str:
        """生成每日公司动态报告，返回报告文本。report_date 为 YYYY-MM-DD，默认今天。"""
        ...
