#!/usr/bin/env python3
"""
验证 search_service。需在项目根目录执行：python scripts/check_search.py
"""
import sys

sys.path.insert(0, ".")


def main():
    from config.settings import SEARCH_PROVIDER
    from app.services import get_search_service

    print("SEARCH_PROVIDER:", SEARCH_PROVIDER)

    try:
        svc = get_search_service()
        items = svc.search_news("Tesla")
        print("成功调用 search_service")
        print("search_news('Tesla') 返回条数:", len(items))
        for i, item in enumerate(items, 1):
            print(f"  [{i}] {item.title} | {item.source} | {item.date}")
        return 0
    except Exception as e:
        print("调用失败:", e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
