
import os
import re
import json
import logging
from typing import Dict, List, Any

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")
ADMIN_PHONE = os.getenv("ADMIN_PHONE", "+998901234567")
DB_PATH = os.getenv("PRODUCT_DB_PATH", "product_db_super.json")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

TXT = {
    "ru": {
        "choose_lang": "Выберите язык:",
        "choose_role": "Выберите режим:",
        "role_physical": "👤 Физическое лицо",
        "role_legal": "🏢 Юридическое лицо",
        "role_broker": "👨‍💼 Для брокеров (PRO)",
        "saved": "Готово. Выберите раздел:",
        "back_menu": "⬅️ Назад в меню",
        "back": "⬅️ Назад",
        "specialist": "👨‍💼 Специалист",
        "change": "🌐 Сменить язык / роль",
        "chat": "💬 Чат с помощником",
        "faq": "❓ FAQ",
        "docs": "📄 Документы",
        "tnved": "🔎 ТН ВЭД и ставки",
        "exact": "🎯 Точный код и ставка",
        "broker": "👨‍💼 Для брокеров (PRO)",
        "broker_cost": "💰 Узнать таможенную стоимость",
        "broker_min_avg": "📉 Мин. и средняя стоимость",
        "broker_3m": "📊 База за 3 месяца",
        "broker_intro": "Раздел для брокеров (PRO).\n\nДоступна платная услуга:",
        "broker_pick": "Выберите услугу:",
        "broker_paid": "Это платная услуга. После заявки специалист свяжется с вами.",
        "enter_code": "Введите код ТН ВЭД: 4, 6, 8 или 10 цифр.",
        "no_code_in_physical": "В режиме физлица коды и ставки отдельно не показываются.",
        "pick_category": "Выберите категорию:",
        "pick_group": "Выберите группу:",
        "pick_position": "Выберите позицию:",
        "enter_item_in_branch": "Напишите товар простыми словами внутри выбранной ветки.",
        "nothing_found": "Ничего подходящего не найдено. Попробуйте другой товар или нажмите «Специалист».",
        "faq_intro": "Частые вопросы:\n• сколько телефонов можно ввезти\n• лимит через аэропорт\n• IMEI регистрация\n• временный ввоз авто\n• документы для юрлица\n• как определить код ТН ВЭД",
        "docs_physical": "Документы для физлица:\n• паспорт\n• чеки/инвойс при наличии\n• пассажирская декларация при необходимости\n• документы на авто/телефон в нужных случаях",
        "docs_legal": "Документы для юрлица:\n• контракт\n• инвойс\n• упаковочный лист\n• транспортные документы\n• сертификаты/разрешения при необходимости\n• код ТН ВЭД",
        "physical_chat_intro": "Напишите вопрос простыми словами. Я отвечу как помощник для физлиц: лимиты, IMEI, авто для личного пользования, декларация, посылки, документы.",
        "legal_chat_intro": "Напишите товар или вопрос простыми словами. Я покажу 3–4 варианта, если смогу определить направление.",
        "physical_mode_no_calc": "В режиме физлица я не показываю брокерские коды и ставки по умолчанию. Могу объяснить правила для личного пользования или направить к специалисту.",
        "role_legal_ready": "Режим юрлица: сначала категории и варианты, отдельная кнопка для точного кода.",
        "branch_hint": "Если результат не подошёл — нажмите «Специалист».",
        "source": "Источник",
        "application_sent": "✅ Заявка отправлена специалисту.",
        "enter_name": "Введите ваше имя:",
        "enter_product": "Напишите товар / запрос:",
        "enter_country": "Укажите страну происхождения или отправления:",
        "enter_comment": "Добавьте комментарий, если нужно:",
        "service_min_avg": "Мин. и средняя стоимость",
        "service_3m": "База за 3 месяца",
        "lang_saved": "Язык сохранён.",
        "code_result": "Результат по коду",
        "possible": "Возможные варианты:",
    },
    "uz": {
        "choose_lang": "Tilni tanlang:",
        "choose_role": "Rejimni tanlang:",
        "role_physical": "👤 Jismoniy shaxs",
        "role_legal": "🏢 Yuridik shaxs",
        "role_broker": "👨‍💼 Brokerlar uchun (PRO)",
        "saved": "Tayyor. Bo‘limni tanlang:",
        "back_menu": "⬅️ Menyuga qaytish",
        "back": "⬅️ Orqaga",
        "specialist": "👨‍💼 Mutaxassis",
        "change": "🌐 Til / rolni almashtirish",
        "chat": "💬 Yordamchi bilan chat",
        "faq": "❓ FAQ",
        "docs": "📄 Hujjatlar",
        "tnved": "🔎 TN VED va stavkalar",
        "exact": "🎯 Aniq kod va stavka",
        "broker": "👨‍💼 Brokerlar uchun (PRO)",
        "broker_cost": "💰 Bojxona qiymatini bilish",
        "broker_min_avg": "📉 Min. va o‘rtacha qiymat",
        "broker_3m": "📊 Oxirgi 3 oy bazasi",
        "broker_intro": "Brokerlar uchun bo‘lim (PRO).\n\nPullik xizmat mavjud:",
        "broker_pick": "Xizmatni tanlang:",
        "broker_paid": "Bu pullik xizmat. Ariza yuborilgach, mutaxassis siz bilan bog‘lanadi.",
        "enter_code": "TN VED kodini kiriting: 4, 6, 8 yoki 10 ta raqam.",
        "no_code_in_physical": "Jismoniy shaxs rejimida kod va stavkalar alohida ko‘rsatilmaydi.",
        "pick_category": "Kategoriyani tanlang:",
        "pick_group": "Guruhni tanlang:",
        "pick_position": "Pozitsiyani tanlang:",
        "enter_item_in_branch": "Tanlangan bo‘lim ichida tovarni oddiy so‘zlar bilan yozing.",
        "nothing_found": "Mos natija topilmadi. Boshqa tovarni yozing yoki «Mutaxassis» tugmasini bosing.",
        "faq_intro": "Ko‘p beriladigan savollar:\n• nechta telefon olib kirish mumkin\n• aeroport limiti\n• IMEI ro‘yxatdan o‘tkazish\n• vaqtinchalik auto olib kirish\n• yuridik shaxs hujjatlari\n• TN VED kodini aniqlash",
        "docs_physical": "Jismoniy shaxs uchun hujjatlar:\n• pasport\n• chek/invoys bo‘lsa\n• kerak bo‘lsa yo‘lovchi deklaratsiyasi\n• ayrim holatlarda auto/telefon hujjatlari",
        "docs_legal": "Yuridik shaxs uchun hujjatlar:\n• kontrakt\n• invoys\n• qadoqlash varaqasi\n• transport hujjatlari\n• zarur bo‘lsa sertifikat/ruxsatnomalar\n• TN VED kodi",
        "physical_chat_intro": "Savolni oddiy so‘zlar bilan yozing. Men jismoniy shaxslar uchun yordam beraman: limitlar, IMEI, shaxsiy foydalanish uchun auto, deklaratsiya, posilkalar, hujjatlar.",
        "legal_chat_intro": "Tovar yoki savolni oddiy so‘zlar bilan yozing. Aniqlashtira olsam, 3–4 variant ko‘rsataman.",
        "physical_mode_no_calc": "Jismoniy shaxs rejimida brokerlik kodlari va stavkalarini odatda ko‘rsatmayman. Shaxsiy foydalanish qoidalarini tushuntiraman yoki mutaxassisga yo‘naltiraman.",
        "role_legal_ready": "Yuridik shaxs rejimi: avval kategoriyalar va variantlar, aniq kod uchun alohida tugma.",
        "branch_hint": "Natija mos kelmasa — «Mutaxassis» tugmasini bosing.",
        "source": "Manba",
        "application_sent": "✅ Ariza mutaxassisga yuborildi.",
        "enter_name": "Ismingizni kiriting:",
        "enter_product": "Tovar / so‘rovni yozing:",
        "enter_country": "Kelib chiqish yoki jo‘natish davlatini kiriting:",
        "enter_comment": "Kerak bo‘lsa izoh qoldiring:",
        "service_min_avg": "Min. va o‘rtacha qiymat",
        "service_3m": "Oxirgi 3 oy bazasi",
        "lang_saved": "Til saqlandi.",
        "code_result": "Kod bo‘yicha natija",
        "possible": "Mumkin bo‘lgan variantlar:",
    }
}

class Flow(StatesGroup):
    choose_lang = State()
    choose_role = State()
    legal_category = State()
    legal_group = State()
    legal_position = State()
    legal_item = State()
    exact_code = State()
    physical_chat = State()
    legal_chat = State()
    specialist_name = State()
    specialist_product = State()
    broker_service = State()
    broker_name = State()
    broker_product = State()
    broker_country = State()
    broker_comment = State()

TREE = {
    "medicine": {
        "label": {"ru": "💊 Медицина", "uz": "💊 Tibbiyot"},
        "groups": {
            "drugs": {
                "label": {"ru": "💊 Лекарства", "uz": "💊 Dori vositalari"},
                "positions": {
                    "tablets": {"label": {"ru": "💊 Таблетки", "uz": "💊 Tabletkalar"}, "hint": {"ru": "Примеры: парацетамол, витамины, антибиотики", "uz": "Misollar: paratsetamol, vitaminlar, antibiotiklar"}},
                    "syrups": {"label": {"ru": "🧴 Сиропы", "uz": "🧴 Sirop"}, "hint": {"ru": "Примеры: сироп от кашля, детский сироп", "uz": "Misollar: yo‘tal siropi, bolalar siropi"}},
                }
            }
        }
    },
    "electronics": {
        "label": {"ru": "📱 Электроника", "uz": "📱 Elektronika"},
        "groups": {
            "phones": {
                "label": {"ru": "📱 Телефоны", "uz": "📱 Telefonlar"},
                "positions": {
                    "smartphones": {"label": {"ru": "📱 Смартфоны", "uz": "📱 Smartfonlar"}, "hint": {"ru": "Примеры: iPhone, Samsung, Redmi", "uz": "Misollar: iPhone, Samsung, Redmi"}},
                    "speakers": {"label": {"ru": "🔊 Колонки", "uz": "🔊 Kolonkalar"}, "hint": {"ru": "Примеры: компьютерные колонки, bluetooth", "uz": "Misollar: kompyuter kolonkasi, bluetooth"}},
                }
            }
        }
    },
    "auto": {
        "label": {"ru": "🚗 Авто и запчасти", "uz": "🚗 Avto va ehtiyot qismlar"},
        "groups": {
            "cars": {
                "label": {"ru": "🚘 Легковые автомобили", "uz": "🚘 Yengil avtomobillar"},
                "positions": {
                    "ev": {"label": {"ru": "⚡ Электромобили", "uz": "⚡ Elektromobillar"}, "hint": {"ru": "Примеры: BYD Song Plus, Tesla", "uz": "Misollar: BYD Song Plus, Tesla"}},
                    "hybrid": {"label": {"ru": "🔋 Гибриды", "uz": "🔋 Gibridlar"}, "hint": {"ru": "Примеры: гибрид 1.5, Prius", "uz": "Misollar: gibrid 1.5, Prius"}},
                    "tires": {"label": {"ru": "🛞 Шины", "uz": "🛞 Shinalar"}, "hint": {"ru": "Примеры: автошины, зимние шины", "uz": "Misollar: avtoshina, qishki shina"}},
                }
            }
        }
    },
    "food": {
        "label": {"ru": "🫒 Продукты и масла", "uz": "🫒 Oziq-ovqat va moylar"},
        "groups": {
            "oil": {
                "label": {"ru": "🫒 Масла", "uz": "🫒 Moylar"},
                "positions": {
                    "sunflower_oil": {"label": {"ru": "🌻 Подсолнечное масло", "uz": "🌻 Kungaboqar moyi"}, "hint": {"ru": "Примеры: подсолнечное масло, рафинированное масло", "uz": "Misollar: kungaboqar moyi, rafinatsiyalangan moy"}},
                }
            }
        }
    }
}

def seed_db():
    return {
        "1512": {"code": "1512", "name_ru": "Масло подсолнечное, сафлоровое или хлопковое и их фракции", "name_uz": "Kungaboqar, safsar yoki paxta moyi va ularning fraksiyalari", "category": "food", "group": "oil", "position": "sunflower_oil", "examples": ["подсолнечное масло", "масло растительное"], "duty": "5%", "vat": "12%", "excise": "нет", "util": "нет", "source": "ПҚ-3818"},
        "1512199002": {"code": "1512199002", "name_ru": "Подсолнечное масло, прочее", "name_uz": "Kungaboqar moyi, boshqa", "category": "food", "group": "oil", "position": "sunflower_oil", "examples": ["подсолнечное масло", "рафинированное масло"], "duty": "5%", "vat": "12%", "excise": "нет", "util": "нет", "source": "ПҚ-3818"},
        "3004900000": {"code": "3004900000", "name_ru": "Лекарственные средства прочие, в дозированных формах", "name_uz": "Dozalangan shakldagi boshqa dori vositalari", "category": "medicine", "group": "drugs", "position": "tablets", "examples": ["таблетки", "витамины", "парацетамол"], "duty": "0%", "vat": "12%", "excise": "нет", "util": "нет", "source": "ПҚ-3818"},
        "3004500000": {"code": "3004500000", "name_ru": "Лекарственные средства, содержащие витамины", "name_uz": "Vitamin saqlovchi dori vositalari", "category": "medicine", "group": "drugs", "position": "tablets", "examples": ["витамины", "витамин C", "таблетки с витаминами"], "duty": "0%", "vat": "12%", "excise": "нет", "util": "нет", "source": "ПҚ-3818"},
        "3004100000": {"code": "3004100000", "name_ru": "Лекарственные средства, содержащие пенициллины или их производные", "name_uz": "Penitsillin yoki hosilalarini saqlovchi dori vositalari", "category": "medicine", "group": "drugs", "position": "tablets", "examples": ["антибиотики", "таблетки антибиотики"], "duty": "0%", "vat": "12%", "excise": "нет", "util": "нет", "source": "ПҚ-3818"},
        "8517130000": {"code": "8517130000", "name_ru": "Смартфоны", "name_uz": "Smartfonlar", "category": "electronics", "group": "phones", "position": "smartphones", "examples": ["смартфон", "iphone", "samsung"], "duty": "0%", "vat": "12%", "excise": "нет", "util": "нет", "source": "ПҚ-3818"},
        "8518210000": {"code": "8518210000", "name_ru": "Одиночные громкоговорители в корпусе", "name_uz": "Korpusdagi yakka karnaylar", "category": "electronics", "group": "phones", "position": "speakers", "examples": ["колонки", "громкоговоритель", "компьютерные колонки"], "duty": "15%", "vat": "12%", "excise": "нет", "util": "нет", "source": "ПҚ-3818"},
        "8703800001": {"code": "8703800001", "name_ru": "Электромобили", "name_uz": "Elektromobillar", "category": "auto", "group": "cars", "position": "ev", "examples": ["электромобиль", "byd song plus", "tesla"], "duty": "0%", "vat": "12%", "excise": "нет", "util": "120 БРВ (до 3 лет) / 210 БРВ (старше 3 лет)", "source": "ПҚ-3818 + ПКМ-347"},
        "8703400000": {"code": "8703400000", "name_ru": "Гибридные легковые автомобили", "name_uz": "Gibrid yengil avtomobillar", "category": "auto", "group": "cars", "position": "hybrid", "examples": ["гибрид", "гибрид 1.5", "prius"], "duty": "15%", "vat": "12%", "excise": "нет / уточнить по модели", "util": "по ПКМ-347 зависит от объема и возраста", "source": "ПҚ-3818 + ПКМ-347"},
        "4011100000": {"code": "4011100000", "name_ru": "Шины новые резиновые для легковых автомобилей", "name_uz": "Yengil avtomobillar uchun yangi rezina shinalar", "category": "auto", "group": "cars", "position": "tires", "examples": ["шины", "автошины", "зимние шины"], "duty": "20%", "vat": "12%", "excise": "нет", "util": "может применяться по отдельным правилам", "source": "ПҚ-3818"}
    }

def load_db():
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            fixed = {}
            for k, v in data.items():
                key = "".join(ch for ch in str(k) if ch.isdigit())
                if not key:
                    continue
                item = dict(v) if isinstance(v, dict) else {"name_ru": str(v), "name_uz": str(v)}
                item.setdefault("code", key)
                item.setdefault("name_ru", item.get("name", key))
                item.setdefault("name_uz", item.get("name_ru", key))
                item.setdefault("category", "")
                item.setdefault("group", "")
                item.setdefault("position", "")
                item.setdefault("examples", [])
                item.setdefault("duty", "уточнить")
                item.setdefault("vat", "12%")
                item.setdefault("excise", "нет")
                item.setdefault("util", "нет")
                item.setdefault("source", "локальная база")
                fixed[key] = item
            if fixed:
                return fixed
    return seed_db()

PRODUCT_DB = load_db()

def t(lang, key):
    return TXT.get(lang, TXT["ru"]).get(key, key)

def normalize_code(value):
    return "".join(ch for ch in str(value) if ch.isdigit())

def normalize_text(value):
    return re.sub(r"\s+", " ", value.strip().lower())

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
    kb.add(t(lang, "broker"), t(lang, "specialist"))
    kb.add(t(lang, "change"))
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

def build_lang_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Русский", "O'zbekcha")
    return kb

def role_kb(lang):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "role_physical"), t(lang, "role_legal"))
    kb.add(t(lang, "role_broker"))
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
    return (
        f"{idx}) <b>{name}</b>\n"
        f"Код: <code>{item.get('code','')}</code>\n"
        f"Пошлина: {item.get('duty','уточнить')}\n"
        f"НДС: {item.get('vat','12%')}\n"
        f"Акциз: {item.get('excise','нет')}\n"
        f"♻️ Утильсбор: {item.get('util','нет')}\n"
        f"{t(lang, 'source')}: {item.get('source','локальная база')}\n"
    )

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
    for size in [8, 6, 4]:
        if len(code) >= size:
            part = code[:size]
            hits = [v for k, v in PRODUCT_DB.items() if normalize_code(k).startswith(part)]
            if hits:
                hits = sorted(hits, key=lambda x: len(normalize_code(x.get("code", ""))))
                return hits[:4]
    return []

def search_branch(query, category, group, position):
    q = normalize_text(query)
    if not q:
        return []
    strict, grp, cat, other = [], [], [], []
    for item in PRODUCT_DB.values():
        hay = " ".join([
            normalize_text(item.get("name_ru", "")),
            normalize_text(item.get("name_uz", "")),
            *[normalize_text(x) for x in item.get("examples", [])]
        ])
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
    if any(x in q for x in ["валют", "доллар", "tilla", "oltin"]):
        return "Для физлица по валюте действуют отдельные правила декларирования." if lang == "ru" else "Jismoniy shaxslar uchun valyuta bo‘yicha alohida deklaratsiya qoidalari bor."
    return t(lang, "physical_mode_no_calc")

async def send_main_for_role(message, state, lang, role):
    await state.update_data(role=role, lang=lang)
    if role == "physical":
        await message.answer(t(lang, "saved"), reply_markup=physical_menu(lang))
    elif role == "legal":
        await message.answer(t(lang, "saved") + "\n\n" + t(lang, "role_legal_ready"), reply_markup=legal_menu(lang))
    else:
        await message.answer(t(lang, "broker_intro"), reply_markup=broker_menu(lang))

@dp.message_handler(commands=["start"])
async def cmd_start(message, state):
    await state.finish()
    await Flow.choose_lang.set()
    await message.answer(TXT["ru"]["choose_lang"], reply_markup=build_lang_kb())

@dp.message_handler(state=Flow.choose_lang)
async def choose_lang(message, state):
    text = message.text.strip()
    if text == "Русский":
        lang = "ru"
    elif text == "O'zbekcha":
        lang = "uz"
    else:
        await message.answer(TXT["ru"]["choose_lang"], reply_markup=build_lang_kb())
        return
    await state.update_data(lang=lang)
    await Flow.choose_role.set()
    await message.answer(t(lang, "lang_saved") + "\n" + t(lang, "choose_role"), reply_markup=role_kb(lang))

@dp.message_handler(state=Flow.choose_role)
async def choose_role(message, state):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    text = message.text.strip()
    if text == t(lang, "role_physical"):
        await send_main_for_role(message, state, lang, "physical"); return
    if text == t(lang, "role_legal"):
        await send_main_for_role(message, state, lang, "legal"); return
    if text == t(lang, "role_broker"):
        await send_main_for_role(message, state, lang, "broker"); return
    await message.answer(t(lang, "choose_role"), reply_markup=role_kb(lang))

@dp.message_handler(lambda m: True)
async def router(message, state):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    role = data.get("role", "physical")
    text = message.text.strip()
    current = await state.get_state()

    if text == t(lang, "change"):
        await state.finish()
        await Flow.choose_lang.set()
        await message.answer(t(lang, "choose_lang"), reply_markup=build_lang_kb()); return

    if text == t(lang, "back_menu"):
        await send_main_for_role(message, state, lang, role); return

    if text == t(lang, "specialist"):
        await Flow.specialist_name.set()
        await message.answer(t(lang, "enter_name")); return

    if role == "physical":
        if text == t(lang, "faq"):
            await message.answer(t(lang, "faq_intro"), reply_markup=physical_menu(lang)); return
        if text == t(lang, "docs"):
            await message.answer(t(lang, "docs_physical"), reply_markup=physical_menu(lang)); return
        if text == t(lang, "chat"):
            await Flow.physical_chat.set()
            await message.answer(t(lang, "physical_chat_intro"), reply_markup=physical_menu(lang)); return
        if text in [t(lang, "tnved"), t(lang, "exact")]:
            await message.answer(t(lang, "no_code_in_physical"), reply_markup=physical_menu(lang)); return

    if role == "legal":
        if text == t(lang, "docs"):
            await message.answer(t(lang, "docs_legal"), reply_markup=legal_menu(lang)); return
        if text == t(lang, "faq"):
            await message.answer(t(lang, "faq_intro"), reply_markup=legal_menu(lang)); return
        if text == t(lang, "chat"):
            await Flow.legal_chat.set()
            await message.answer(t(lang, "legal_chat_intro"), reply_markup=legal_menu(lang)); return
        if text == t(lang, "exact"):
            await Flow.exact_code.set()
            await message.answer(t(lang, "enter_code"), reply_markup=legal_menu(lang)); return
        if text == t(lang, "tnved"):
            await Flow.legal_category.set()
            await message.answer(t(lang, "pick_category"), reply_markup=category_kb(lang)); return
        if text == t(lang, "broker"):
            await send_main_for_role(message, state, lang, "broker"); return

    if role == "broker":
        if text == t(lang, "broker_cost"):
            await Flow.broker_service.set()
            await message.answer(t(lang, "broker_pick"), reply_markup=broker_cost_menu(lang)); return

    if current == Flow.physical_chat.state:
        await message.answer(physical_answer(text, lang), reply_markup=physical_menu(lang)); return

    if current == Flow.legal_chat.state:
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

    if current == Flow.exact_code.state:
        results = find_by_code(text)
        if not results:
            await message.answer(t(lang, "nothing_found"), reply_markup=legal_menu(lang)); return
        out = f"<b>{t(lang, 'code_result')}</b>\n\n"
        for i, item in enumerate(results, 1):
            out += format_item(item, lang, i) + "\n"
        await message.answer(out, reply_markup=legal_menu(lang)); return

    if current == Flow.legal_category.state:
        found = find_ids_by_label(lang, text)
        if found and found[0] == "category":
            _, cat_id = found
            await state.update_data(category=cat_id)
            await Flow.legal_group.set()
            await message.answer(t(lang, "pick_group"), reply_markup=group_kb(lang, cat_id)); return
        await message.answer(t(lang, "pick_category"), reply_markup=category_kb(lang)); return

    if current == Flow.legal_group.state:
        cat_id = data.get("category")
        if text == t(lang, "back"):
            await Flow.legal_category.set()
            await message.answer(t(lang, "pick_category"), reply_markup=category_kb(lang)); return
        found = find_ids_by_label(lang, text)
        if found and found[0] == "group":
            _, found_cat, group_id = found
            if found_cat == cat_id:
                await state.update_data(group=group_id)
                await Flow.legal_position.set()
                await message.answer(t(lang, "pick_position"), reply_markup=position_kb(lang, cat_id, group_id)); return
        await message.answer(t(lang, "pick_group"), reply_markup=group_kb(lang, cat_id)); return

    if current == Flow.legal_position.state:
        cat_id = data.get("category")
        group_id = data.get("group")
        if text == t(lang, "back"):
            await Flow.legal_group.set()
            await message.answer(t(lang, "pick_group"), reply_markup=group_kb(lang, cat_id)); return
        found = find_ids_by_label(lang, text)
        if found and found[0] == "position":
            _, found_cat, found_group, position_id = found
            if found_cat == cat_id and found_group == group_id:
                await state.update_data(position=position_id)
                await Flow.legal_item.set()
                hint = TREE[cat_id]["groups"][group_id]["positions"][position_id]["hint"][lang]
                await message.answer(f"{t(lang, 'enter_item_in_branch')}\n\n{hint}", reply_markup=legal_menu(lang)); return
        await message.answer(t(lang, "pick_position"), reply_markup=position_kb(lang, cat_id, group_id)); return

    if current == Flow.legal_item.state:
        results = search_branch(text, data.get("category",""), data.get("group",""), data.get("position",""))
        if not results:
            await message.answer(t(lang, "nothing_found"), reply_markup=legal_menu(lang)); return
        out = f"<b>{t(lang, 'possible')}</b>\n\n"
        for i, item in enumerate(results, 1):
            out += format_item(item, lang, i) + "\n"
        out += t(lang, "branch_hint")
        await message.answer(out, reply_markup=legal_menu(lang)); return

    if current == Flow.specialist_name.state:
        await state.update_data(spec_name=text)
        await Flow.specialist_product.set()
        await message.answer(t(lang, "enter_product")); return

    if current == Flow.specialist_product.state:
        name = data.get("spec_name","")
        username = message.from_user.username or "-"
        msg = f"📩 <b>Новая заявка специалисту</b>\n\nИмя: {name}\nЗапрос: {text}\nРежим: {role}\nID: <code>{message.from_user.id}</code>\nUsername: @{username}"
        if ADMIN_CHAT_ID:
            try:
                await bot.send_message(ADMIN_CHAT_ID, msg)
            except Exception:
                pass
        await message.answer(t(lang, "application_sent"))
        await send_main_for_role(message, state, lang, role); return

    if current == Flow.broker_service.state:
        if text == t(lang, "broker_min_avg"):
            await state.update_data(broker_service=t(lang, "service_min_avg"))
            await Flow.broker_name.set()
            await message.answer(t(lang, "broker_paid") + "\n\n" + t(lang, "enter_name")); return
        if text == t(lang, "broker_3m"):
            await state.update_data(broker_service=t(lang, "service_3m"))
            await Flow.broker_name.set()
            await message.answer(t(lang, "broker_paid") + "\n\n" + t(lang, "enter_name")); return
        await message.answer(t(lang, "broker_pick"), reply_markup=broker_cost_menu(lang)); return

    if current == Flow.broker_name.state:
        await state.update_data(broker_name=text)
        await Flow.broker_product.set()
        await message.answer(t(lang, "enter_product")); return

    if current == Flow.broker_product.state:
        await state.update_data(broker_product=text)
        await Flow.broker_country.set()
        await message.answer(t(lang, "enter_country")); return

    if current == Flow.broker_country.state:
        await state.update_data(broker_country=text)
        await Flow.broker_comment.set()
        await message.answer(t(lang, "enter_comment")); return

    if current == Flow.broker_comment.state:
        msg = (
            "💼 <b>Новая PRO-заявка</b>\n\n"
            f"Услуга: {data.get('broker_service','')}\n"
            f"Имя: {data.get('broker_name','')}\n"
            f"Товар: {data.get('broker_product','')}\n"
            f"Страна: {data.get('broker_country','')}\n"
            f"Комментарий: {text}\n"
            f"ID: <code>{message.from_user.id}</code>\n"
            f"Username: @{message.from_user.username or '-'}"
        )
        if ADMIN_CHAT_ID:
            try:
                await bot.send_message(ADMIN_CHAT_ID, msg)
            except Exception:
                pass
        await message.answer(t(lang, "application_sent"))
        await send_main_for_role(message, state, lang, "broker"); return

    if role == "physical":
        await message.answer(t(lang, "physical_mode_no_calc"), reply_markup=physical_menu(lang))
    elif role == "legal":
        await message.answer(t(lang, "saved"), reply_markup=legal_menu(lang))
    else:
        await message.answer(t(lang, "broker_intro"), reply_markup=broker_menu(lang))

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
