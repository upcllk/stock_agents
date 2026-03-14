"""
PostgreSQL 连接。使用 config.settings 中的 DATABASE_URL。
"""
import psycopg2
from psycopg2.extras import RealDictCursor

from config.settings import DATABASE_URL


def get_connection():
    """
    返回一个新的数据库连接。调用方负责关闭或使用 with 语句。

    用法:
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT 1")
        finally:
            conn.close()

        或:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT 1")
    """
    return psycopg2.connect(DATABASE_URL)


def get_cursor(connection=None, *, dict_cursor=True):
    """
    在连接上打开游标。若传入 connection 则使用该连接（调用方负责关闭）；
    否则创建新连接并在退出时关闭（仅适合短操作）。

    用法:
        with get_cursor() as cur:
            cur.execute("SELECT * FROM company_watchlist WHERE enabled = TRUE")
            rows = cur.fetchall()
    """
    if connection is not None:
        cursor_factory = RealDictCursor if dict_cursor else None
        return connection.cursor(cursor_factory=cursor_factory)

    class _CursorContext:
        def __init__(self, dict_cursor=True):
            self.conn = get_connection()
            self.cursor_factory = RealDictCursor if dict_cursor else None

        def __enter__(self):
            self.cursor = self.conn.cursor(cursor_factory=self.cursor_factory)
            return self.cursor

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.cursor.close()
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            self.conn.close()
            return False

    return _CursorContext(dict_cursor=dict_cursor)
