"""SQLite 数据库：存对话历史，支持多轮对话上下文。"""
import json
import sqlite3
from datetime import datetime
from backend.config import DATABASE_URL, MAX_HISTORY_TURNS


def get_db() -> sqlite3.Connection:
    """获取数据库连接。"""
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
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
    conn.close()


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
    conn.close()


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
    conn.close()
    return [{"role": row["role"], "content": row["content"]} for row in rows]
