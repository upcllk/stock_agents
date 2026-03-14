"""
PostgreSQL 连接与会话。使用 config.settings 中的 DATABASE_URL。
- get_connection / get_cursor：原始 psycopg2 连接（兼容旧用法）。
- engine / get_session：SQLAlchemy 引擎与会话，供 repository 层 CRUD 使用。
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.settings import DATABASE_URL

# SQLAlchemy 引擎与会话工厂（供 app.db.repository 使用）
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class _SessionContext:
    """Session 上下文：退出时 commit（成功）或 rollback（异常）并关闭。"""

    def __init__(self) -> None:
        self._session = SessionLocal()

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._session.commit()
        else:
            self._session.rollback()
        self._session.close()
        return False


def get_session():
    """
    返回一个 SQLAlchemy Session 上下文管理器。退出时自动 commit/rollback 并关闭。

    用法:
        with get_session() as session:
            repo = CompanyWatchlistRepository(session)
            companies = repo.list_enabled()
    """
    return _SessionContext()


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
