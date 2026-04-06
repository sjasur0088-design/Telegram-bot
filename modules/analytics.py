import logging
import sqlite3
from datetime import datetime

def init_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            lang TEXT,
            role TEXT,
            event_type TEXT,
            event_value TEXT,
            created_at TEXT
        )
        '''
    )
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_type TEXT,
            title TEXT,
            user_id INTEGER,
            username TEXT,
            lang TEXT,
            role TEXT,
            status TEXT DEFAULT 'new',
            payload_json TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        '''
    )
    conn.commit()
    conn.close()

def track(db_path: str, uid: int, username: str, lang: str, role: str, event_type: str, event_value: str = "") -> None:
    try:
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO analytics (user_id, username, lang, role, event_type, event_value, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                uid,
                username or "",
                lang or "ru",
                role or "",
                event_type or "",
                event_value or "",
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        logging.exception("Failed to track analytics event")

def is_admin(admin_chat_id: str, uid: int) -> bool:
    return bool(str(admin_chat_id).strip()) and str(uid) == str(admin_chat_id).strip()
