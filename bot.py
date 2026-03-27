import os
import re
import json
import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Any

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")
ADMIN_PHONE = os.getenv("ADMIN_PHONE", "+998901234567")
PRODUCT_DB_PATH = os.getenv("PRODUCT_DB_PATH", "product_db_super.json")
ANALYTICS_DB_PATH = os.getenv("ANALYTICS_DB_PATH", "analytics.db")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

TXT = {
    "ru": {
        "choose_lang": "Выберите язык:",
        "choose_role": "Выберите режим:",
        "lang_saved": "Язык сохранён.",
        "saved": "Готово. Выберите раздел:",
        "role_physical": "👤 Физическое лицо",
        "role_legal": "🏢 Юридическое лицо",
        "role_broker": "👨‍💼 Для брокеров (PRO)",
        "chat": "💬 Чат с помощником",
        "faq": "❓ FAQ",
        "docs": "📄 Документы",
        "specialist": "👨‍💼 Специалист",
        "change": "🌐 Сменить язык / роль",
        "tnved": "🔎 ТН ВЭД и ставки",
        "exact": "🎯 Точный код и ставка",
        "broker_cost": "💰 Узнать таможенную стоимость",
        "broker_min_avg": "📉 Мин. и средняя стоимость",
        "broker_3m": "📊 База за 3 месяца",
        "back_menu": "⬅️ Назад в меню",
        "back": "⬅️ Назад",
        "pick_category": "Выберите категорию:",
        "pick_group": "Выберите группу:",
        "pick_position": "Выберите позицию:",
        "enter_branch_item": "Напишите товар простыми словами внутри выбранной ветки.",
        "enter_code": "Введите код ТН ВЭД: 4, 6, 8 или 10 цифр.",
        "nothing_found": "Ничего подходящего не найдено. Попробуйте другой товар или нажмите «Специалист».",
        "possible": "Возможные варианты:",
        "code_result": "Результат по коду",
        "source": "Источник",
        "branch_hint": "Если результат не подошёл — нажмите «Специалист».",
        "physical_intro": "Напишите вопрос простыми словами. Я отвечу по правилам для физлиц: лимиты, телефоны, IMEI, авто для личного пользования, декларация, посылки, документы.",
        "legal_intro": "Напишите товар или вопрос простыми словами. Я покажу 3–4 возможных варианта, если смогу определить направление.",
        "faq_intro": "Частые вопросы:\n• сколько телефонов можно ввезти\n• лимит через аэропорт\n• IMEI регистрация\n• временный ввоз авто\n• документы для юрлица\n• как определить код ТН ВЭД",
        "docs_physical": "Документы для физлица:\n• паспорт\n• чеки/инвойс при наличии\n• пассажирская декларация при необходимости\n• документы на авто/телефон в нужных случаях",
        "docs_legal": "Документы для юрлица:\n• контракт\n• инвойс\n• упаковочный лист\n• транспортные документы\n• сертификаты/разрешения при необходимости\n• код ТН ВЭД",
        "physical_no_calc": "В режиме физлица я не показываю брокерские коды и ставки по умолчанию. Могу объяснить правила для личного пользования или направить к специалисту.",
        "broker_intro": "Раздел для брокеров (PRO).\n\nДоступна платная услуга:",
        "broker_pick": "Выберите услугу:",
        "broker_paid": "Это платная услуга. После заявки специалист свяжется с вами.",
        "enter_name": "Введите ваше имя:",
        "enter_product": "Напишите товар / запрос:",
        "enter_country": "Укажите страну происхождения или отправления:",
        "enter_comment": "Добавьте комментарий, если нужно:",
        "service_min_avg": "Мин. и средняя стоимость",
        "service_3m": "База за 3 месяца",
        "application_sent": "✅ Заявка отправлена специалисту.",
        "analytics_empty": "Статистика пока пустая.",
        "analytics_title": "📊 Аналитика бота",
        "role_legal_ready": "Режим юрлица: сначала категории и варианты, отдельная кнопка для точного кода.",
    },
    "uz": {
        "choose_lang": "Tilni tanlang:",
        "choose_role": "Rejimni tanlang:",
        "lang_saved": "Til saqlandi.",
        "saved": "Tayyor. Bo‘limni tanlang:",
        "role_physical": "👤 Jismoniy shaxs",
        "role_legal": "🏢 Yuridik shaxs",
        "role_broker": "👨‍💼 Brokerlar uchun (PRO)",
        "chat": "💬 Yordamchi bilan chat",
        "faq": "❓ FAQ",
        "docs": "📄 Hujjatlar",
        "specialist": "👨‍💼 Mutaxassis",
        "change": "🌐 Til / rolni almashtirish",
        "tnved": "🔎 TN VED va stavkalar",
        "exact": "🎯 Aniq kod va stavka",
        "broker_cost": "💰 Bojxona qiymatini bilish",
        "broker_min_avg": "📉 Min. va o‘rtacha qiymat",
        "broker_3m": "📊 Oxirgi 3 oy bazasi",
        "back_menu": "⬅️ Menyuga qaytish",
        "back": "⬅️ Orqaga",
        "pick_category": "Kategoriyani tanlang:",
        "pick_group": "Guruhni tanlang:",
        "pick_position": "Pozitsiyani tanlang:",
        "enter_branch_item": "Tanlangan bo‘lim ichida tovarni oddiy so‘zlar bilan yozing.",
        "enter_code": "TN VED kodini kiriting: 4, 6, 8 yoki 10 ta raqam.",
        "nothing_found": "Mos natija topilmadi. Boshqa tovarni yozing yoki «Mutaxassis» tugmasini bosing.",
        "possible": "Mumkin bo‘lgan variantlar:",
        "code_result": "Kod bo‘yicha natija",
        "source": "Manba",
        "branch_hint": "Natija mos kelmasa — «Mutaxassis» tugmasini bosing.",
        "physical_intro": "Savolni oddiy so‘zlar bilan yozing. Men jismoniy shaxslar uchun yordam beraman: limitlar, telefonlar, IMEI, shaxsiy foydalanish uchun avto, deklaratsiya, posilkalar, hujjatlar.",
        "legal_intro": "Tovar yoki savolni oddiy so‘zlar bilan yozing. Aniqlashtira olsam, 3–4 variant ko‘rsataman.",
        "faq_intro": "Ko‘p beriladigan savollar:\n• nechta telefon olib kirish mumkin\n• aeroport limiti\n• IMEI ro‘yxatdan o‘tkazish\n• vaqtinchalik auto olib kirish\n• yuridik shaxs hujjatlari\n• TN VED kodini aniqlash",
        "docs_physical": "Jismoniy shaxs uchun hujjatlar:\n• pasport\n• chek/invoys bo‘lsa\n• kerak bo‘lsa yo‘lovchi deklaratsiyasi\n• ayrim holatlarda auto/telefon hujjatlari",
        "docs_legal": "Yuridik shaxs uchun hujjatlar:\n• kontrakt\n• invoys\n• qadoqlash varaqasi\n• transport hujjatlari\n• zarur bo‘lsa sertifikat/ruxsatnomalar\n• TN VED kodi",
        "physical_no_calc": "Jismoniy shaxs rejimida brokerlik kodlari va stavkalarini odatda ko‘rsatmayman. Shaxsiy foydalanish qoidalarini tushuntiraman yoki mutaxassisga yo‘naltiraman.",
        "broker_intro": "Brokerlar uchun bo‘lim (PRO).\n\nPullik xizmat mavjud:",
        "broker_pick": "Xizmatni tanlang:",
        "broker_paid": "Bu pullik xizmat. Ariza yuborilgach, mutaxassis siz bilan bog‘lanadi.",
        "enter_name": "Ismingizni kiriting:",
        "enter_product": "Tovar / so‘rovni yozing:",
        "enter_country": "Kelib chiqish yoki jo‘natish davlatini kiriting:",
        "enter_comment": "Kerak bo‘lsa izoh qoldiring:",
        "service_min_avg": "Min. va o‘rtacha qiymat",
        "service_3m": "Oxirgi 3 oy bazasi",
        "application_sent": "✅ Ariza mutaxassisga yuborildi.",
        "analytics_empty": "Statistika hozircha bo‘sh.",
        "analytics_title": "📊 Bot analitikasi",
        "role_legal_ready": "Yuridik shaxs rejimi: avval kategoriyalar va variantlar, aniq kod uchun alohida tugma.",
    }
}

USER_CTX = {}

def ctx(user_id):
    if user_id not in USER_CTX:
        USER_CTX[user_id] = {"lang":"ru","role":None,"mode":None,"category":None,"group":None,"position":None,"pending_form":None,"form_data":{}}
    return USER_CTX[user_id]

def reset_mode(user_id):
    c = ctx(user_id)
    c["mode"] = None
    c["category"] = None
    c["group"] = None
    c["position"] = None
    c["pending_form"] = None
    c["form_data"] = {}

def db_conn():
    conn = sqlite3.connect(ANALYTICS_DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,username TEXT,lang TEXT,role TEXT,event_type TEXT,event_value TEXT,created_at TEXT)")
    return conn

def track(user_id, username, lang, role, event_type, event_value=""):
    conn = db_conn()
    conn.execute("INSERT INTO events (user_id, username, lang, role, event_type, event_value, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (user_id, username or "", lang or "", role or "", event_type, event_value, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def analytics_text(lang):
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(DISTINCT user_id) FROM events")
    users = cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM events WHERE event_type='message'")
    messages = cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM events WHERE event_type='application'")
    applications = cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM events WHERE event_type='broker_application'")
    broker_apps = cur.fetchone()[0] or 0
    cur.execute("SELECT role, COUNT(*) FROM events WHERE event_type='role_selected' GROUP BY role ORDER BY COUNT(*) DESC")
    roles = cur.fetchall()
    cur.execute("SELECT event_value, COUNT(*) FROM events WHERE event_type='code_search' GROUP BY event_value ORDER BY COUNT(*) DESC LIMIT 10")
    codes = cur.fetchall()
    conn.close()
    if not any([users, messages, applications, broker_apps, roles, codes]):
        return TXT[lang]["analytics_empty"]
    lines = [f"<b>{TXT[lang]['analytics_title']}</b>", "", f"👥 Пользователи: {users}", f"💬 Сообщения: {messages}", f"📩 Заявки специалисту: {applications}", f"💼 PRO-заявки брокеров: {broker_apps}", ""]
    if roles:
        lines.append("<b>Режимы:</b>")
        for role, count in roles:
            lines.append(f"• {role}: {count}")
        lines.append("")
    if codes:
        lines.append("<b>Топ кодов:</b>")
        for code, count in codes:
            lines.append(f"• {code}: {count}")
    return "\n".join(lines)

TREE = {
    "medicine":{"label":{"ru":"💊 Медицина","uz":"💊 Tibbiyot"},"groups":{"drugs":{"label":{"ru":"💊 Лекарства","uz":"💊 Dori vositalari"},"positions":{"tablets":{"label":{"ru":"💊 Таблетки","uz":"💊 Tabletkalar"},"hint":{"ru":"Примеры: парацетамол, витамины, антибиотики","uz":"Misollar: paratsetamol, vitaminlar, antibiotiklar"}},"syrups":{"label":{"ru":"🧴 Сиропы","uz":"🧴 Sirop"},"hint":{"ru":"Примеры: сироп от кашля, детский сироп","uz":"Misollar: yo‘tal siropi, bolalar siropi"}}}}}},
    "electronics":{"label":{"ru":"📱 Электроника","uz":"📱 Elektronika"},"groups":{"phones":{"label":{"ru":"📱 Телефоны","uz":"📱 Telefonlar"},"positions":{"smartphones":{"label":{"ru":"📱 Смартфоны","uz":"📱 Smartfonlar"},"hint":{"ru":"Примеры: iPhone, Samsung, Redmi","uz":"Misollar: iPhone, Samsung, Redmi"}},"speakers":{"label":{"ru":"🔊 Колонки","uz":"🔊 Kolonkalar"},"hint":{"ru":"Примеры: компьютерные колонки, bluetooth","uz":"Misollar: kompyuter kolonkasi, bluetooth"}}}}}},
    "auto":{"label":{"ru":"🚗 Авто и запчасти","uz":"🚗 Avto va ehtiyot qismlar"},"groups":{"cars":{"label":{"ru":"🚘 Легковые автомобили","uz":"🚘 Yengil avtomobillar"},"positions":{"ev":{"label":{"ru":"⚡ Электромобили","uz":"⚡ Elektromobillar"},"hint":{"ru":"Примеры: BYD Song Plus, Tesla","uz":"Misollar: BYD Song Plus, Tesla"}},"hybrid":{"label":{"ru":"🔋 Гибриды","uz":"🔋 Gibridlar"},"hint":{"ru":"Примеры: гибрид 1.5, Prius","uz":"Misollar: gibrid 1.5, Prius"}},"tires":{"label":{"ru":"🛞 Шины","uz":"🛞 Shinalar"},"hint":{"ru":"Примеры: автошины, зимние шины","uz":"Misollar: avtoshina, qishki shina"}}}}}},
    "food":{"label":{"ru":"🫒 Продукты и масла","uz":"🫒 Oziq-ovqat va moylar"},"groups":{"oil":{"label":{"ru":"🫒 Масла","uz":"🫒 Moylar"},"positions":{"sunflower_oil":{"label":{"ru":"🌻 Подсолнечное масло","uz":"🌻 Kungaboqar moyi"},"hint":{"ru":"Примеры: подсолнечное масло, рафинированное масло","uz":"Misollar: kungaboqar moyi, rafinatsiyalangan moy"}}}}}}
}

def load_db():
    if os.path.exists(PRODUCT_DB_PATH):
        with open(PRODUCT_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}
PRODUCT_DB = load_db()

def t(lang, key):
    return TXT.get(lang, TXT["ru"]).get(key, key)

def build_lang_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Русский", "O'zbekcha")
    return kb

def role_kb(lang):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "role_physical"), t(lang, "role_legal"))
    kb.add(t(lang, "role_broker"))
    return kb

def physical_menu(lang):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "chat"), t(lang, "faq"))
    kb.add(t(lang, "docs"), t(lang, "specialist"))
    kb.add(t(lang, "change"))
    return kb

def legal_menu(lang):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "tnved"), t(lang, "exact"))
    kb.add(t(lang, "chat"), t(lang, "docs"))
    kb.add(t(lang, "broker_cost"), t(lang, "specialist"))
    kb.add("📊 Analytics", t(lang, "change"))
    return kb

def broker_menu(lang):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "broker_cost"))
    kb.add(t(lang, "back_menu"))
    return kb

def broker_cost_menu(lang):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "broker_min_avg"), t(lang, "broker_3m"))
    kb.add(t(lang, "back_menu"))
    return kb

def category_kb(lang):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for cat in TREE.values():
        kb.add(cat["label"][lang])
    kb.add(t(lang, "back_menu"))
    return kb

def group_kb(lang, category_id):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for group in TREE[category_id]["groups"].values():
        kb.add(group["label"][lang])
    kb.add(t(lang, "back"), t(lang, "back_menu"))
    return kb

def position_kb(lang, category_id, group_id):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for pos in TREE[category_id]["groups"][group_id]["positions"].values():
        kb.add(pos["label"][lang])
    kb.add(t(lang, "back"), t(lang, "back_menu"))
    return kb

def normalize_code(value):
    return "".join(ch for ch in str(value) if ch.isdigit())

def normalize_text(value):
    return re.sub(r"\s+", " ", value.strip().lower())

def find_ids_by_label(lang, label):
    for cat_id, cat in TREE.items():
        if cat["label"][lang] == label:
            return ("category", cat_id)
        for group_id, group in cat["groups"].items():
            if group["label"][lang] == label:
                return ("group", cat_id, group_id)
            for pos_id, pos in group["positions"].items():
                if pos["label"][lang] == label:
                    return ("position", cat_id, group_id, pos_id)
    return None

def format_item(item, lang, idx):
    name = item.get("name_ru") if lang == "ru" else item.get("name_uz")
    return f"{idx}) <b>{name}</b>\nКод: <code>{item.get('code','')}</code>\nПошлина: {item.get('duty','уточнить')}\nНДС: {item.get('vat','12%')}\nАкциз: {item.get('excise','нет')}\n♻️ Утильсбор: {item.get('util','нет')}\n{t(lang, 'source')}: {item.get('source','локальная база')}\n"

def find_by_code(code):
    code = normalize_code(code)
    if not code:
        return []
    if code in PRODUCT_DB:
        return [PRODUCT_DB[code]]
    exact = [v for k, v in PRODUCT_DB.items() if normalize_code(k) == code]
    if exact:
        return exact[:4]
    pref = [v for k, v in PRODUCT_DB.items() if normalize_code(k).startswith(code)]
    if pref:
        pref = sorted(pref, key=lambda x: len(normalize_code(x.get("code", ""))))
        return pref[:4]
    return []

def search_branch(query, category, group, position):
    q = normalize_text(query)
    strict, grp, cat, other = [], [], [], []
    for item in PRODUCT_DB.values():
        hay = " ".join([normalize_text(item.get("name_ru","")), normalize_text(item.get("name_uz",""))] + [normalize_text(x) for x in item.get("examples", [])])
        if q not in hay:
            continue
        if item.get("category") == category and item.get("group") == group and item.get("position") == position:
            strict.append(item)
        elif item.get("category") == category and item.get("group") == group:
            grp.append(item)
        elif item.get("category") == category:
            cat.append(item)
        else:
            other.append(item)
    return (strict or grp or cat or other)[:4]

def physical_answer(query, lang):
    q = normalize_text(query)
    if any(x in q for x in ["телефон", "iphone", "смартфон", "phone"]):
        return "Для физлица важны лимит, личное пользование и IMEI-регистрация." if lang == "ru" else "Jismoniy shaxs uchun limit, shaxsiy foydalanish va IMEI ro‘yxatdan o‘tkazish muhim."
    if any(x in q for x in ["авто", "машин", "byd", "tesla", "gibrid", "электро", "mashina", "avto"]):
        return "Для физлица по авто важны тип, возраст, объём двигателя, документы и цель ввоза." if lang == "ru" else "Jismoniy shaxs uchun avto bo‘yicha turi, yoshi, dvigatel hajmi, hujjatlar va olib kirish maqsadi muhim."
    return t(lang, "physical_no_calc")

async def send_main_menu(message, user_id):
    c = ctx(user_id)
    lang = c["lang"]
    role = c["role"]
    reset_mode(user_id)
    c["role"] = role
    c["lang"] = lang
    if role == "physical":
        await message.answer(t(lang, "saved"), reply_markup=physical_menu(lang))
    elif role == "legal":
        await message.answer(t(lang, "saved") + "\n\n" + t(lang, "role_legal_ready"), reply_markup=legal_menu(lang))
    elif role == "broker":
        await message.answer(t(lang, "broker_intro"), reply_markup=broker_menu(lang))
    else:
        await message.answer(t(lang, "choose_role"), reply_markup=role_kb(lang))

@dp.message_handler(commands=["start"])
async def start_cmd(message):
    USER_CTX[message.from_user.id] = {"lang":"ru","role":None,"mode":"choose_lang","category":None,"group":None,"position":None,"pending_form":None,"form_data":{}}
    track(message.from_user.id, message.from_user.username or "", "ru", "", "button", "/start")
    await message.answer(TXT["ru"]["choose_lang"], reply_markup=build_lang_kb())

@dp.message_handler(commands=["myid"])
async def myid_cmd(message):
    await message.answer(f"Ваш ID: <code>{message.from_user.id}</code>")

@dp.message_handler(commands=["analytics", "stats"])
async def analytics_cmd(message):
    if ADMIN_CHAT_ID and str(message.from_user.id) != str(ADMIN_CHAT_ID):
        return
    await message.answer(analytics_text(ctx(message.from_user.id)["lang"]))

@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def router(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    c = ctx(user_id)
    lang = c["lang"]
    role = c["role"]
    text = message.text.strip()
    track(user_id, username, lang, role or "", "message", text)

    if text in ["Русский", "O'zbekcha"]:
        c["lang"] = "ru" if text == "Русский" else "uz"
        c["mode"] = "choose_role"
        track(user_id, username, c["lang"], role or "", "button", text)
        await message.answer(t(c["lang"], "lang_saved") + "\n" + t(c["lang"], "choose_role"), reply_markup=role_kb(c["lang"]))
        return

    lang = c["lang"]

    if text in [t(lang, "role_physical"), t(lang, "role_legal"), t(lang, "role_broker")]:
        if text == t(lang, "role_physical"):
            c["role"] = "physical"
        elif text == t(lang, "role_legal"):
            c["role"] = "legal"
        else:
            c["role"] = "broker"
        c["mode"] = None
        track(user_id, username, lang, c["role"], "role_selected", c["role"])
        await send_main_menu(message, user_id)
        return

    if text == t(lang, "change"):
        reset_mode(user_id)
        c["role"] = None
        c["mode"] = "choose_lang"
        await message.answer(t(lang, "choose_lang"), reply_markup=build_lang_kb())
        return

    if text == t(lang, "back_menu"):
        await send_main_menu(message, user_id)
        return

    if text == t(lang, "back"):
        if c["mode"] == "legal_group":
            c["mode"] = "legal_category"
            await message.answer(t(lang, "pick_category"), reply_markup=category_kb(lang))
            return
        if c["mode"] == "legal_position":
            c["mode"] = "legal_group"
            await message.answer(t(lang, "pick_group"), reply_markup=group_kb(lang, c["category"]))
            return
        await send_main_menu(message, user_id)
        return

    if text == t(lang, "specialist"):
        reset_mode(user_id)
        c["pending_form"] = "specialist_name"
        await message.answer(t(lang, "enter_name"))
        return

    if role == "physical":
        if text == t(lang, "faq"):
            await message.answer(t(lang, "faq_intro"), reply_markup=physical_menu(lang)); return
        if text == t(lang, "docs"):
            await message.answer(t(lang, "docs_physical"), reply_markup=physical_menu(lang)); return
        if text == t(lang, "chat"):
            reset_mode(user_id); c["mode"] = "physical_chat"
            await message.answer(t(lang, "physical_intro"), reply_markup=physical_menu(lang)); return
        if text in [t(lang, "tnved"), t(lang, "exact"), t(lang, "broker_cost")]:
            await message.answer(t(lang, "physical_no_calc"), reply_markup=physical_menu(lang)); return

    if role == "legal":
        if text == t(lang, "faq"):
            await message.answer(t(lang, "faq_intro"), reply_markup=legal_menu(lang)); return
        if text == t(lang, "docs"):
            await message.answer(t(lang, "docs_legal"), reply_markup=legal_menu(lang)); return
        if text == t(lang, "chat"):
            reset_mode(user_id); c["mode"] = "legal_chat"
            await message.answer(t(lang, "legal_intro"), reply_markup=legal_menu(lang)); return
        if text == t(lang, "tnved"):
            reset_mode(user_id); c["mode"] = "legal_category"
            await message.answer(t(lang, "pick_category"), reply_markup=category_kb(lang)); return
        if text == t(lang, "exact"):
            reset_mode(user_id); c["mode"] = "exact_code"
            await message.answer(t(lang, "enter_code"), reply_markup=legal_menu(lang)); return
        if text == t(lang, "broker_cost"):
            c["role"] = "broker"
            await send_main_menu(message, user_id); return
        if text == "📊 Analytics" and (not ADMIN_CHAT_ID or str(user_id) == str(ADMIN_CHAT_ID)):
            await message.answer(analytics_text(lang), reply_markup=legal_menu(lang)); return

    if role == "broker":
        if text == t(lang, "broker_cost"):
            reset_mode(user_id); c["mode"] = "broker_service"
            await message.answer(t(lang, "broker_pick"), reply_markup=broker_cost_menu(lang)); return

    if c["mode"] == "legal_category":
        found = find_ids_by_label(lang, text)
        if found and found[0] == "category":
            c["category"] = found[1]
            c["mode"] = "legal_group"
            await message.answer(t(lang, "pick_group"), reply_markup=group_kb(lang, c["category"])); return
        await message.answer(t(lang, "pick_category"), reply_markup=category_kb(lang)); return

    if c["mode"] == "legal_group":
        found = find_ids_by_label(lang, text)
        if found and found[0] == "group" and found[1] == c["category"]:
            c["group"] = found[2]
            c["mode"] = "legal_position"
            await message.answer(t(lang, "pick_position"), reply_markup=position_kb(lang, c["category"], c["group"])); return
        await message.answer(t(lang, "pick_group"), reply_markup=group_kb(lang, c["category"])); return

    if c["mode"] == "legal_position":
        found = find_ids_by_label(lang, text)
        if found and found[0] == "position" and found[1] == c["category"] and found[2] == c["group"]:
            c["position"] = found[3]
            c["mode"] = "legal_item"
            hint = TREE[c["category"]]["groups"][c["group"]]["positions"][c["position"]]["hint"][lang]
            await message.answer(f"{t(lang, 'enter_branch_item')}\n\n{hint}", reply_markup=legal_menu(lang)); return
        await message.answer(t(lang, "pick_position"), reply_markup=position_kb(lang, c["category"], c["group"])); return

    if c["mode"] == "legal_item":
        results = search_branch(text, c["category"], c["group"], c["position"])
        if not results:
            await message.answer(t(lang, "nothing_found"), reply_markup=legal_menu(lang)); return
        out = f"<b>{t(lang, 'possible')}</b>\n\n"
        for i, item in enumerate(results, 1):
            out += format_item(item, lang, i) + "\n"
        out += t(lang, "branch_hint")
        await message.answer(out, reply_markup=legal_menu(lang)); return

    if c["mode"] == "exact_code":
        results = find_by_code(text)
        track(user_id, username, lang, role or "", "code_search", normalize_code(text))
        if not results:
            await message.answer(t(lang, "nothing_found"), reply_markup=legal_menu(lang)); return
        out = f"<b>{t(lang, 'code_result')}</b>\n\n"
        for i, item in enumerate(results, 1):
            out += format_item(item, lang, i) + "\n"
        await message.answer(out, reply_markup=legal_menu(lang)); return

    if c["mode"] == "legal_chat":
        q = normalize_text(text)
        results = []
        for item in PRODUCT_DB.values():
            hay = " ".join([normalize_text(item.get("name_ru","")), normalize_text(item.get("name_uz",""))] + [normalize_text(x) for x in item.get("examples", [])])
            if q and q in hay:
                results.append(item)
        if not results:
            await message.answer(t(lang, "nothing_found"), reply_markup=legal_menu(lang)); return
        out = f"<b>{t(lang, 'possible')}</b>\n\n"
        for i, item in enumerate(results[:4], 1):
            out += format_item(item, lang, i) + "\n"
        out += t(lang, "branch_hint")
        await message.answer(out, reply_markup=legal_menu(lang)); return

    if c["mode"] == "physical_chat":
        await message.answer(physical_answer(text, lang), reply_markup=physical_menu(lang)); return

    if c["pending_form"] == "specialist_name":
        c["form_data"]["name"] = text
        c["pending_form"] = "specialist_product"
        await message.answer(t(lang, "enter_product")); return

    if c["pending_form"] == "specialist_product":
        c["form_data"]["product"] = text
        c["pending_form"] = None
        msg = f"📩 <b>Новая заявка специалисту</b>\n\nИмя: {c['form_data'].get('name','')}\nЗапрос: {c['form_data'].get('product','')}\nРежим: {role or '-'}\nID: <code>{user_id}</code>\nUsername: @{username or '-'}"
        if ADMIN_CHAT_ID:
            try:
                await bot.send_message(ADMIN_CHAT_ID, msg)
            except Exception:
                pass
        track(user_id, username, lang, role or "", "application", c['form_data'].get('product',''))
        await message.answer(t(lang, "application_sent"))
        await send_main_menu(message, user_id); return

    if c["mode"] == "broker_service":
        if text == t(lang, "broker_min_avg"):
            c["form_data"] = {"service": t(lang, "service_min_avg")}
            c["pending_form"] = "broker_name"
            c["mode"] = None
            await message.answer(t(lang, "broker_paid") + "\n\n" + t(lang, "enter_name")); return
        if text == t(lang, "broker_3m"):
            c["form_data"] = {"service": t(lang, "service_3m")}
            c["pending_form"] = "broker_name"
            c["mode"] = None
            await message.answer(t(lang, "broker_paid") + "\n\n" + t(lang, "enter_name")); return
        await message.answer(t(lang, "broker_pick"), reply_markup=broker_cost_menu(lang)); return

    if c["pending_form"] == "broker_name":
        c["form_data"]["name"] = text
        c["pending_form"] = "broker_product"
        await message.answer(t(lang, "enter_product")); return

    if c["pending_form"] == "broker_product":
        c["form_data"]["product"] = text
        c["pending_form"] = "broker_country"
        await message.answer(t(lang, "enter_country")); return

    if c["pending_form"] == "broker_country":
        c["form_data"]["country"] = text
        c["pending_form"] = "broker_comment"
        await message.answer(t(lang, "enter_comment")); return

    if c["pending_form"] == "broker_comment":
        c["form_data"]["comment"] = text
        c["pending_form"] = None
        msg = f"💼 <b>Новая PRO-заявка</b>\n\nУслуга: {c['form_data'].get('service','')}\nИмя: {c['form_data'].get('name','')}\nТовар: {c['form_data'].get('product','')}\nСтрана: {c['form_data'].get('country','')}\nКомментарий: {c['form_data'].get('comment','')}\nID: <code>{user_id}</code>\nUsername: @{username or '-'}"
        if ADMIN_CHAT_ID:
            try:
                await bot.send_message(ADMIN_CHAT_ID, msg)
            except Exception:
                pass
        track(user_id, username, lang, role or "", "broker_application", c['form_data'].get('service',''))
        await message.answer(t(lang, "application_sent"))
        await send_main_menu(message, user_id); return

    if role == "physical":
        await message.answer(t(lang, "physical_no_calc"), reply_markup=physical_menu(lang))
    elif role == "legal":
        await message.answer(t(lang, "saved"), reply_markup=legal_menu(lang))
    elif role == "broker":
        await message.answer(t(lang, "broker_intro"), reply_markup=broker_menu(lang))
    else:
        await message.answer(t(lang, "choose_lang"), reply_markup=build_lang_kb())

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
