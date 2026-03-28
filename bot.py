import os
import re
import json
import sqlite3
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils import executor
from openai import OpenAI

load_dotenv()

# =========================
# ENV
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0") or 0)
ANALYTICS_DB_PATH = os.getenv("ANALYTICS_DB_PATH", "analytics.db").strip()

logging.basicConfig(level=logging.INFO)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# =========================
# TEXTS
# =========================
TXT = {
    "ru": {
        "choose_lang": "Выберите язык:",
        "main_menu": "Главное меню:",
        "back_main": "⬅️ Назад в главное меню",
        "back": "⬅️ Назад",
        "menu_phys": "👤 Для физ лиц",
        "menu_legal": "🏢 Для юр лиц",
        "menu_broker": "📊 Для брокеров",
        "menu_logistics": "🚚 Логистика",

        "legal_intro": (
            "<b>Для юридических лиц</b>\n\n"
            "Наши специалисты имеют 10–15 лет опыта в таможенной сфере и помогут по вопросам:\n"
            "• ТН ВЭД и ставок\n"
            "• импорта и экспорта\n"
            "• документов\n"
            "• сертификации\n\n"
            "Вы можете получить общую информацию сразу в боте, а точный ответ по вашему кейсу "
            "специалист даст <b>бесплатно в течение дня</b>."
        ),
        "legal_tnved": "1️⃣ ТН ВЭД и ставки",
        "legal_exact": "2️⃣ 🎯 Точный код и ставка",
        "legal_specialist": "3️⃣ 👨‍💼 Связь со специалистом",
        "legal_ai": "4️⃣ 💬 Чат с помощником",

        "ai_intro": (
            "<b>Чат с помощником</b>\n\n"
            "Вы можете выбрать частый вопрос или задать свой.\n"
            "Помощник отвечает только по вопросам:\n"
            "• таможни\n"
            "• импорта и экспорта\n"
            "• ТН ВЭД\n"
            "• документов\n"
            "• сертификации\n"
            "• ставок и платежей\n\n"
            "Если нужен точный ответ по вашему кейсу, специалист поможет <b>бесплатно</b>."
        ),
        "faq_1": "Какие документы нужны для импорта?",
        "faq_2": "Какие документы нужны для экспорта?",
        "faq_3": "Что такое ТН ВЭД код?",
        "faq_4": "От чего считаются пошлины?",
        "faq_5": "Какие сертификаты могут понадобиться?",
        "faq_6": "Как определить код товара?",
        "ask_own_question": "✍️ Задать свой вопрос",
        "free_specialist_hint": "Если хотите, я могу бесплатно передать ваш вопрос специалисту.",

        "specialist_intro": (
            "<b>Связь со специалистом</b>\n\n"
            "Опишите ваш вопрос, и мы передадим его специалисту.\n"
            "Специалист ответит <b>бесплатно в течение дня</b>."
        ),
        "enter_name": "Введите ваше имя:",
        "enter_telegram": "Укажите ваш Telegram (username или номер):",
        "enter_phone": "Введите номер телефона:",
        "enter_question": "Опишите ваш вопрос:",
        "specialist_sent": "✅ Ваша заявка отправлена.\n\nСпециалист свяжется с вами в течение дня.",

        "exact_prompt": "Введите первые 4 цифры кода ТН ВЭД.\n\nНапример: 8703",
        "exact_bad": "Введите именно 4 цифры кода. Например: 8703",
        "not_found": "По вашему запросу ничего не найдено.",

        "tnved_intro": "Выберите категорию товара:",
        "cat_auto": "🚗 Авто",
        "cat_home": "📱 Бытовая техника",
        "cat_agro": "🌾 Сельхоз продукция",
        "cat_cosm": "🧴 Косметика",
        "cat_build": "🧱 Стройматериалы",
        "cat_clothes": "👕 Одежда",
        "cat_electronics": "💻 Электроника",
        "cat_food": "🍎 Продукты питания",
        "cat_equipment": "🔧 Оборудование",
        "cat_other": "📦 Прочее",

        "broker_intro": (
            "<b>Профессиональная поддержка для брокеров и импортеров</b>\n\n"
            "Наши эксперты имеют 10–15 лет практического опыта в таможенной сфере Узбекистана.\n\n"
            "Мы помогаем:\n"
            "• избежать переплат по таможенной стоимости\n"
            "• проверить документы до подачи\n"
            "• заранее понять требования по сертификации\n"
            "• подготовить кейс для специалиста\n\n"
            "💡 Разбор кейса: <b>Как не переплатить $1000 на ровном месте</b>"
        ),
        "broker_service_1": "1️⃣ Анализ таможенной стоимости",
        "broker_service_2": "2️⃣ Проверка документов перед подачей",
        "broker_service_3": "3️⃣ Нюансы по сертификации",
        "broker_service_4": "4️⃣ Аналитика по ТН ВЭД коду",
        "broker_price_1": "📉 1 год: минимальная и средняя стоимость — 300 000 сум",
        "broker_price_2": "📊 3 месяца: конкретная база по товару — 600 000 сум",
        "broker_price_3": "📄 Проверка документов — от 300 000 до 500 000 сум",
        "broker_price_4": "📑 Сертификация — 300 000 сум",
        "broker_price_5": "📈 Excel по 1 коду ТН ВЭД за год — 500 000 сум",
        "enter_product": "Укажите товар:",
        "enter_brand": "Укажите бренд / модель:",
        "enter_country": "Укажите страну происхождения:",
        "enter_quantity": "Укажите количество / объём партии:",
        "enter_tnved_optional": "Введите код ТН ВЭД, если есть. Если нет — напишите: нет",
        "enter_comment": "Добавьте комментарий:",
        "request_created": "✅ Ваша заявка №{request_id} создана.\n\nСпециалист получит её и свяжется с вами.",

        "log_intro": (
            "<b>Логистика</b>\n\n"
            "Мы собираем предложения от проверенных логистов, а вы выбираете лучший вариант.\n\n"
            "Что вы получаете:\n"
            "• доставка из Китая, Кореи, Европы и СНГ\n"
            "• одна заявка → несколько предложений\n"
            "• выбор по цене и срокам\n\n"
            "Бонус:\n"
            "помощь по документам и растаможке\n\n"
            "У нас есть 10 проверенных логистов.\n"
            "Мы подберём для вас 3–4 лучших варианта."
        ),
        "log_apply": "📝 Оставить заявку",
        "log_how": "ℹ️ Как это работает",
        "log_how_text": (
            "<b>Как это работает:</b>\n\n"
            "1. Вы оставляете заявку\n"
            "2. Мы передаём её логистам\n"
            "3. Получаем предложения\n"
            "4. Отправляем вам 3–4 варианта\n\n"
            "Вы сами выбираете лучшую цену и сроки."
        ),
        "enter_from": "Откуда груз:",
        "enter_to": "Куда доставить:",
        "enter_weight": "Вес или объём груза:",
        "log_created": "✅ Ваша заявка принята.\n\nМы подберём варианты и свяжемся с вами.",

        "admin_panel": "Панель администратора",
        "admin_new": "🆕 Новые заявки",
        "admin_progress": "🔄 В работе",
        "admin_done": "✅ Завершённые",
        "admin_all": "📋 Все заявки",
        "no_requests": "Заявок пока нет.",
        "contact_label": "Контакт клиента",
        "user_notified_in_work": "Ваша заявка №{request_id} принята в работу. С вами скоро свяжется специалист.",
        "user_notified_done": "Ваша заявка №{request_id} обработана. Спасибо!",

        "phys_placeholder": (
            "Раздел для физ лиц пока оставлен без изменений.\n"
            "При необходимости можно доработать его отдельно."
        ),
        "only_customs": "Я помощник только по вопросам таможни, импорта, экспорта, ТН ВЭД, документов и сертификации.",
    },
    "uz": {
        "choose_lang": "Tilni tanlang:",
        "main_menu": "Asosiy menyu:",
        "back_main": "⬅️ Asosiy menyuga qaytish",
        "back": "⬅️ Orqaga",
        "menu_phys": "👤 Jismoniy shaxslar",
        "menu_legal": "🏢 Yuridik shaxslar",
        "menu_broker": "📊 Brokerlar",
        "menu_logistics": "🚚 Logistika",
    },
}

BROKER_PRICES = {
    "min_avg": 300000,
    "3m_base": 600000,
    "docs_check_from": 300000,
    "docs_check_to": 500000,
    "certification": 300000,
    "tnved_analytics": 500000,
}

SERVICE_LABELS_RU = {
    "min_avg": "Анализ стоимости за 1 год (мин. и средняя)",
    "3m_base": "Конкретная база за 3 месяца",
    "docs_check": "Проверка документов перед подачей",
    "certification": "Нюансы по сертификации",
    "tnved_analytics": "Аналитика по ТН ВЭД коду за год",
    "specialist_request": "Связь со специалистом",
    "logistics_request": "Логистическая заявка",
}

# =========================
# DB
# =========================
def ensure_parent_dir(path: str):
    dirname = os.path.dirname(path)
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname, exist_ok=True)

def db_conn():
    ensure_parent_dir(ANALYTICS_DB_PATH)
    conn = sqlite3.connect(ANALYTICS_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            full_name TEXT,
            lang TEXT,
            role TEXT,
            service_type TEXT,
            service_label TEXT,
            price_text TEXT,
            telegram_contact TEXT,
            phone TEXT,
            product TEXT,
            brand TEXT,
            country TEXT,
            quantity TEXT,
            tnved_code TEXT,
            route_from TEXT,
            route_to TEXT,
            comment TEXT,
            question TEXT,
            status TEXT DEFAULT 'new',
            assigned_to INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            lang TEXT,
            role TEXT,
            event_type TEXT,
            event_value TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    return conn

def track(user_id: int, username: str, lang: str, role: str, event_type: str, event_value: str = ""):
    try:
        conn = db_conn()
        conn.execute(
            "INSERT INTO events (user_id, username, lang, role, event_type, event_value, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, username or "", lang or "ru", role or "", event_type, event_value, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()
    except Exception:
        logging.exception("track failed")

def create_request(data: Dict[str, Any]) -> int:
    conn = db_conn()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute("""
        INSERT INTO requests (
            user_id, username, full_name, lang, role, service_type, service_label, price_text,
            telegram_contact, phone, product, brand, country, quantity, tnved_code,
            route_from, route_to, comment, question, status, assigned_to, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', NULL, ?, ?)
    """, (
        data.get("user_id"),
        data.get("username", ""),
        data.get("full_name", ""),
        data.get("lang", "ru"),
        data.get("role", ""),
        data.get("service_type", ""),
        data.get("service_label", ""),
        data.get("price_text", ""),
        data.get("telegram_contact", ""),
        data.get("phone", ""),
        data.get("product", ""),
        data.get("brand", ""),
        data.get("country", ""),
        data.get("quantity", ""),
        data.get("tnved_code", ""),
        data.get("route_from", ""),
        data.get("route_to", ""),
        data.get("comment", ""),
        data.get("question", ""),
        now,
        now,
    ))
    rid = cur.lastrowid
    conn.commit()
    conn.close()
    return rid

def get_request(request_id: int):
    conn = db_conn()
    row = conn.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone()
    conn.close()
    return row

def list_requests(status: Optional[str] = None, limit: int = 20):
    conn = db_conn()
    if status:
        rows = conn.execute(
            "SELECT * FROM requests WHERE status = ? ORDER BY id DESC LIMIT ?",
            (status, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM requests ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return rows

def update_request_status(request_id: int, status: str, assigned_to: Optional[int] = None):
    conn = db_conn()
    now = datetime.utcnow().isoformat()
    if assigned_to is not None:
        conn.execute(
            "UPDATE requests SET status = ?, assigned_to = ?, updated_at = ? WHERE id = ?",
            (status, assigned_to, now, request_id)
        )
    else:
        conn.execute(
            "UPDATE requests SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, request_id)
        )
    conn.commit()
    conn.close()

def stats_summary() -> str:
    conn = db_conn()
    total = conn.execute("SELECT COUNT(*) c FROM requests").fetchone()["c"]
    new = conn.execute("SELECT COUNT(*) c FROM requests WHERE status='new'").fetchone()["c"]
    progress = conn.execute("SELECT COUNT(*) c FROM requests WHERE status='in_progress'").fetchone()["c"]
    done = conn.execute("SELECT COUNT(*) c FROM requests WHERE status='done'").fetchone()["c"]

    by_type = conn.execute("""
        SELECT service_type, COUNT(*) c
        FROM requests
        GROUP BY service_type
        ORDER BY c DESC
    """).fetchall()
    conn.close()

    lines = [
        "<b>📊 Статистика бота</b>",
        "",
        f"Всего заявок: {total}",
        f"Новые: {new}",
        f"В работе: {progress}",
        f"Завершённые: {done}",
        "",
        "<b>По услугам:</b>",
    ]
    if by_type:
        for row in by_type:
            lines.append(f"• {row['service_type']}: {row['c']}")
    else:
        lines.append("• Пока нет данных")
    return "\n".join(lines)

# =========================
# USER CTX
# =========================
USER_CTX: Dict[int, Dict[str, Any]] = {}

def get_ctx(uid: int) -> Dict[str, Any]:
    if uid not in USER_CTX:
        USER_CTX[uid] = {
            "lang": None,
            "section": None,
            "mode": None,
            "pending_form": None,
            "form_data": {},
        }
    return USER_CTX[uid]

def reset_ctx(uid: int):
    USER_CTX[uid] = {
        "lang": None,
        "section": None,
        "mode": None,
        "pending_form": None,
        "form_data": {},
    }

def t(lang: str, key: str) -> str:
    if key in TXT.get(lang or "ru", {}):
        return TXT[lang or "ru"][key]
    return TXT["ru"].get(key, key)

# =========================
# LOAD PRODUCT DB
# =========================
PRODUCT_DB: List[Dict[str, Any]] = []

def load_product_db():
    global PRODUCT_DB
    PRODUCT_DB = []
    for i in range(1, 7):
        fname = f"product_db_part{i}.json"
        path = os.path.join(os.getcwd(), fname)
        if os.path.exists(path):
            logging.info("Loading DB file: %s", path)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    PRODUCT_DB.extend(data)
    logging.info("Loaded records: %s", len(PRODUCT_DB))

# =========================
# HELPERS
# =========================
def format_sum(value: int) -> str:
    return f"{value:,}".replace(",", " ") + " сум"

def safe_get(item: Dict[str, Any], *keys: str, default: str = "уточняется") -> str:
    for k in keys:
        if k in item and str(item.get(k)).strip():
            return str(item.get(k))
    return default

def normalize_code(code: str) -> str:
    return re.sub(r"\D", "", str(code or ""))

def search_by_code_prefix(code_prefix: str, limit: int = 10) -> List[Dict[str, Any]]:
    prefix = normalize_code(code_prefix)
    out = []
    if not prefix:
        return out
    for item in PRODUCT_DB:
        item_code = normalize_code(safe_get(item, "code", default=""))
        if item_code.startswith(prefix):
            out.append(item)
            if len(out) >= limit:
                break
    return out

def search_tnved(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    q = query.lower().strip()
    if not q:
        return []
    results = []
    words = [w for w in re.split(r"\s+", q) if w]
    for item in PRODUCT_DB:
        text = " ".join([
            safe_get(item, "code", default=""),
            safe_get(item, "name", "title", "description", default=""),
        ]).lower()
        score = 0
        for w in words:
            if w in text:
                score += 1
        if score:
            results.append((score, item))
    results.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in results[:limit]]

def format_tnved_item(item: Dict[str, Any]) -> str:
    code = safe_get(item, "code", default="-")
    name = safe_get(item, "name", "title", "description", default="-")
    duty = safe_get(item, "duty", "duty_rate", "boj", default="уточняется")
    vat = safe_get(item, "vat", "nds", default="12%")
    excise = safe_get(item, "excise", "akciz", default="нет данных")
    util = safe_get(item, "util_fee", "util", "utilsbor", default="нет данных")
    return (
        f"<b>{code}</b>\n"
        f"{name}\n"
        f"• Пошлина: {duty}\n"
        f"• НДС: {vat}\n"
        f"• Акциз: {excise}\n"
        f"• Утильсбор: {util}"
    )

def format_matches(matches: List[Dict[str, Any]], header: Optional[str] = None) -> str:
    lines = []
    if header:
        lines.append(header)
        lines.append("")
    for item in matches:
        lines.append(format_tnved_item(item))
        lines.append("")
    return "\n".join(lines).strip()

def split_text(text: str, limit: int = 4000) -> List[str]:
    if len(text) <= limit:
        return [text]
    chunks, cur = [], ""
    for part in text.split("\n"):
        nxt = (cur + "\n" + part).strip() if cur else part
        if len(nxt) <= limit:
            cur = nxt
        else:
            if cur:
                chunks.append(cur)
            while len(part) > limit:
                chunks.append(part[:limit])
                part = part[limit:]
            cur = part
    if cur:
        chunks.append(cur)
    return chunks

async def safe_answer(message: types.Message, text: str, reply_markup=None):
    for i, chunk in enumerate(split_text(text)):
        await message.answer(chunk, reply_markup=reply_markup if i == len(split_text(text)) - 1 else None)

def extract_code(text: str) -> Optional[str]:
    m = re.search(r"\b\d{4,10}\b", text or "")
    return m.group(0) if m else None

def is_customs_question(text: str) -> bool:
    text = (text or "").lower()
    keywords = [
        "тн вэд", "код", "импорт", "экспорт", "документ", "сертифик", "пошлин",
        "ндс", "тамож", "утиль", "акциз", "ставк", "оформлен", "декларац"
    ]
    return any(k in text for k in keywords) or bool(extract_code(text))

def ask_ai_comment(question: str, db_context: str = "") -> str:
    if not client:
        return "AI-комментарий временно недоступен."
    prompt = (
        "Ты помощник по таможенным вопросам Узбекистана.\n"
        "Если пользователю переданы результаты из базы ТН ВЭД:\n"
        "1. Сначала опирайся на найденные ставки и коды.\n"
        "2. Не скрывай пошлины, НДС, акциз и утильсбор, если они есть в контексте.\n"
        "3. Уточнение предлагай только после показа найденных ставок.\n"
        "4. Отвечай только по таможенной теме.\n"
        "5. Дай короткий, практический комментарий без воды.\n\n"
        f"Контекст из базы:\n{db_context}\n\n"
        f"Вопрос пользователя:\n{question}"
    )
    try:
        resp = client.responses.create(
            model=OPENAI_MODEL,
            input=prompt,
            max_output_tokens=350,
        )
        text = getattr(resp, "output_text", None)
        if text:
            return text.strip()
        return "Комментарий временно недоступен."
    except Exception:
        logging.exception("OpenAI request failed")
        return "Комментарий временно недоступен."

def request_card(row) -> str:
    return (
        f"📥 <b>Заявка #{row['id']}</b>\n\n"
        f"<b>Услуга:</b> {row['service_label']}\n"
        f"<b>Цена:</b> {row['price_text'] or '-'}\n"
        f"<b>Статус:</b> {row['status'].upper()}\n\n"
        f"<b>Имя:</b> {row['full_name'] or '-'}\n"
        f"<b>Telegram:</b> {row['telegram_contact'] or ('@' + row['username'] if row['username'] else '-')}\n"
        f"<b>Телефон:</b> {row['phone'] or '-'}\n"
        f"<b>ID:</b> <code>{row['user_id']}</code>\n\n"
        f"<b>Товар:</b> {row['product'] or '-'}\n"
        f"<b>Бренд:</b> {row['brand'] or '-'}\n"
        f"<b>Страна:</b> {row['country'] or '-'}\n"
        f"<b>Количество:</b> {row['quantity'] or '-'}\n"
        f"<b>Код ТН ВЭД:</b> {row['tnved_code'] or '-'}\n"
        f"<b>Маршрут:</b> {row['route_from'] or '-'} → {row['route_to'] or '-'}\n"
        f"<b>Вопрос:</b> {row['question'] or '-'}\n"
        f"<b>Комментарий:</b> {row['comment'] or '-'}"
    )

def is_admin(user_id: int) -> bool:
    return bool(ADMIN_CHAT_ID and int(user_id) == int(ADMIN_CHAT_ID))

async def send_request_to_admin(request_id: int):
    if not ADMIN_CHAT_ID:
        return
    row = get_request(request_id)
    if not row:
        return
    await bot.send_message(
        ADMIN_CHAT_ID,
        request_card(row),
        reply_markup=request_inline_kb(request_id)
    )

# =========================
# KEYBOARDS
# =========================
def lang_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🇷🇺 Русский", "🇺🇿 O‘zbekcha")
    return kb

def main_menu_kb(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "menu_phys"), t(lang, "menu_legal"))
    kb.add(t(lang, "menu_broker"), t(lang, "menu_logistics"))
    return kb

def legal_menu_kb(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "legal_tnved"))
    kb.add(t(lang, "legal_exact"))
    kb.add(t(lang, "legal_specialist"))
    kb.add(t(lang, "legal_ai"))
    kb.add(t(lang, "back_main"))
    return kb

def legal_categories_kb(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "cat_auto"), t(lang, "cat_home"))
    kb.add(t(lang, "cat_agro"), t(lang, "cat_cosm"))
    kb.add(t(lang, "cat_build"), t(lang, "cat_clothes"))
    kb.add(t(lang, "cat_electronics"), t(lang, "cat_food"))
    kb.add(t(lang, "cat_equipment"), t(lang, "cat_other"))
    kb.add(t(lang, "back"))
    return kb

def auto_sub_kb(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Легковые авто", "Грузовые авто")
    kb.add("Гибриды", "Электромобили")
    kb.add(t(lang, "back"))
    return kb

def home_sub_kb(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Телефоны", "Телевизоры")
    kb.add("Холодильники", "Стиральные машины")
    kb.add(t(lang, "back"))
    return kb

def agro_sub_kb(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Фрукты", "Овощи")
    kb.add("Зерно", "Семена")
    kb.add(t(lang, "back"))
    return kb

def faq_kb(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "faq_1"))
    kb.add(t(lang, "faq_2"))
    kb.add(t(lang, "faq_3"))
    kb.add(t(lang, "faq_4"))
    kb.add(t(lang, "faq_5"))
    kb.add(t(lang, "faq_6"))
    kb.add(t(lang, "ask_own_question"))
    kb.add(t(lang, "legal_specialist"))
    kb.add(t(lang, "back"))
    return kb

def broker_menu(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "broker_service_1"))
    kb.add(t(lang, "broker_service_2"))
    kb.add(t(lang, "broker_service_3"))
    kb.add(t(lang, "broker_service_4"))
    kb.add(t(lang, "back_main"))
    return kb

def logistics_menu(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "log_apply"))
    kb.add(t(lang, "log_how"))
    kb.add(t(lang, "back_main"))
    return kb

def admin_requests_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🆕 Новые заявки", "🔄 В работе")
    kb.add("✅ Завершённые", "📋 Все заявки")
    kb.add("⬅️ Назад")
    return kb

def request_inline_kb(request_id: int):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🟢 Взять в работу", callback_data=f"req_take:{request_id}"),
        InlineKeyboardButton("✅ Закрыть", callback_data=f"req_done:{request_id}"),
    )
    kb.add(
        InlineKeyboardButton("📞 Контакт", callback_data=f"req_contact:{request_id}")
    )
    return kb

# =========================
# MENUS
# =========================
async def send_main_menu(message: types.Message, uid: int):
    ctx = get_ctx(uid)
    lang = ctx.get("lang") or "ru"
    await message.answer(t(lang, "main_menu"), reply_markup=main_menu_kb(lang))

# =========================
# STARTUP
# =========================
async def on_startup(_):
    await bot.delete_webhook(drop_pending_updates=True)
    load_product_db()
    logging.info("=== FINAL CUSTOMS BOT RUNNING ===")

# =========================
# COMMANDS
# =========================
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    uid = message.from_user.id
    reset_ctx(uid)
    await message.answer(TXT["ru"]["choose_lang"], reply_markup=lang_kb())

@dp.message_handler(commands=["admin"])
async def admin_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(t("ru", "admin_panel"), reply_markup=admin_requests_kb())

@dp.message_handler(commands=["stats"])
async def stats_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(stats_summary())

# =========================
# CALLBACKS
# =========================
@dp.callback_query_handler(lambda c: c.data and c.data.startswith("req_"))
async def request_admin_actions(callback_query: types.CallbackQuery):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("Нет доступа", show_alert=True)
        return

    await callback_query.answer()
    try:
        action, request_id = callback_query.data.split(":")
        request_id = int(request_id)
    except Exception:
        return

    row = get_request(request_id)
    if not row:
        return

    if action == "req_take":
        update_request_status(request_id, "in_progress", callback_query.from_user.id)
        try:
            await bot.send_message(
                row["user_id"],
                t("ru", "user_notified_in_work").format(request_id=request_id),
            )
        except Exception:
            pass

    elif action == "req_done":
        update_request_status(request_id, "done")
        try:
            await bot.send_message(
                row["user_id"],
                t("ru", "user_notified_done").format(request_id=request_id),
            )
        except Exception:
            pass

    elif action == "req_contact":
        await callback_query.message.answer(
            f"<b>{t('ru', 'contact_label')}</b>\n\n"
            f"Имя: {row['full_name'] or '-'}\n"
            f"Telegram: {row['telegram_contact'] or ('@' + row['username'] if row['username'] else '-')}\n"
            f"Телефон: {row['phone'] or '-'}\n"
            f"ID: <code>{row['user_id']}</code>"
        )
        return

    updated = get_request(request_id)
    await callback_query.message.edit_text(
        request_card(updated),
        reply_markup=request_inline_kb(request_id)
    )

# =========================
# MAIN ROUTER
# =========================
@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def router(message: types.Message):
    uid = message.from_user.id
    username = message.from_user.username or ""
    text = (message.text or "").strip()
    ctx = get_ctx(uid)
    lang = ctx.get("lang") or "ru"
    role = ctx.get("section") or ""

    track(uid, username, lang, role, "message", text)

    # language
    if text == "🇷🇺 Русский":
        ctx["lang"] = "ru"
        await send_main_menu(message, uid)
        return

    if text == "🇺🇿 O‘zbekcha":
        ctx["lang"] = "uz"
        await send_main_menu(message, uid)
        return

    # common back
    if text in [t(lang, "back_main"), "⬅️ Назад в главное меню"]:
        ctx["section"] = None
        ctx["mode"] = None
        ctx["pending_form"] = None
        ctx["form_data"] = {}
        await send_main_menu(message, uid)
        return

    if text in [t(lang, "back"), "⬅️ Назад"]:
        if ctx.get("mode") in {"legal_auto_sub", "legal_home_sub", "legal_agro_sub", "legal_categories", "legal_ai"}:
            ctx["mode"] = None
            await message.answer(t(lang, "legal_intro"), reply_markup=legal_menu_kb(lang))
            return
        if ctx.get("section") == "logistics":
            ctx["mode"] = None
            await message.answer(t(lang, "log_intro"), reply_markup=logistics_menu(lang))
            return
        if ctx.get("section") == "broker":
            ctx["mode"] = None
            await message.answer(
                t(lang, "broker_intro") + "\n\n"
                + t(lang, "broker_price_1") + "\n"
                + t(lang, "broker_price_2") + "\n"
                + t(lang, "broker_price_3") + "\n"
                + t(lang, "broker_price_4") + "\n"
                + t(lang, "broker_price_5"),
                reply_markup=broker_menu(lang)
            )
            return
        await send_main_menu(message, uid)
        return

    # admin message menu
    if is_admin(uid):
        if text == "🆕 Новые заявки":
            rows = list_requests("new", 10)
            if not rows:
                await message.answer(t("ru", "no_requests"), reply_markup=admin_requests_kb())
                return
            for row in rows:
                await message.answer(request_card(row), reply_markup=request_inline_kb(row["id"]))
            return

        if text == "🔄 В работе":
            rows = list_requests("in_progress", 10)
            if not rows:
                await message.answer(t("ru", "no_requests"), reply_markup=admin_requests_kb())
                return
            for row in rows:
                await message.answer(request_card(row), reply_markup=request_inline_kb(row["id"]))
            return

        if text == "✅ Завершённые":
            rows = list_requests("done", 10)
            if not rows:
                await message.answer(t("ru", "no_requests"), reply_markup=admin_requests_kb())
                return
            for row in rows:
                await message.answer(request_card(row), reply_markup=request_inline_kb(row["id"]))
            return

        if text == "📋 Все заявки":
            rows = list_requests(None, 10)
            if not rows:
                await message.answer(t("ru", "no_requests"), reply_markup=admin_requests_kb())
                return
            for row in rows:
                await message.answer(request_card(row), reply_markup=request_inline_kb(row["id"]))
            return

    # main menu sections
    if text == t(lang, "menu_phys"):
        ctx["section"] = "phys"
        await message.answer(t(lang, "phys_placeholder"), reply_markup=main_menu_kb(lang))
        return

    if text == t(lang, "menu_legal"):
        ctx["section"] = "legal"
        ctx["mode"] = None
        await message.answer(t(lang, "legal_intro"), reply_markup=legal_menu_kb(lang))
        return

    if text == t(lang, "menu_broker"):
        ctx["section"] = "broker"
        ctx["mode"] = None
        await message.answer(
            t(lang, "broker_intro") + "\n\n"
            + t(lang, "broker_price_1") + "\n"
            + t(lang, "broker_price_2") + "\n"
            + t(lang, "broker_price_3") + "\n"
            + t(lang, "broker_price_4") + "\n"
            + t(lang, "broker_price_5"),
            reply_markup=broker_menu(lang)
        )
        return

    if text == t(lang, "menu_logistics"):
        ctx["section"] = "logistics"
        ctx["mode"] = None
        await message.answer(t(lang, "log_intro"), reply_markup=logistics_menu(lang))
        return

    # =========================
    # LEGAL SECTION
    # =========================
    if text == t(lang, "legal_tnved"):
        ctx["mode"] = "legal_categories"
        await message.answer(t(lang, "tnved_intro"), reply_markup=legal_categories_kb(lang))
        return

    if ctx.get("mode") == "legal_categories":
        if text == t(lang, "cat_auto"):
            ctx["mode"] = "legal_auto_sub"
            await message.answer("Выберите подкатегорию:", reply_markup=auto_sub_kb(lang))
            return
        if text == t(lang, "cat_home"):
            ctx["mode"] = "legal_home_sub"
            await message.answer("Выберите подкатегорию:", reply_markup=home_sub_kb(lang))
            return
        if text == t(lang, "cat_agro"):
            ctx["mode"] = "legal_agro_sub"
            await message.answer("Выберите подкатегорию:", reply_markup=agro_sub_kb(lang))
            return

        mapping = {
            t(lang, "cat_cosm"): "косметика",
            t(lang, "cat_build"): "стройматериалы",
            t(lang, "cat_clothes"): "одежда",
            t(lang, "cat_electronics"): "электроника",
            t(lang, "cat_food"): "продукты питания",
            t(lang, "cat_equipment"): "оборудование",
            t(lang, "cat_other"): "прочее",
        }
        if text in mapping:
            q = mapping[text]
            matches = search_tnved(q, 5)
            if matches:
                await safe_answer(message, format_matches(matches, header=f"<b>{text}</b>"), reply_markup=legal_categories_kb(lang))
            else:
                await message.answer(t(lang, "not_found"), reply_markup=legal_categories_kb(lang))
            ctx["mode"] = None
            return

    if ctx.get("mode") == "legal_auto_sub":
        auto_map = {
            "Легковые авто": "легковые автомобили",
            "Грузовые авто": "грузовые автомобили",
            "Гибриды": "гибрид",
            "Электромобили": "электромобиль",
        }
        if text in auto_map:
            matches = search_tnved(auto_map[text], 5)
            if matches:
                await safe_answer(message, format_matches(matches, header=f"<b>{text}</b>"), reply_markup=legal_categories_kb(lang))
            else:
                await message.answer(t(lang, "not_found"), reply_markup=legal_categories_kb(lang))
            ctx["mode"] = None
            return

    if ctx.get("mode") == "legal_home_sub":
        home_map = {
            "Телефоны": "телефон",
            "Телевизоры": "телевизор",
            "Холодильники": "холодильник",
            "Стиральные машины": "стиральная машина",
        }
        if text in home_map:
            matches = search_tnved(home_map[text], 5)
            if matches:
                await safe_answer(message, format_matches(matches, header=f"<b>{text}</b>"), reply_markup=legal_categories_kb(lang))
            else:
                await message.answer(t(lang, "not_found"), reply_markup=legal_categories_kb(lang))
            ctx["mode"] = None
            return

    if ctx.get("mode") == "legal_agro_sub":
        agro_map = {
            "Фрукты": "фрукты",
            "Овощи": "овощи",
            "Зерно": "зерно",
            "Семена": "семена",
        }
        if text in agro_map:
            matches = search_tnved(agro_map[text], 5)
            if matches:
                await safe_answer(message, format_matches(matches, header=f"<b>{text}</b>"), reply_markup=legal_categories_kb(lang))
            else:
                await message.answer(t(lang, "not_found"), reply_markup=legal_categories_kb(lang))
            ctx["mode"] = None
            return

    if text == t(lang, "legal_exact"):
        ctx["mode"] = "legal_exact_code"
        await message.answer(t(lang, "exact_prompt"), reply_markup=legal_menu_kb(lang))
        return

    if ctx.get("mode") == "legal_exact_code":
        code4 = normalize_code(text)
        if len(code4) != 4:
            await message.answer(t(lang, "exact_bad"), reply_markup=legal_menu_kb(lang))
            return
        matches = search_by_code_prefix(code4, 10)
        if not matches:
            await message.answer(t(lang, "not_found"), reply_markup=legal_menu_kb(lang))
            ctx["mode"] = None
            return
        await safe_answer(message, format_matches(matches, header=f"<b>Варианты по коду {code4}</b>"), reply_markup=legal_menu_kb(lang))
        ctx["mode"] = None
        return

    if text == t(lang, "legal_specialist"):
        ctx["mode"] = None
        ctx["pending_form"] = "spec_name"
        ctx["form_data"] = {
            "service_type": "specialist_request",
            "service_label": SERVICE_LABELS_RU["specialist_request"],
            "price_text": "бесплатно",
        }
        await message.answer(t(lang, "specialist_intro") + "\n\n" + t(lang, "enter_name"), reply_markup=legal_menu_kb(lang))
        return

    if text == t(lang, "legal_ai"):
        ctx["mode"] = "legal_ai"
        await message.answer(t(lang, "ai_intro"), reply_markup=faq_kb(lang))
        return

    # Specialist form
    if ctx.get("pending_form") == "spec_name":
        ctx["form_data"]["full_name"] = text
        ctx["pending_form"] = "spec_telegram"
        await message.answer(t(lang, "enter_telegram"), reply_markup=legal_menu_kb(lang))
        return

    if ctx.get("pending_form") == "spec_telegram":
        ctx["form_data"]["telegram_contact"] = text
        ctx["pending_form"] = "spec_phone"
        await message.answer(t(lang, "enter_phone"), reply_markup=legal_menu_kb(lang))
        return

    if ctx.get("pending_form") == "spec_phone":
        ctx["form_data"]["phone"] = text
        ctx["pending_form"] = "spec_question"
        await message.answer(t(lang, "enter_question"), reply_markup=legal_menu_kb(lang))
        return

    if ctx.get("pending_form") == "spec_question":
        ctx["form_data"]["question"] = text
        request_id = create_request({
            "user_id": uid,
            "username": username,
            "full_name": ctx["form_data"].get("full_name", ""),
            "lang": lang,
            "role": "legal",
            "service_type": "specialist_request",
            "service_label": SERVICE_LABELS_RU["specialist_request"],
            "price_text": "бесплатно",
            "telegram_contact": ctx["form_data"].get("telegram_contact", ""),
            "phone": ctx["form_data"].get("phone", ""),
            "question": ctx["form_data"].get("question", ""),
        })
        await send_request_to_admin(request_id)
        ctx["pending_form"] = None
        ctx["form_data"] = {}
        await message.answer(t(lang, "specialist_sent"), reply_markup=legal_menu_kb(lang))
        return

    # AI chat
    if ctx.get("mode") == "legal_ai":
        faq_answers = {
            t(lang, "faq_1"): (
                "Обычно для импорта нужны:\n"
                "• контракт\n"
                "• инвойс\n"
                "• упаковочный лист\n"
                "• транспортные документы\n"
                "• при необходимости сертификаты и разрешительные документы\n\n"
                "Уточните, пожалуйста: о каком товаре идёт речь?"
            ),
            t(lang, "faq_2"): (
                "Обычно для экспорта нужны:\n"
                "• контракт\n"
                "• инвойс\n"
                "• упаковочный лист\n"
                "• транспортные документы\n"
                "• при необходимости разрешительные документы\n\n"
                "Уточните, пожалуйста: о каком товаре идёт речь?"
            ),
            t(lang, "faq_3"): (
                "ТН ВЭД код — это код товарной номенклатуры внешнеэкономической деятельности.\n"
                "По нему определяются:\n"
                "• пошлина\n"
                "• НДС\n"
                "• акциз\n"
                "• сертификация\n"
                "• ограничения и разрешения\n\n"
                "Уточните, пожалуйста: вам нужен код для конкретного товара?"
            ),
            t(lang, "faq_4"): (
                "Пошлины обычно считаются от таможенной стоимости товара.\n"
                "В зависимости от кода ТН ВЭД также могут применяться:\n"
                "• НДС\n"
                "• акциз\n"
                "• утильсбор\n"
                "• специальные сборы\n\n"
                "Уточните, пожалуйста: вы хотите рассчитать платежи по конкретному товару?"
            ),
            t(lang, "faq_5"): (
                "В зависимости от товара могут понадобиться:\n"
                "• сертификат соответствия\n"
                "• санитарно-эпидемиологическое заключение\n"
                "• разрешительные документы\n"
                "• декларация соответствия\n\n"
                "Уточните, пожалуйста: о каком товаре идёт речь?"
            ),
            t(lang, "faq_6"): (
                "Код товара определяется по его описанию, назначению, материалу, характеристикам и правилам классификации.\n\n"
                "Уточните, пожалуйста: какой именно товар нужно определить?"
            ),
        }

        if text in faq_answers:
            await message.answer(faq_answers[text] + "\n\n" + t(lang, "free_specialist_hint"), reply_markup=faq_kb(lang))
            return

        if text == t(lang, "ask_own_question"):
            await message.answer("Напишите свой вопрос.", reply_markup=faq_kb(lang))
            return

        if text == t(lang, "legal_specialist"):
            ctx["mode"] = None
            ctx["pending_form"] = "spec_name"
            ctx["form_data"] = {
                "service_type": "specialist_request",
                "service_label": SERVICE_LABELS_RU["specialist_request"],
                "price_text": "бесплатно",
            }
            await message.answer(t(lang, "specialist_intro") + "\n\n" + t(lang, "enter_name"), reply_markup=legal_menu_kb(lang))
            return

        if not is_customs_question(text):
            await message.answer(t(lang, "only_customs"), reply_markup=faq_kb(lang))
            return

        code = extract_code(text)
        matches = search_by_code_prefix(code, 5) if code else search_tnved(text, 5)

        if matches:
            db_block = format_matches(matches, header="<b>Найдено в базе:</b>")
            ai_comment = ask_ai_comment(text, db_block)
            final_text = (
                db_block
                + "\n\n<b>AI-комментарий:</b>\n"
                + ai_comment
                + "\n\n"
                + t(lang, "free_specialist_hint")
            )
            await safe_answer(message, final_text, reply_markup=faq_kb(lang))
            return

        ai_comment = ask_ai_comment(text, "")
        await safe_answer(
            message,
            ai_comment + "\n\n" + t(lang, "free_specialist_hint"),
            reply_markup=faq_kb(lang)
        )
        return

    # =========================
    # BROKER SECTION
    # =========================
    if text == t(lang, "broker_service_1"):
        ctx["pending_form"] = "broker_name"
        ctx["form_data"] = {
            "service_type": "min_avg",
            "service_label": SERVICE_LABELS_RU["min_avg"],
            "price_text": format_sum(BROKER_PRICES["min_avg"]),
        }
        await message.answer(
            f"{ctx['form_data']['service_label']}\n💰 {ctx['form_data']['price_text']}\n\n{t(lang, 'enter_name')}",
            reply_markup=broker_menu(lang)
        )
        return

    if text == t(lang, "broker_service_2"):
        ctx["pending_form"] = "broker_name"
        ctx["form_data"] = {
            "service_type": "docs_check",
            "service_label": SERVICE_LABELS_RU["docs_check"],
            "price_text": f"от {format_sum(BROKER_PRICES['docs_check_from'])} до {format_sum(BROKER_PRICES['docs_check_to'])}",
        }
        await message.answer(
            f"{ctx['form_data']['service_label']}\n💰 {ctx['form_data']['price_text']}\n\n{t(lang, 'enter_name')}",
            reply_markup=broker_menu(lang)
        )
        return

    if text == t(lang, "broker_service_3"):
        ctx["pending_form"] = "broker_name"
        ctx["form_data"] = {
            "service_type": "certification",
            "service_label": SERVICE_LABELS_RU["certification"],
            "price_text": format_sum(BROKER_PRICES["certification"]),
        }
        await message.answer(
            f"{ctx['form_data']['service_label']}\n💰 {ctx['form_data']['price_text']}\n\n{t(lang, 'enter_name')}",
            reply_markup=broker_menu(lang)
        )
        return

    if text == t(lang, "broker_service_4"):
        ctx["pending_form"] = "broker_name"
        ctx["form_data"] = {
            "service_type": "tnved_analytics",
            "service_label": SERVICE_LABELS_RU["tnved_analytics"],
            "price_text": format_sum(BROKER_PRICES["tnved_analytics"]),
        }
        await message.answer(
            f"{ctx['form_data']['service_label']}\n💰 {ctx['form_data']['price_text']}\n\n{t(lang, 'enter_name')}",
            reply_markup=broker_menu(lang)
        )
        return

    if ctx.get("pending_form") == "broker_name":
        ctx["form_data"]["full_name"] = text
        ctx["pending_form"] = "broker_product"
        await message.answer(t(lang, "enter_product"), reply_markup=broker_menu(lang))
        return

    if ctx.get("pending_form") == "broker_product":
        ctx["form_data"]["product"] = text
        ctx["pending_form"] = "broker_brand"
        await message.answer(t(lang, "enter_brand"), reply_markup=broker_menu(lang))
        return

    if ctx.get("pending_form") == "broker_brand":
        ctx["form_data"]["brand"] = text
        ctx["pending_form"] = "broker_country"
        await message.answer(t(lang, "enter_country"), reply_markup=broker_menu(lang))
        return

    if ctx.get("pending_form") == "broker_country":
        ctx["form_data"]["country"] = text
        ctx["pending_form"] = "broker_quantity"
        await message.answer(t(lang, "enter_quantity"), reply_markup=broker_menu(lang))
        return

    if ctx.get("pending_form") == "broker_quantity":
        ctx["form_data"]["quantity"] = text
        ctx["pending_form"] = "broker_tnved"
        await message.answer(t(lang, "enter_tnved_optional"), reply_markup=broker_menu(lang))
        return

    if ctx.get("pending_form") == "broker_tnved":
        ctx["form_data"]["tnved_code"] = "" if text.lower() in ["нет", "yo'q", "yoq", "no"] else text
        ctx["pending_form"] = "broker_comment"
        await message.answer(t(lang, "enter_comment"), reply_markup=broker_menu(lang))
        return

    if ctx.get("pending_form") == "broker_comment":
        ctx["form_data"]["comment"] = text
        request_id = create_request({
            "user_id": uid,
            "username": username,
            "full_name": ctx["form_data"].get("full_name", ""),
            "lang": lang,
            "role": "broker",
            "service_type": ctx["form_data"].get("service_type", ""),
            "service_label": ctx["form_data"].get("service_label", ""),
            "price_text": ctx["form_data"].get("price_text", ""),
            "product": ctx["form_data"].get("product", ""),
            "brand": ctx["form_data"].get("brand", ""),
            "country": ctx["form_data"].get("country", ""),
            "quantity": ctx["form_data"].get("quantity", ""),
            "tnved_code": ctx["form_data"].get("tnved_code", ""),
            "comment": ctx["form_data"].get("comment", ""),
        })
        await send_request_to_admin(request_id)
        ctx["pending_form"] = None
        ctx["mode"] = None
        ctx["form_data"] = {}
        await message.answer(t(lang, "request_created").format(request_id=request_id))
        await send_main_menu(message, uid)
        return

    # =========================
    # LOGISTICS SECTION
    # =========================
    if text == t(lang, "log_how"):
        await message.answer(t(lang, "log_how_text"), reply_markup=logistics_menu(lang))
        return

    if text == t(lang, "log_apply"):
        ctx["pending_form"] = "log_name"
        ctx["form_data"] = {
            "service_type": "logistics_request",
            "service_label": SERVICE_LABELS_RU["logistics_request"],
            "price_text": "",
        }
        await message.answer(t(lang, "enter_name"), reply_markup=logistics_menu(lang))
        return

    if ctx.get("pending_form") == "log_name":
        ctx["form_data"]["full_name"] = text
        ctx["pending_form"] = "log_tg"
        await message.answer(t(lang, "enter_telegram"), reply_markup=logistics_menu(lang))
        return

    if ctx.get("pending_form") == "log_tg":
        ctx["form_data"]["telegram_contact"] = text
        ctx["pending_form"] = "log_phone"
        await message.answer(t(lang, "enter_phone"), reply_markup=logistics_menu(lang))
        return

    if ctx.get("pending_form") == "log_phone":
        ctx["form_data"]["phone"] = text
        ctx["pending_form"] = "log_from"
        await message.answer(t(lang, "enter_from"), reply_markup=logistics_menu(lang))
        return

    if ctx.get("pending_form") == "log_from":
        ctx["form_data"]["route_from"] = text
        ctx["pending_form"] = "log_to"
        await message.answer(t(lang, "enter_to"), reply_markup=logistics_menu(lang))
        return

    if ctx.get("pending_form") == "log_to":
        ctx["form_data"]["route_to"] = text
        ctx["pending_form"] = "log_product"
        await message.answer(t(lang, "enter_product"), reply_markup=logistics_menu(lang))
        return

    if ctx.get("pending_form") == "log_product":
        ctx["form_data"]["product"] = text
        ctx["pending_form"] = "log_weight"
        await message.answer(t(lang, "enter_weight"), reply_markup=logistics_menu(lang))
        return

    if ctx.get("pending_form") == "log_weight":
        ctx["form_data"]["quantity"] = text
        ctx["pending_form"] = "log_comment"
        await message.answer(t(lang, "enter_comment"), reply_markup=logistics_menu(lang))
        return

    if ctx.get("pending_form") == "log_comment":
        ctx["form_data"]["comment"] = text
        request_id = create_request({
            "user_id": uid,
            "username": username,
            "full_name": ctx["form_data"].get("full_name", ""),
            "lang": lang,
            "role": "logistics",
            "service_type": "logistics_request",
            "service_label": SERVICE_LABELS_RU["logistics_request"],
            "price_text": "",
            "telegram_contact": ctx["form_data"].get("telegram_contact", ""),
            "phone": ctx["form_data"].get("phone", ""),
            "route_from": ctx["form_data"].get("route_from", ""),
            "route_to": ctx["form_data"].get("route_to", ""),
            "product": ctx["form_data"].get("product", ""),
            "quantity": ctx["form_data"].get("quantity", ""),
            "comment": ctx["form_data"].get("comment", ""),
        })
        await send_request_to_admin(request_id)
        ctx["pending_form"] = None
        ctx["mode"] = None
        ctx["form_data"] = {}
        await message.answer(t(lang, "log_created"), reply_markup=logistics_menu(lang))
        return

    # =========================
    # fallback
    # =========================
    if ctx.get("section") == "legal":
        await message.answer(t(lang, "legal_intro"), reply_markup=legal_menu_kb(lang))
        return
    if ctx.get("section") == "broker":
        await message.answer(
            t(lang, "broker_intro") + "\n\n"
            + t(lang, "broker_price_1") + "\n"
            + t(lang, "broker_price_2") + "\n"
            + t(lang, "broker_price_3") + "\n"
            + t(lang, "broker_price_4") + "\n"
            + t(lang, "broker_price_5"),
            reply_markup=broker_menu(lang)
        )
        return
    if ctx.get("section") == "logistics":
        await message.answer(t(lang, "log_intro"), reply_markup=logistics_menu(lang))
        return

    await send_main_menu(message, uid)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
