"""去重服务：协议与职责。精确去重 + 近重复去重在 service 内组合。"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class DedupService(Protocol):
    """去重服务协议：对新闻列表做精确/近重复去重，返回未重复项。"""

    def filter_duplicates(self, items: list[dict]) -> list[dict]:
        """
        按配置组合去重规则（先精确、后近重复），过滤掉重复项。
        items 每项为 dict，含 title / source / url / date / summary。
        返回通过去重的子列表。
        """
        ...
