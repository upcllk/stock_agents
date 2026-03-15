"""64 位 SimHash 与汉明距离，用于近重复去重。与 plans/3. news_hash_sql.md 一致。"""
from __future__ import annotations

import hashlib
import re


def clean_text_for_simhash(text: str) -> str:
    """SimHash 前清洗：去首尾空白、多空白合并、转小写。"""
    if not text:
        return ""
    s = re.sub(r"\s+", " ", (text or "").strip())
    return s.lower()


def _tokenize_for_simhash(text: str) -> list[str]:
    """按字符 3-gram 切分，不足 3 的保留。"""
    if not text:
        return []
    tokens = []
    for i in range(len(text)):
        tokens.append(text[i : i + 3])
    return [t for t in tokens if len(t) >= 1]


def simhash64(text: str) -> int:
    """
    对清洗后文本生成 64 位 SimHash（BIGINT）。
    算法：3-gram token → 每 token 哈希成 64 位 → 按位投票得 64 位指纹。
    """
    cleaned = clean_text_for_simhash(text)
    if not cleaned:
        return 0
    tokens = _tokenize_for_simhash(cleaned)
    if not tokens:
        return 0
    bits = [0] * 64
    for t in tokens:
        h_bytes = hashlib.sha256(t.encode("utf-8")).digest()[:8]
        h = int.from_bytes(h_bytes, "big")
        for i in range(64):
            bits[i] += (h >> i) & 1
    n = len(tokens)
    result = 0
    for i in range(64):
        if bits[i] > n / 2:
            result |= 1 << i
    return result


def _mask64(x: int) -> int:
    """保留低 64 位，转为 0..2^64-1。"""
    return x & ((1 << 64) - 1)


def simhash64_to_db(value: int) -> int:
    """
    将 simhash64() 的无符号 64 位结果转为 PostgreSQL BIGINT 可存的有符号值。
    写入 DB 时使用。
    """
    v = _mask64(value)
    return v if v < (1 << 63) else v - (1 << 64)


def simhash_from_db(value: int) -> int:
    """
    将 DB 读出的有符号 BIGINT 转为无符号 64 位，供汉明距离比较。
    """
    return _mask64(value)


def hamming_distance(a: int, b: int) -> int:
    """两个 64 位整数的汉明距离（不同位的个数）。a、b 可为无符号或 DB 读出的有符号。"""
    ua, ub = _mask64(a), _mask64(b)
    x = ua ^ ub
    return bin(x).count("1")
