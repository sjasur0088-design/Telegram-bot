import os
import re
import json
import html
import glob
import logging
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")
ANALYTICS_DB_PATH = os.getenv("ANALYTICS_DB_PATH", "analytics.db")
OPENAI_MAX_OUTPUT_TOKENS = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "900"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)
client = OpenAI(api_key=OPENAI_API_KEY) if (OPENAI_API_KEY and OpenAI) else None

TELEGRAM_LIMIT = 3900
CONTEXTS: Dict[int, Dict[str, Any]] = {}
PRODUCT_DB: List[dict] = []

BROKER_PRICES = {
    "analysis_year": 300000,
    "analysis_3m": 600000,
    "docs_from": 300000,
    "docs_to": 500000,
    "certification": 300000,
    "tnved_analytics": 500000,
}

TXT = {
    "ru": {
        "choose_lang": "Выберите язык / Tilni tanlang:",
        "main_menu": "<b>Главное меню</b>\n\nВыберите раздел:",
        "back_main": "⬅️ Назад в главное меню",
        "back": "⬅️ Назад",
        "menu": "Меню",
        "phys": "👤 Для физ лиц",
        "legal": "🏢 Для юр лиц",
        "brokers": "📊 Для брокеров",
        "logistics": "🚚 Логистика",
        "legal_intro": (
            "<b>Для юридических лиц</b>\n\n"
            "Наши специалисты имеют 10–15 лет опыта в таможенной сфере и помогут по вопросам:\n\n"
            "• ТН ВЭД и ставок\n"
            "• импорта и экспорта\n"
            "• документов\n"
            "• сертификации\n\n"
            "Вы можете получить общую информацию сразу в боте, а точный ответ по вашему кейсу специалист даст бесплатно в течение дня."
        ),
        "legal_tnved": "1️⃣ ТН ВЭД и ставки",
        "legal_exact": "2️⃣ 🎯 Точный код и ставка",
        "legal_spec": "3️⃣ 👨‍💼 Связь со специалистом",
        "legal_ai": "4️⃣ 💬 Чат с помощником",
        "enter_product": "Введите наименование товара:",
        "exact_intro": (
            "<b>Точный код и ставка</b>\n\n"
            "Для более точного определения укажите по очереди:\n"
            "• наименование товара\n"
            "• назначение\n"
            "• материал\n"
            "• бренд/модель\n"
            "• страну происхождения\n"
            "• фото или описание, если есть"
        ),
        "enter_usage": "Укажите назначение товара:",
        "enter_material": "Укажите материал:",
        "enter_brand": "Укажите бренд / модель:",
        "enter_country": "Укажите страну происхождения:",
        "enter_desc": "Добавьте описание или напишите 'нет':",
        "spec_intro": "<b>Связь со специалистом</b>\n\nОпишите ваш вопрос, и мы передадим его специалисту.\n\nСпециалист ответит бесплатно в течение дня.",
        "enter_name": "Введите ваше имя:",
        "enter_tg": "Укажите ваш Telegram (username или номер):",
        "enter_phone": "Введите номер телефона:",
        "enter_question": "Опишите ваш вопрос:",
        "request_sent": "✅ Ваша заявка отправлена.\n\nСпециалист свяжется с вами в течение дня.",
        "ai_intro": "<b>Чат с помощником</b>\n\nВы можете задать вопрос по:\n• ТН ВЭД\n• ставкам\n• импорту/экспорту\n• документам\n• сертификации",
        "not_customs": "Я помощник только по вопросам таможни, импорта, экспорта, ТН ВЭД, документов и сертификации.",
        "ai_footer": "\n\nТочную информацию по вашему кейсу можно получить бесплатно через специалиста.",
        "quick_import_docs": "Какие документы нужны для импорта?",
        "quick_export_docs": "Какие документы нужны для экспорта?",
        "quick_certs": "Какие сертификаты нужны для импорта?",
        "quick_tnved": "Как определяется код ТН ВЭД?",
        "quick_payments": "Какие платежи при импорте?",
        "quick_ask": "Задать свой вопрос",
        "broker_intro": (
            "<b>Профессиональная поддержка для брокеров и импортеров</b>\n\n"
            "Наши эксперты имеют 10–15 лет практического опыта в таможенной сфере Узбекистана.\n\n"
            "Мы помогаем:\n"
            "• избежать переплат по таможенной стоимости\n"
            "• проверить документы до подачи\n"
            "• заранее понять требования по сертификации\n"
            "• подготовить кейс для специалиста\n\n"
            "💡 <b>Разбор кейса: Как не переплатить $1000 на ровном месте</b>\n\n"
            "Выберите услугу:"
        ),
        "broker_1": "📉 Анализ таможенной стоимости",
        "broker_2": "📄 Проверка документов перед подачей",
        "broker_3": "📑 Нюансы по сертификации",
        "broker_4": "📊 Аналитика по ТН ВЭД коду",
        "broker_prices": (
            "📉 1 год: минимальная и средняя стоимость — 300 000 сум\n"
            "📊 3 месяца: конкретная база по товару — 600 000 сум\n"
            "📄 Проверка документов — от 300 000 до 500 000 сум\n"
            "📑 Сертификация — 300 000 сум\n"
            "📈 Excel по 1 коду ТН ВЭД за год — 500 000 сум"
        ),
        "log_intro": (
            "<b>Логистика</b>\n\n"
            "Мы собираем предложения от проверенных логистов, а вы выбираете лучший вариант.\n\n"
            "Что вы получаете:\n"
            "• доставка из Китая, Кореи, Европы и СНГ\n"
            "• одна заявка → несколько предложений\n"
            "• выбор по цене и срокам\n\n"
            "Бонус:\n"
            "помощь по документам и растаможке\n\n"
            "У нас есть 10 проверенных логистов. Мы подберём для вас 3–4 лучших варианта."
        ),
        "log_request": "📝 Оставить заявку",
        "log_how": "ℹ️ Как это работает",
        "log_how_text": (
            "<b>Как это работает</b>\n\n"
            "1. Вы оставляете заявку\n"
            "2. Мы передаём её логистам\n"
            "3. Получаем предложения\n"
            "4. Отправляем вам 3–4 варианта\n\n"
            "Вы сами выбираете лучшую цену и сроки."
        ),
        "enter_from": "Откуда груз:",
        "enter_to": "Куда доставить:",
        "enter_weight": "Вес или объём груза:",
        "enter_comment": "Дополнительная информация:",
        "log_sent": "✅ Ваша заявка принята.\n\nМы подберём варианты и свяжемся с вами.",
        "phys_stub": "Раздел для физ лиц оставлен без изменений. Вы можете продолжать использовать текущую логику этого раздела.",
        "admin_panel": "Панель администратора",
        "admin_new": "🆕 Новые заявки",
        "admin_progress": "🔄 В работе",
        "admin_done": "✅ Завершённые",
        "admin_all": "📋 Все заявки",
        "stats_title": "📊 <b>Статистика бота</b>",
        "no_requests": "Заявок пока нет.",
        "unknown": "Пожалуйста, выберите пункт меню кнопками ниже.",
    },
    "uz": {
        "choose_lang": "Tilni tanlang / Выберите язык:",
        "main_menu": "<b>Asosiy menyu</b>\n\nBo'limni tanlang:",
        "back_main": "⬅️ Asosiy menyuga qaytish",
        "back": "⬅️ Orqaga",
        "menu": "Menyu",
        "phys": "👤 Jismoniy shaxslar",
        "legal": "🏢 Yuridik shaxslar",
        "brokers": "📊 Brokerlar",
        "logistics": "🚚 Logistika",
        "legal_intro": (
            "<b>Yuridik shaxslar uchun</b>\n\n"
            "Mutaxassislarimiz bojxona sohasida 10–15 yillik tajribaga ega va quyidagilar bo'yicha yordam beradi:\n\n"
            "• TN VED va stavkalar\n"
            "• import va eksport\n"
            "• hujjatlar\n"
            "• sertifikatlash\n\n"
            "Umumiy ma'lumotni botdan olishingiz mumkin, aniq javobni esa mutaxassis kun davomida bepul beradi."
        ),
        "legal_tnved": "1️⃣ TN VED va stavkalar",
        "legal_exact": "2️⃣ 🎯 Aniq kod va stavka",
        "legal_spec": "3️⃣ 👨‍💼 Mutaxassis bilan aloqa",
        "legal_ai": "4️⃣ 💬 Yordamchi bilan chat",
        "enter_product": "Tovar nomini kiriting:",
        "exact_intro": (
            "<b>Aniq kod va stavka</b>\n\n"
            "Aniqroq aniqlash uchun ketma-ket quyidagilarni kiriting:\n"
            "• tovar nomi\n• maqsadi\n• materiali\n• brend/model\n• kelib chiqish davlati\n• foto yoki tavsif"
        ),
        "enter_usage": "Tovar maqsadini kiriting:",
        "enter_material": "Materialni kiriting:",
        "enter_brand": "Brend / modelni kiriting:",
        "enter_country": "Kelib chiqish davlatini kiriting:",
        "enter_desc": "Tavsif kiriting yoki 'yoq' deb yozing:",
        "spec_intro": "<b>Mutaxassis bilan aloqa</b>\n\nSavolingizni yozing, biz mutaxassisga yuboramiz.\n\nMutaxassis kun davomida bepul javob beradi.",
        "enter_name": "Ismingizni kiriting:",
        "enter_tg": "Telegram username yoki raqamni kiriting:",
        "enter_phone": "Telefon raqamingizni kiriting:",
        "enter_question": "Savolingizni yozing:",
        "request_sent": "✅ Arizangiz yuborildi.\n\nMutaxassis siz bilan kun davomida bog'lanadi.",
        "ai_intro": "<b>Yordamchi bilan chat</b>\n\nQuyidagilar bo'yicha savol berishingiz mumkin:\n• TN VED\n• stavkalar\n• import/eksport\n• hujjatlar\n• sertifikatlash",
        "not_customs": "Men faqat bojxona, import, eksport, TN VED, hujjatlar va sertifikatlash bo'yicha yordam beraman.",
        "ai_footer": "\n\nAniq javobni mutaxassis orqali bepul olishingiz mumkin.",
        "quick_import_docs": "Import uchun qaysi hujjatlar kerak?",
        "quick_export_docs": "Eksport uchun qaysi hujjatlar kerak?",
        "quick_certs": "Import uchun qaysi sertifikatlar kerak?",
        "quick_tnved": "TN VED kodi qanday aniqlanadi?",
        "quick_payments": "Importda qaysi to'lovlar bor?",
        "quick_ask": "O'z savolimni berish",
        "broker_intro": (
            "<b>Brokerlar va importerlar uchun professional yordam</b>\n\n"
            "Mutaxassislarimiz O'zbekiston bojxona sohasida 10–15 yillik tajribaga ega.\n\n"
            "Biz yordam beramiz:\n"
            "• bojxona qiymati bo'yicha ortiqcha to'lovlardan qochish\n"
            "• topshirishdan oldin hujjatlarni tekshirish\n"
            "• sertifikatlash talablarini tushunish\n"
            "• кейсni mutaxassis uchun tayyorlash\n\n"
            "💡 <b>Case: Qanday qilib $1000 ortiqcha to'lamaslik</b>\n\n"
            "Xizmatni tanlang:"
        ),
        "broker_1": "📉 Bojxona qiymati tahlili",
        "broker_2": "📄 Hujjatlarni tekshirish",
        "broker_3": "📑 Sertifikatlash нюанслари",
        "broker_4": "📊 TN VED kodi bo'yicha analitika",
        "broker_prices": (
            "📉 1 yil: minimal va o'rtacha qiymat — 300 000 so'm\n"
            "📊 3 oy: tovar bo'yicha aniq baza — 600 000 so'm\n"
            "📄 Hujjatlarni tekshirish — 300 000 dan 500 000 so'mgacha\n"
            "📑 Sertifikatlash — 300 000 so'm\n"
            "📈 1 ta TN VED kodi bo'yicha Excel — 500 000 so'm"
        ),
        "log_intro": (
            "<b>Logistika</b>\n\n"
            "Biz ishonchli logistlardan takliflarni yig'amiz, siz esa eng yaxshi variantni tanlaysiz.\n\n"
            "Nima olasiz:\n"
            "• Xitoy, Koreya, Yevropa va MDH dan yetkazib berish\n"
            "• bitta ariza → bir nechta taklif\n"
            "• narx va muddat bo'yicha tanlov\n\n"
            "Bonus:\n"
            "hujjatlar va bojxona rasmiylashtiruvi bo'yicha yordam\n\n"
            "Bizda 10 ta tekshirilgan logist bor. Siz uchun 3–4 ta eng yaxshi variantni tanlaymiz."
        ),
        "log_request": "📝 Ariza qoldirish",
        "log_how": "ℹ️ Qanday ishlaydi",
        "log_how_text": (
            "<b>Qanday ishlaydi</b>\n\n"
            "1. Siz ariza qoldirasiz\n"
            "2. Biz uni logistlarga yuboramiz\n"
            "3. Takliflarni olamiz\n"
            "4. Sizga 3–4 variant yuboramiz\n\n"
            "Siz narx va muddat bo'yicha eng yaxshi variantni tanlaysiz."
        ),
        "enter_from": "Yuk qayerdan:",
        "enter_to": "Qayerga yetkazish kerak:",
        "enter_weight": "Yuk vazni yoki hajmi:",
        "enter_comment": "Qo'shimcha ma'lumot:",
        "log_sent": "✅ Arizangiz qabul qilindi.\n\nVariantlarni tayyorlab siz bilan bog'lanamiz.",
        "phys_stub": "Jismoniy shaxslar bo'limi o'zgartirilmagan. Joriy logikani ishlatishda davom etishingiz mumkin.",
        "admin_panel": "Administrator paneli",
        "admin_new": "🆕 Yangi arizalar",
        "admin_progress": "🔄 Jarayonda",
        "admin_done": "✅ Yakunlangan",
        "admin_all": "📋 Barcha arizalar",
        "stats_title": "📊 <b>Bot statistikasi</b>",
        "no_requests": "Hozircha arizalar yo'q.",
        "unknown": "Iltimos, pastdagi tugmalar orqali bo'limni tanlang.",
    }
}


# ---------------- Utilities ----------------

def t(lang: str, key: str) -> str:
    lang = lang if lang in TXT else "ru"
    return TXT[lang].get(key, TXT["ru"].get(key, key))


def get_ctx(uid: int) -> Dict[str, Any]:
    if uid not in CONTEXTS:
        CONTEXTS[uid] = {
            "lang": None,
            "section": None,
            "mode": None,
            "pending_form": None,
            "form_data": {},
        }
    return CONTEXTS[uid]


def format_sum(value: int) -> str:
    return f"{value:,}".replace(",", " ") + " сум"


def split_text(text: str, limit: int = TELEGRAM_LIMIT) -> List[str]:
    text = text.strip()
    if len(text) <= limit:
        return [text]
    parts = []
    current = ""
    for paragraph in text.split("\n"):
        if len(current) + len(paragraph) + 1 <= limit:
            current += ("\n" if current else "") + paragraph
        else:
            if current:
                parts.append(current)
            while len(paragraph) > limit:
                parts.append(paragraph[:limit])
                paragraph = paragraph[limit:]
            current = paragraph
    if current:
        parts.append(current)
    return parts


async def safe_answer(message: types.Message, text: str, reply_markup=None):
    for idx, chunk in enumerate(split_text(text)):
        await message.answer(chunk, reply_markup=reply_markup if idx == len(split_text(text)) - 1 else None)


def ensure_dir_for_file(path: str):
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def db_conn() -> sqlite3.Connection:
    ensure_dir_for_file(ANALYTICS_DB_PATH)
    conn = sqlite3.connect(ANALYTICS_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            lang TEXT,
            section TEXT,
            event_type TEXT,
            event_value TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            full_name TEXT,
            lang TEXT,
            request_type TEXT,
            service_type TEXT,
            service_label TEXT,
            price_text TEXT,
            tg_contact TEXT,
            phone TEXT,
            question TEXT,
            product TEXT,
            brand TEXT,
            country TEXT,
            quantity TEXT,
            tnved_code TEXT,
            comment TEXT,
            from_city TEXT,
            to_city TEXT,
            weight_volume TEXT,
            status TEXT DEFAULT 'new',
            assigned_to INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    conn.commit()
    return conn


def track(uid: int, username: str, lang: str, section: str, event_type: str, event_value: str):
    try:
        conn = db_conn()
        conn.execute(
            "INSERT INTO events (user_id, username, lang, section, event_type, event_value, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (uid, username or "", lang or "ru", section or "", event_type, event_value[:1000], datetime.utcnow().isoformat()),
        )
        conn.commit()
        conn.close()
    except Exception:
        logging.exception("track failed")


def create_request(data: Dict[str, Any]) -> int:
    conn = db_conn()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute(
        """
        INSERT INTO requests (
            user_id, username, full_name, lang, request_type, service_type, service_label, price_text,
            tg_contact, phone, question, product, brand, country, quantity, tnved_code, comment,
            from_city, to_city, weight_volume, status, assigned_to, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', NULL, ?, ?)
        """,
        (
            data.get("user_id"),
            data.get("username", ""),
            data.get("full_name", ""),
            data.get("lang", "ru"),
            data.get("request_type", ""),
            data.get("service_type", ""),
            data.get("service_label", ""),
            data.get("price_text", ""),
            data.get("tg_contact", ""),
            data.get("phone", ""),
            data.get("question", ""),
            data.get("product", ""),
            data.get("brand", ""),
            data.get("country", ""),
            data.get("quantity", ""),
            data.get("tnved_code", ""),
            data.get("comment", ""),
            data.get("from_city", ""),
            data.get("to_city", ""),
            data.get("weight_volume", ""),
            now,
            now,
        ),
    )
    req_id = cur.lastrowid
    conn.commit()
    conn.close()
    return req_id


def get_request(req_id: int):
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM requests WHERE id = ?", (req_id,))
    row = cur.fetchone()
    conn.close()
    return row


def list_requests(status: Optional[str] = None, limit: int = 20):
    conn = db_conn()
    cur = conn.cursor()
    if status:
        cur.execute("SELECT * FROM requests WHERE status = ? ORDER BY id DESC LIMIT ?", (status, limit))
    else:
        cur.execute("SELECT * FROM requests ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows


def update_request_status(req_id: int, status: str, assigned_to: Optional[int] = None):
    conn = db_conn()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    if assigned_to is None:
        cur.execute("UPDATE requests SET status = ?, updated_at = ? WHERE id = ?", (status, now, req_id))
    else:
        cur.execute(
            "UPDATE requests SET status = ?, assigned_to = ?, updated_at = ? WHERE id = ?",
            (status, assigned_to, now, req_id),
        )
    conn.commit()
    conn.close()


def request_card(row: sqlite3.Row) -> str:
    lines = [
        f"📥 <b>Заявка #{row['id']}</b>",
        "",
        f"<b>Тип:</b> {html.escape(row['request_type'] or '-')}",
    ]
    if row["service_label"]:
        lines.append(f"<b>Услуга:</b> {html.escape(row['service_label'])}")
    if row["price_text"]:
        lines.append(f"<b>Цена:</b> {html.escape(row['price_text'])}")
    lines += [
        f"<b>Статус:</b> {html.escape((row['status'] or '').upper())}",
        "",
        f"<b>Имя:</b> {html.escape(row['full_name'] or '-')}",
        f"<b>Telegram:</b> {html.escape(row['tg_contact'] or ('@' + row['username'] if row['username'] else '-'))}",
        f"<b>Телефон:</b> {html.escape(row['phone'] or '-')}",
        f"<b>ID:</b> <code>{row['user_id']}</code>",
    ]
    extras = {
        "Вопрос": row["question"],
        "Товар": row["product"],
        "Бренд": row["brand"],
        "Страна": row["country"],
        "Количество": row["quantity"],
        "Код ТН ВЭД": row["tnved_code"],
        "Откуда": row["from_city"],
        "Куда": row["to_city"],
        "Вес/объём": row["weight_volume"],
        "Комментарий": row["comment"],
    }
    for label, value in extras.items():
        if value:
            lines.append(f"<b>{label}:</b> {html.escape(str(value))}")
    lines += ["", f"<b>Создано:</b> {row['created_at']}"]
    return "\n".join(lines)


def request_inline_kb(req_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🟢 Взять в работу", callback_data=f"req_take:{req_id}"),
        InlineKeyboardButton("✅ Закрыть", callback_data=f"req_done:{req_id}"),
    )
    kb.add(InlineKeyboardButton("📞 Контакт", callback_data=f"req_contact:{req_id}"))
    return kb


async def send_request_to_admin(req_id: int):
    if not ADMIN_CHAT_ID:
        return
    try:
        await bot.send_message(int(ADMIN_CHAT_ID), request_card(get_request(req_id)), reply_markup=request_inline_kb(req_id))
    except Exception:
        logging.exception("send_request_to_admin failed")


def is_admin(uid: int) -> bool:
    try:
        return bool(ADMIN_CHAT_ID) and int(uid) == int(ADMIN_CHAT_ID)
    except Exception:
        return False


# ---------------- Keyboards ----------------

def lang_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🇷🇺 Русский", "🇺🇿 O‘zbekcha")
    return kb


def main_menu(lang: str) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "phys"), t(lang, "legal"))
    kb.add(t(lang, "brokers"), t(lang, "logistics"))
    return kb


def legal_menu(lang: str) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "legal_tnved"))
    kb.add(t(lang, "legal_exact"))
    kb.add(t(lang, "legal_spec"))
    kb.add(t(lang, "legal_ai"))
    kb.add(t(lang, "back_main"))
    return kb


def ai_quick_kb(lang: str) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "quick_import_docs"))
    kb.add(t(lang, "quick_export_docs"))
    kb.add(t(lang, "quick_certs"))
    kb.add(t(lang, "quick_tnved"))
    kb.add(t(lang, "quick_payments"))
    kb.add(t(lang, "quick_ask"))
    kb.add(t(lang, "legal_spec"), t(lang, "back_main"))
    return kb


def broker_menu(lang: str) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "broker_1"))
    kb.add(t(lang, "broker_2"))
    kb.add(t(lang, "broker_3"))
    kb.add(t(lang, "broker_4"))
    kb.add(t(lang, "back_main"))
    return kb


def log_menu(lang: str) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "log_request"))
    kb.add(t(lang, "log_how"))
    kb.add(t(lang, "back_main"))
    return kb


def admin_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🆕 Новые заявки", "🔄 В работе")
    kb.add("✅ Завершённые", "📋 Все заявки")
    kb.add("⬅️ Назад в главное меню")
    return kb


# ---------------- Product DB ----------------

def load_product_db():
    global PRODUCT_DB
    records: List[dict] = []
    for path in sorted(glob.glob("product_db_part*.json")):
        try:
            logging.info("Загрузка файла базы данных: %s", os.path.abspath(path))
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    records.extend([x for x in data if isinstance(x, dict)])
        except Exception:
            logging.exception("Не удалось загрузить %s", path)
    PRODUCT_DB = records
    logging.info("Загружено записей: %s", len(PRODUCT_DB))


def extract_code_name_rate(item: dict) -> Tuple[str, str, str]:
    code = str(item.get("code") or item.get("tnved") or item.get("hs_code") or item.get("Код") or "").strip()
    name = str(item.get("name") or item.get("description") or item.get("Наименование") or item.get("title") or "").strip()
    rate = str(item.get("rate") or item.get("duty") or item.get("stavka") or item.get("Ставка") or "").strip()
    return code, name, rate


def search_tnved(query: str, limit: int = 7) -> List[dict]:
    q = query.lower().strip()
    if not q or not PRODUCT_DB:
        return []
    scored = []
    words = [w for w in re.split(r"\s+", q) if w]
    for item in PRODUCT_DB:
        code, name, rate = extract_code_name_rate(item)
        hay = f"{code} {name} {rate} {json.dumps(item, ensure_ascii=False)}".lower()
        score = 0
        for w in words:
            if w in hay:
                score += 3 if w in name.lower() else 1
        if q in hay:
            score += 5
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:limit]]


def format_tnved_results(results: List[dict], title: str = "Результаты поиска") -> str:
    if not results:
        return "Ничего подходящего по базе не найдено. Попробуйте уточнить наименование товара или обратиться к специалисту."
    lines = [f"<b>{title}</b>"]
    for idx, item in enumerate(results, 1):
        code, name, rate = extract_code_name_rate(item)
        lines.append(f"\n<b>{idx}.</b> <code>{html.escape(code or '-')}</code>")
        if name:
            lines.append(html.escape(name))
        if rate:
            lines.append(f"<b>Ставка:</b> {html.escape(rate)}")
    return "\n".join(lines)


# ---------------- AI ----------------

def is_customs_question(text: str) -> bool:
    keywords = [
        "тн вэд", "tn ved", "hs", "ставк", "пошлин", "ндс", "акциз", "импорт", "экспорт",
        "тамож", "сертифик", "документ", "декларац", "код товара", "оформлен", "растамож",
        "imei", "утиль", "инвойс", "упаковоч", "контракт", "сэс", "узстандарт",
    ]
    lower = text.lower()
    return any(k in lower for k in keywords)


def ask_ai(system_prompt: str, user_text: str) -> Optional[str]:
    if not client:
        return None
    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=f"{system_prompt}\n\nВопрос пользователя: {user_text}",
            max_output_tokens=OPENAI_MAX_OUTPUT_TOKENS,
        )
        text_parts = []
        for out in getattr(response, "output", []) or []:
            for c in getattr(out, "content", []) or []:
                txt = getattr(c, "text", None)
                if txt:
                    text_parts.append(txt)
        return "\n".join(text_parts).strip() or None
    except Exception:
        logging.exception("ask_ai failed")
        return None


CUSTOMS_ASSISTANT_PROMPT = (
    "Ты помощник только по вопросам таможни, импорта, экспорта, ТН ВЭД, ставок, документов, "
    "сертификации и таможенного оформления в Узбекистане. "
    "Если вопрос не относится к этим темам, ответь, что ты работаешь только по таможенной теме. "
    "Отвечай кратко, структурированно и без ухода в другие темы."
)

EXACT_CODE_PROMPT = (
    "Ты эксперт по ТН ВЭД Узбекистана. На основе описания товара предложи наиболее вероятные коды и логику выбора. "
    "Не выдумывай точные ставки, если их нет в базе. Если данных недостаточно, прямо укажи это и предложи обратиться к специалисту."
)


# ---------------- Menus / navigation ----------------
async def show_main_menu(message: types.Message, uid: int):
    ctx = get_ctx(uid)
    lang = ctx.get("lang") or "ru"
    ctx["section"] = None
    ctx["mode"] = None
    ctx["pending_form"] = None
    ctx["form_data"] = {}
    await message.answer(t(lang, "main_menu"), reply_markup=main_menu(lang))


async def show_legal_menu(message: types.Message, uid: int):
    ctx = get_ctx(uid)
    lang = ctx.get("lang") or "ru"
    ctx["section"] = "legal"
    ctx["mode"] = None
    ctx["pending_form"] = None
    ctx["form_data"] = {}
    await safe_answer(message, t(lang, "legal_intro"), reply_markup=legal_menu(lang))


async def show_broker_menu(message: types.Message, uid: int):
    ctx = get_ctx(uid)
    lang = ctx.get("lang") or "ru"
    ctx["section"] = "broker"
    ctx["mode"] = None
    ctx["pending_form"] = None
    ctx["form_data"] = {}
    text = t(lang, "broker_intro") + "\n\n" + t(lang, "broker_prices")
    await safe_answer(message, text, reply_markup=broker_menu(lang))


async def show_logistics_menu(message: types.Message, uid: int):
    ctx = get_ctx(uid)
    lang = ctx.get("lang") or "ru"
    ctx["section"] = "logistics"
    ctx["mode"] = None
    ctx["pending_form"] = None
    ctx["form_data"] = {}
    await safe_answer(message, t(lang, "log_intro"), reply_markup=log_menu(lang))


# ---------------- Stats ----------------
def stats_text() -> str:
    conn = db_conn()
    cur = conn.cursor()
    def scalar(q, params=()):
        cur.execute(q, params)
        row = cur.fetchone()
        return row[0] if row else 0
    total = scalar("SELECT COUNT(*) FROM requests")
    new = scalar("SELECT COUNT(*) FROM requests WHERE status='new'")
    progress = scalar("SELECT COUNT(*) FROM requests WHERE status='in_progress'")
    done = scalar("SELECT COUNT(*) FROM requests WHERE status='done'")
    broker = scalar("SELECT COUNT(*) FROM requests WHERE request_type='broker'")
    logistics = scalar("SELECT COUNT(*) FROM requests WHERE request_type='logistics'")
    specialist = scalar("SELECT COUNT(*) FROM requests WHERE request_type='specialist'")
    cur.execute("SELECT service_label, COUNT(*) cnt FROM requests WHERE service_label != '' GROUP BY service_label ORDER BY cnt DESC LIMIT 10")
    services = cur.fetchall()
    conn.close()

    lines = [
        "📊 <b>Статистика бота</b>",
        "",
        f"Всего заявок: {total}",
        f"Новые: {new}",
        f"В работе: {progress}",
        f"Завершённые: {done}",
        "",
        "<b>По типам:</b>",
        f"Брокеры: {broker}",
        f"Логистика: {logistics}",
        f"Специалист: {specialist}",
    ]
    if services:
        lines += ["", "<b>По услугам:</b>"]
        for row in services:
            lines.append(f"{html.escape(row['service_label'])}: {row['cnt']}")
    return "\n".join(lines)


# ---------------- Handlers ----------------
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    uid = message.from_user.id
    ctx = get_ctx(uid)
    ctx["lang"] = None
    ctx["section"] = None
    ctx["mode"] = None
    ctx["pending_form"] = None
    ctx["form_data"] = {}
    await message.answer(TXT["ru"]["choose_lang"], reply_markup=lang_kb())


@dp.message_handler(commands=["admin"])
async def cmd_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Панель администратора", reply_markup=admin_kb())


@dp.message_handler(commands=["stats"])
async def cmd_stats(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await safe_answer(message, stats_text(), reply_markup=admin_kb())


@dp.callback_query_handler(lambda c: c.data and c.data.startswith("req_"))
async def request_admin_actions(callback_query: types.CallbackQuery):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("Нет доступа", show_alert=True)
        return
    await callback_query.answer()
    data = callback_query.data
    try:
        action, req_id = data.split(":")
        req_id = int(req_id)
    except Exception:
        return
    row = get_request(req_id)
    if not row:
        await callback_query.message.answer("Заявка не найдена")
        return
    if action == "req_take":
        update_request_status(req_id, "in_progress", callback_query.from_user.id)
        try:
            await bot.send_message(row["user_id"], f"Ваша заявка №{req_id} принята в работу. С вами скоро свяжется специалист.")
        except Exception:
            pass
        await callback_query.message.edit_text(request_card(get_request(req_id)), reply_markup=request_inline_kb(req_id))
        return
    if action == "req_done":
        update_request_status(req_id, "done")
        try:
            await bot.send_message(row["user_id"], f"Ваша заявка №{req_id} обработана. Спасибо!")
        except Exception:
            pass
        await callback_query.message.edit_text(request_card(get_request(req_id)), reply_markup=request_inline_kb(req_id))
        return
    if action == "req_contact":
        contact = (
            f"<b>Контакт клиента</b>\n\n"
            f"Имя: {html.escape(row['full_name'] or '-')}\n"
            f"Telegram: {html.escape(row['tg_contact'] or ('@' + row['username'] if row['username'] else '-'))}\n"
            f"Телефон: {html.escape(row['phone'] or '-')}\n"
            f"ID: <code>{row['user_id']}</code>"
        )
        await callback_query.message.answer(contact)


@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def router(message: types.Message):
    uid = message.from_user.id
    username = message.from_user.username or ""
    text = (message.text or "").strip()
    ctx = get_ctx(uid)
    lang = ctx.get("lang") or "ru"

    # language selection
    if text == "🇷🇺 Русский":
        ctx["lang"] = "ru"
        await show_main_menu(message, uid)
        return
    if text == "🇺🇿 O‘zbekcha":
        ctx["lang"] = "uz"
        await show_main_menu(message, uid)
        return

    if not ctx.get("lang"):
        await message.answer(TXT["ru"]["choose_lang"], reply_markup=lang_kb())
        return

    # universal back/menu
    if text in {t(lang, "back_main"), t(lang, "menu"), "Меню", "Menyu", "⬅️ Назад в главное меню", "⬅️ Asosiy menyuga qaytish"}:
        await show_main_menu(message, uid)
        return

    # admin quick views
    if is_admin(uid):
        if text == "🆕 Новые заявки":
            rows = list_requests("new")
            if not rows:
                await message.answer(t(lang, "no_requests"), reply_markup=admin_kb())
            else:
                for row in rows:
                    await safe_answer(message, request_card(row), reply_markup=request_inline_kb(row["id"]))
            return
        if text == "🔄 В работе":
            rows = list_requests("in_progress")
            if not rows:
                await message.answer(t(lang, "no_requests"), reply_markup=admin_kb())
            else:
                for row in rows:
                    await safe_answer(message, request_card(row), reply_markup=request_inline_kb(row["id"]))
            return
        if text == "✅ Завершённые":
            rows = list_requests("done")
            if not rows:
                await message.answer(t(lang, "no_requests"), reply_markup=admin_kb())
            else:
                for row in rows:
                    await safe_answer(message, request_card(row), reply_markup=request_inline_kb(row["id"]))
            return
        if text == "📋 Все заявки":
            rows = list_requests(None)
            if not rows:
                await message.answer(t(lang, "no_requests"), reply_markup=admin_kb())
            else:
                for row in rows:
                    await safe_answer(message, request_card(row), reply_markup=request_inline_kb(row["id"]))
            return

    # pending forms
    pf = ctx.get("pending_form")
    if pf == "legal_spec_name":
        ctx["form_data"]["full_name"] = text
        ctx["pending_form"] = "legal_spec_tg"
        await message.answer(t(lang, "enter_tg"), reply_markup=legal_menu(lang))
        return
    if pf == "legal_spec_tg":
        ctx["form_data"]["tg_contact"] = text
        ctx["pending_form"] = "legal_spec_phone"
        await message.answer(t(lang, "enter_phone"), reply_markup=legal_menu(lang))
        return
    if pf == "legal_spec_phone":
        ctx["form_data"]["phone"] = text
        ctx["pending_form"] = "legal_spec_question"
        await message.answer(t(lang, "enter_question"), reply_markup=legal_menu(lang))
        return
    if pf == "legal_spec_question":
        ctx["form_data"]["question"] = text
        req_id = create_request({
            "user_id": uid,
            "username": username,
            "full_name": ctx["form_data"].get("full_name", ""),
            "lang": lang,
            "request_type": "specialist",
            "service_type": "specialist_question",
            "service_label": "Связь со специалистом" if lang == "ru" else "Mutaxassis bilan aloqa",
            "tg_contact": ctx["form_data"].get("tg_contact", ""),
            "phone": ctx["form_data"].get("phone", ""),
            "question": ctx["form_data"].get("question", ""),
        })
        await send_request_to_admin(req_id)
        track(uid, username, lang, "legal", "specialist_request", text)
        ctx["pending_form"] = None
        ctx["form_data"] = {}
        await message.answer(t(lang, "request_sent"), reply_markup=legal_menu(lang))
        return

    if pf == "exact_name":
        ctx["form_data"]["product"] = text
        ctx["pending_form"] = "exact_usage"
        await message.answer(t(lang, "enter_usage"), reply_markup=legal_menu(lang))
        return
    if pf == "exact_usage":
        ctx["form_data"]["usage"] = text
        ctx["pending_form"] = "exact_material"
        await message.answer(t(lang, "enter_material"), reply_markup=legal_menu(lang))
        return
    if pf == "exact_material":
        ctx["form_data"]["material"] = text
        ctx["pending_form"] = "exact_brand"
        await message.answer(t(lang, "enter_brand"), reply_markup=legal_menu(lang))
        return
    if pf == "exact_brand":
        ctx["form_data"]["brand"] = text
        ctx["pending_form"] = "exact_country"
        await message.answer(t(lang, "enter_country"), reply_markup=legal_menu(lang))
        return
    if pf == "exact_country":
        ctx["form_data"]["country"] = text
        ctx["pending_form"] = "exact_desc"
        await message.answer(t(lang, "enter_desc"), reply_markup=legal_menu(lang))
        return
    if pf == "exact_desc":
        ctx["form_data"]["desc"] = "" if text.lower() in {"нет", "yoq", "yo'q", "no"} else text
        query = " ".join([ctx["form_data"].get(k, "") for k in ["product", "usage", "material", "brand", "country", "desc"]]).strip()
        results = search_tnved(query, 5)
        base_text = format_tnved_results(results, "Наиболее вероятные варианты")
        ai_text = ask_ai(EXACT_CODE_PROMPT, query)
        answer = base_text
        if ai_text:
            answer += "\n\n<b>AI-комментарий:</b>\n" + html.escape(ai_text)
        answer += "\n\nДля окончательного подтверждения вы можете отправить вопрос специалисту бесплатно."
        ctx["pending_form"] = None
        ctx["form_data"] = {}
        await safe_answer(message, answer, reply_markup=legal_menu(lang))
        return

    if pf == "broker_name":
        ctx["form_data"]["full_name"] = text
        ctx["pending_form"] = "broker_tg"
        await message.answer(t(lang, "enter_tg"), reply_markup=broker_menu(lang))
        return
    if pf == "broker_tg":
        ctx["form_data"]["tg_contact"] = text
        ctx["pending_form"] = "broker_phone"
        await message.answer(t(lang, "enter_phone"), reply_markup=broker_menu(lang))
        return
    if pf == "broker_phone":
        ctx["form_data"]["phone"] = text
        ctx["pending_form"] = "broker_product"
        await message.answer(t(lang, "enter_product"), reply_markup=broker_menu(lang))
        return
    if pf == "broker_product":
        ctx["form_data"]["product"] = text
        ctx["pending_form"] = "broker_brand"
        await message.answer(t(lang, "enter_brand"), reply_markup=broker_menu(lang))
        return
    if pf == "broker_brand":
        ctx["form_data"]["brand"] = text
        ctx["pending_form"] = "broker_country"
        await message.answer(t(lang, "enter_country"), reply_markup=broker_menu(lang))
        return
    if pf == "broker_country":
        ctx["form_data"]["country"] = text
        ctx["pending_form"] = "broker_quantity"
        await message.answer(t(lang, "enter_weight"), reply_markup=broker_menu(lang))
        return
    if pf == "broker_quantity":
        ctx["form_data"]["quantity"] = text
        ctx["pending_form"] = "broker_tnved"
        await message.answer("Введите код ТН ВЭД, если есть. Если нет — напишите: нет", reply_markup=broker_menu(lang))
        return
    if pf == "broker_tnved":
        ctx["form_data"]["tnved_code"] = "" if text.lower() in {"нет", "yoq", "yo'q", "no"} else text
        ctx["pending_form"] = "broker_comment"
        await message.answer(t(lang, "enter_comment"), reply_markup=broker_menu(lang))
        return
    if pf == "broker_comment":
        ctx["form_data"]["comment"] = text
        req_id = create_request({
            "user_id": uid,
            "username": username,
            "full_name": ctx["form_data"].get("full_name", ""),
            "lang": lang,
            "request_type": "broker",
            "service_type": ctx["form_data"].get("service_type", ""),
            "service_label": ctx["form_data"].get("service_label", ""),
            "price_text": ctx["form_data"].get("price_text", ""),
            "tg_contact": ctx["form_data"].get("tg_contact", ""),
            "phone": ctx["form_data"].get("phone", ""),
            "product": ctx["form_data"].get("product", ""),
            "brand": ctx["form_data"].get("brand", ""),
            "country": ctx["form_data"].get("country", ""),
            "quantity": ctx["form_data"].get("quantity", ""),
            "tnved_code": ctx["form_data"].get("tnved_code", ""),
            "comment": ctx["form_data"].get("comment", ""),
        })
        await send_request_to_admin(req_id)
        track(uid, username, lang, "broker", "request", ctx["form_data"].get("service_type", ""))
        ctx["pending_form"] = None
        ctx["form_data"] = {}
        await message.answer(f"✅ Ваша заявка №{req_id} создана.\n\nСпециалист получит её и свяжется с вами.", reply_markup=broker_menu(lang))
        return

    if pf == "log_name":
        ctx["form_data"]["full_name"] = text
        ctx["pending_form"] = "log_tg"
        await message.answer(t(lang, "enter_tg"), reply_markup=log_menu(lang))
        return
    if pf == "log_tg":
        ctx["form_data"]["tg_contact"] = text
        ctx["pending_form"] = "log_phone"
        await message.answer(t(lang, "enter_phone"), reply_markup=log_menu(lang))
        return
    if pf == "log_phone":
        ctx["form_data"]["phone"] = text
        ctx["pending_form"] = "log_from"
        await message.answer(t(lang, "enter_from"), reply_markup=log_menu(lang))
        return
    if pf == "log_from":
        ctx["form_data"]["from_city"] = text
        ctx["pending_form"] = "log_to"
        await message.answer(t(lang, "enter_to"), reply_markup=log_menu(lang))
        return
    if pf == "log_to":
        ctx["form_data"]["to_city"] = text
        ctx["pending_form"] = "log_product"
        await message.answer(t(lang, "enter_product"), reply_markup=log_menu(lang))
        return
    if pf == "log_product":
        ctx["form_data"]["product"] = text
        ctx["pending_form"] = "log_weight"
        await message.answer(t(lang, "enter_weight"), reply_markup=log_menu(lang))
        return
    if pf == "log_weight":
        ctx["form_data"]["weight_volume"] = text
        ctx["pending_form"] = "log_comment"
        await message.answer(t(lang, "enter_comment"), reply_markup=log_menu(lang))
        return
    if pf == "log_comment":
        ctx["form_data"]["comment"] = text
        req_id = create_request({
            "user_id": uid,
            "username": username,
            "full_name": ctx["form_data"].get("full_name", ""),
            "lang": lang,
            "request_type": "logistics",
            "service_type": "logistics_request",
            "service_label": "Логистика" if lang == "ru" else "Logistika",
            "tg_contact": ctx["form_data"].get("tg_contact", ""),
            "phone": ctx["form_data"].get("phone", ""),
            "from_city": ctx["form_data"].get("from_city", ""),
            "to_city": ctx["form_data"].get("to_city", ""),
            "product": ctx["form_data"].get("product", ""),
            "weight_volume": ctx["form_data"].get("weight_volume", ""),
            "comment": ctx["form_data"].get("comment", ""),
        })
        await send_request_to_admin(req_id)
        track(uid, username, lang, "logistics", "request", ctx["form_data"].get("product", ""))
        ctx["pending_form"] = None
        ctx["form_data"] = {}
        await message.answer(t(lang, "log_sent"), reply_markup=log_menu(lang))
        return

    # main sections
    if text == t(lang, "phys"):
        ctx["section"] = "phys"
        track(uid, username, lang, "phys", "open_section", "phys")
        await message.answer(t(lang, "phys_stub"), reply_markup=main_menu(lang))
        return

    if text == t(lang, "legal"):
        track(uid, username, lang, "legal", "open_section", "legal")
        await show_legal_menu(message, uid)
        return

    if text == t(lang, "brokers"):
        track(uid, username, lang, "broker", "open_section", "broker")
        await show_broker_menu(message, uid)
        return

    if text == t(lang, "logistics"):
        track(uid, username, lang, "logistics", "open_section", "logistics")
        await show_logistics_menu(message, uid)
        return

    # legal section
    if text == t(lang, "legal_tnved"):
        ctx["section"] = "legal"
        ctx["mode"] = "legal_tnved"
        await message.answer(t(lang, "enter_product"), reply_markup=legal_menu(lang))
        return

    if text == t(lang, "legal_exact"):
        ctx["section"] = "legal"
        ctx["mode"] = None
        ctx["pending_form"] = "exact_name"
        ctx["form_data"] = {}
        await safe_answer(message, t(lang, "exact_intro"), reply_markup=legal_menu(lang))
        await message.answer(t(lang, "enter_product"), reply_markup=legal_menu(lang))
        return

    if text == t(lang, "legal_spec"):
        ctx["section"] = "legal"
        ctx["mode"] = None
        ctx["pending_form"] = "legal_spec_name"
        ctx["form_data"] = {}
        await safe_answer(message, t(lang, "spec_intro"), reply_markup=legal_menu(lang))
        await message.answer(t(lang, "enter_name"), reply_markup=legal_menu(lang))
        return

    if text == t(lang, "legal_ai"):
        ctx["section"] = "legal"
        ctx["mode"] = "legal_ai"
        await safe_answer(message, t(lang, "ai_intro"), reply_markup=ai_quick_kb(lang))
        return

    # broker menu
    if text == t(lang, "broker_1"):
        ctx["section"] = "broker"
        ctx["pending_form"] = "broker_name"
        ctx["form_data"] = {
            "service_type": "analysis_year",
            "service_label": "Анализ таможенной стоимости" if lang == "ru" else "Bojxona qiymati tahlili",
            "price_text": format_sum(BROKER_PRICES["analysis_year"]),
        }
        await message.answer(f"{ctx['form_data']['service_label']}\n💰 {ctx['form_data']['price_text']}\n\n{t(lang, 'enter_name')}", reply_markup=broker_menu(lang))
        return
    if text == t(lang, "broker_2"):
        ctx["section"] = "broker"
        ctx["pending_form"] = "broker_name"
        ctx["form_data"] = {
            "service_type": "docs_check",
            "service_label": "Проверка документов перед подачей" if lang == "ru" else "Hujjatlarni tekshirish",
            "price_text": f"от {format_sum(BROKER_PRICES['docs_from'])} до {format_sum(BROKER_PRICES['docs_to'])}",
        }
        await message.answer(f"{ctx['form_data']['service_label']}\n💰 {ctx['form_data']['price_text']}\n\n{t(lang, 'enter_name')}", reply_markup=broker_menu(lang))
        return
    if text == t(lang, "broker_3"):
        ctx["section"] = "broker"
        ctx["pending_form"] = "broker_name"
        ctx["form_data"] = {
            "service_type": "certification",
            "service_label": "Нюансы по сертификации" if lang == "ru" else "Sertifikatlash bo'yicha нюанслар",
            "price_text": format_sum(BROKER_PRICES["certification"]),
        }
        await message.answer(f"{ctx['form_data']['service_label']}\n💰 {ctx['form_data']['price_text']}\n\n{t(lang, 'enter_name')}", reply_markup=broker_menu(lang))
        return
    if text == t(lang, "broker_4"):
        ctx["section"] = "broker"
        ctx["pending_form"] = "broker_name"
        ctx["form_data"] = {
            "service_type": "tnved_analytics",
            "service_label": "Аналитика по ТН ВЭД коду" if lang == "ru" else "TN VED kodi bo'yicha analitika",
            "price_text": format_sum(BROKER_PRICES["tnved_analytics"]),
        }
        await message.answer(f"{ctx['form_data']['service_label']}\n💰 {ctx['form_data']['price_text']}\n\n{t(lang, 'enter_name')}", reply_markup=broker_menu(lang))
        return

    # logistics menu
    if text == t(lang, "log_how"):
        await safe_answer(message, t(lang, "log_how_text"), reply_markup=log_menu(lang))
        return
    if text == t(lang, "log_request"):
        ctx["section"] = "logistics"
        ctx["pending_form"] = "log_name"
        ctx["form_data"] = {}
        await message.answer(t(lang, "enter_name"), reply_markup=log_menu(lang))
        return

    # legal AI mode
    if ctx.get("mode") == "legal_ai":
        if text == t(lang, "quick_ask"):
            await message.answer("Напишите ваш вопрос." if lang == "ru" else "Savolingizni yozing.", reply_markup=ai_quick_kb(lang))
            return
        question = text
        if not is_customs_question(question):
            await message.answer(t(lang, "not_customs"), reply_markup=ai_quick_kb(lang))
            return
        ai_resp = ask_ai(CUSTOMS_ASSISTANT_PROMPT, question)
        if not ai_resp:
            # fallback answers for quick questions
            low = question.lower()
            if "импорт" in low and "документ" in low:
                ai_resp = "Обычно для импорта нужны контракт, инвойс, упаковочный лист, транспортные документы, при необходимости сертификаты и разрешительные документы."
            elif "экспорт" in low and "документ" in low:
                ai_resp = "Для экспорта обычно нужны контракт, инвойс, упаковочный лист, транспортные документы и документы, подтверждающие происхождение или разрешения, если они требуются."
            elif "сертифик" in low:
                ai_resp = "Сертификация зависит от товара и кода ТН ВЭД. Для некоторых товаров требуются документы Узстандарт, СЭС или другие разрешения."
            elif "тн вэд" in low:
                ai_resp = "Код ТН ВЭД определяется по назначению, составу, материалу, конструкции и техническим характеристикам товара."
            else:
                ai_resp = "Для ответа важно уточнить товар, страну происхождения и цель ввоза или вывоза."
        await safe_answer(message, html.escape(ai_resp) + t(lang, "ai_footer"), reply_markup=ai_quick_kb(lang))
        return

    # legal tnved search mode
    if ctx.get("mode") == "legal_tnved":
        track(uid, username, lang, "legal", "tnved_search", text)
        results = search_tnved(text, 7)
        await safe_answer(message, format_tnved_results(results), reply_markup=legal_menu(lang))
        ctx["mode"] = None
        return

    await message.answer(t(lang, "unknown"), reply_markup=main_menu(lang) if ctx.get("section") is None else {
        "legal": legal_menu(lang),
        "broker": broker_menu(lang),
        "logistics": log_menu(lang),
    }.get(ctx.get("section"), main_menu(lang)))


if __name__ == "__main__":
    print("=== ПРОВЕРКА ОКРУЖАЮЩЕЙ СРЕДЫ ===")
    print("BOT_TOKEN:", "OK" if BOT_TOKEN else "MISSING")
    print("ИДЕНТИФИКАТОР АДМИНИСТРАТИВНОГО ЧАТА:", ADMIN_CHAT_ID or "NOT SET")
    print("ANALYTICS_DB_PATH:", ANALYTICS_DB_PATH)
    load_product_db()
    executor.start_polling(dp, skip_updates=True)
