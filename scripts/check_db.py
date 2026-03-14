#!/usr/bin/env python3
"""
验证数据库连接。需在项目根目录执行：python scripts/check_db.py
"""
import sys

# 保证从项目根运行时能导入 config 和 app
sys.path.insert(0, ".")


def main():
    from config.settings import DATABASE_URL
    from app.db.database import get_connection

    # 隐藏密码，只显示用于提示的连接信息
    safe_url = DATABASE_URL
    if "@" in safe_url and ":" in safe_url.split("@")[0]:
        user_part = safe_url.split("//")[1].split("@")[0]
        if ":" in user_part:
            safe_url = DATABASE_URL.replace(user_part, user_part.split(":")[0] + ":****")
    print("连接:", safe_url)

    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                row = cur.fetchone()
                print("成功连接 PostgreSQL")
                print("版本:", row[0][:80] + "..." if len(row[0]) > 80 else row[0])
                cur.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' ORDER BY table_name;"
                )
                tables = [r[0] for r in cur.fetchall()]
                if tables:
                    print("当前库中的表:", ", ".join(tables))
                else:
                    print("当前库中尚无表，可执行: psql -d stock_agents -f scripts/init_db.sql")
            return 0
        finally:
            conn.close()
    except Exception as e:
        print("连接失败:", e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
