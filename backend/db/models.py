"""SQLite 数据库：存对话历史，支持多轮对话上下文。

特性：
- WAL 模式：支持并发读写
- 连接复用：减少频繁开关开销
"""
import json
import logging
import sqlite3
import threading
from datetime import datetime
from backend.config import DATABASE_URL, MAX_HISTORY_TURNS

logger = logging.getLogger(__name__)

# 线程本地连接（每个线程复用同一个连接）
_local = threading.local()


def get_db() -> sqlite3.Connection:
    """获取当前线程的数据库连接（自动复用）。"""
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(DATABASE_URL)
        conn.row_factory = sqlite3.Row
        # 启用 WAL 模式（Write-Ahead Logging，支持并发读写）
        conn.execute("PRAGMA journal_mode=WAL")
        # 外键约束
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return conn


def init_db():
    """初始化数据库表（应用启动时调用一次）。"""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            sources TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_session_id
        ON conversations(session_id)
    """)
    conn.commit()
    logger.info("SQLite 数据库初始化完成: %s", DATABASE_URL)


def save_conversation(
    session_id: str, role: str, content: str, sources: list[str] | None = None
):
    """保存一条对话记录。"""
    conn = get_db()
    conn.execute(
        "INSERT INTO conversations (session_id, role, content, sources) VALUES (?, ?, ?, ?)",
        (session_id, role, content, json.dumps(sources, ensure_ascii=False) if sources else None),
    )
    conn.commit()


def get_conversation_history(session_id: str) -> list[dict]:
    """获取指定会话的对话历史（最近 N 轮）。"""
    conn = get_db()
    rows = conn.execute(
        """SELECT role, content FROM (
            SELECT id, role, content FROM conversations
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
        ) ORDER BY id ASC""",
        (session_id, MAX_HISTORY_TURNS * 2),
    ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in rows]
