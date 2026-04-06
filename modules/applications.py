import json
import logging
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from .keyboards import admin_app_status_kb

def save_application(db_path: str, app_type: str, title: str, uid: int, username: str, lang: str, role: str, payload: Dict[str, Any]) -> int:
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        '''
        INSERT INTO applications
        (app_type, title, user_id, username, lang, role, status, payload_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 'new', ?, ?, ?)
        ''',
        (app_type, title, uid, username or "", lang or "ru", role or "", json.dumps(payload, ensure_ascii=False), now, now),
    )
    conn.commit()
    app_id = int(cur.lastrowid)
    conn.close()
    return app_id

def get_application(db_path: str, app_id: int) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    data = dict(row)
    try:
        data["payload"] = json.loads(data.get("payload_json") or "{}")
    except Exception:
        data["payload"] = {}
    return data

def update_application_status(db_path: str, app_id: int, status: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE applications SET status = ?, updated_at = ? WHERE id = ?", (status, datetime.utcnow().isoformat(), app_id))
    conn.commit()
    conn.close()

def list_applications(db_path: str, app_type: str = None, status: str = None, limit: int = 20) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    query = "SELECT * FROM applications WHERE 1=1"
    params = []
    if app_type:
        query += " AND app_type = ?"
        params.append(app_type)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    result = []
    for row in rows:
        item = dict(row)
        try:
            item["payload"] = json.loads(item.get("payload_json") or "{}")
        except Exception:
            item["payload"] = {}
        result.append(item)
    return result

def status_text(t_func, lang: str, status: str) -> str:
    return {
        "new": t_func(lang, "status_new"),
        "accepted": t_func(lang, "status_accepted"),
        "in_work": t_func(lang, "status_in_work"),
        "closed": t_func(lang, "status_closed"),
    }.get(status, status)

def _payload_brief(payload: Dict[str, Any]) -> str:
    ordered = ["service", "price", "name", "tg", "phone", "tnved", "product", "from", "to", "weight", "question", "comment"]
    lines = []
    for key in ordered:
        value = payload.get(key)
        if value:
            lines.append(f"• {key}: {value}")
    docs = payload.get("documents") or []
    if docs:
        lines.append(f"• documents: {len(docs)}")
    return "\n".join(lines)

def admin_apps_text(db_path: str, t_func, lang: str, app_type: str = None, status: str = None) -> str:
    rows = list_applications(db_path=db_path, app_type=app_type, status=status, limit=20)
    if not rows:
        return t_func(lang, "admin_apps_empty")
    type_map = {
        "specialist": "👨‍💼 Specialist",
        "broker": "💼 Broker PRO",
        "logistics": "🚚 Logistics",
    }
    parts = [f"<b>{t_func(lang, 'admin_apps')}</b>"]
    for row in rows:
        payload = row.get("payload") or {}
        parts.append(
            f"\n<b>#{row['id']} · {type_map.get(row.get('app_type'), row.get('app_type','-'))}</b>\n"
            f"Status: {status_text(t_func, lang, row.get('status', 'new'))}\n"
            f"Title: {row.get('title','-')}\n"
            f"User ID: <code>{row.get('user_id')}</code>\n"
            f"Username: @{row.get('username') or '-'}\n"
            f"Role: {row.get('role') or '-'}\n"
            f"Created: {row.get('created_at') or '-'}"
        )
        brief = _payload_brief(payload)
        if brief:
            parts.append(brief)
    return "\n".join(parts)

async def send_specialist_application_to_admin(*, bot, admin_chat_id: str, db_path: str, uid: int, username: str, form_data: Dict[str, Any], role: str, lang: str):
    app_id = save_application(
        db_path=db_path,
        app_type="specialist",
        title="Заявка специалисту" if lang == "ru" else "Mutaxassisga ariza",
        uid=uid,
        username=username,
        lang=lang,
        role=role,
        payload=form_data,
    )
    msg = (
        f"👨‍💼 <b>Новая заявка специалисту</b>\n\n"
        f"ID заявки: <code>{app_id}</code>\n"
        f"Имя: {form_data.get('name','')}\n"
        f"Telegram: {form_data.get('tg','')}\n"
        f"Телефон: {form_data.get('phone','')}\n"
        f"Вопрос: {form_data.get('question','')}\n"
        f"Роль: {role or '-'}\n"
        f"ID клиента: <code>{uid}</code>\n"
        f"Username: @{username or '-'}"
    )
    if admin_chat_id:
        try:
            await bot.send_message(int(admin_chat_id), msg, reply_markup=admin_app_status_kb(app_id, "new"))
        except Exception:
            logging.exception("Failed to send specialist application to admin")
    return app_id
