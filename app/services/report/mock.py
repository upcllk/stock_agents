"""报告服务 Mock 实现。"""
from datetime import date

from app.services.report.base import ReportService


class MockReportService:
    """返回固定报告内容，用于联调与测试。"""

    def generate_daily_report(self, report_date: str | None = None) -> str:
        d = report_date or date.today().isoformat()
        return f"# 每日公司动态报告（Mock）\n\n日期：{d}\n\n（暂无数据，请先运行 news_agent 抓取新闻。）\n"
