"""JSON 解析工具：兼容 markdown 包裹与容错截取。"""
from __future__ import annotations

import json
from typing import Any


def safe_json_loads(text: str) -> Any | None:
    """解析 JSON，兼容 ```json ... ``` 包裹及首段 {}/[] 截取。"""
    s = text.strip()
    if not s:
        return None

    # 兼容 ```json ... ``` 包裹
    if s.startswith("```"):
        lines = s.splitlines()
        if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].strip() == "```":
            s = "\n".join(lines[1:-1]).strip()
        if s.lower().startswith("json"):
            s = s[4:].strip()

    try:
        return json.loads(s)
    except Exception:
        pass

    # 容错：截取首个 JSON 对象/数组
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = s.find(open_ch)
        end = s.rfind(close_ch)
        if start != -1 and end != -1 and end > start:
            candidate = s[start : end + 1]
            try:
                return json.loads(candidate)
            except Exception:
                continue
    return None
