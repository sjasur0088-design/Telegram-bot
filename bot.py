import asyncio
import logging
import os
from html import escape

from dotenv import load_dotenv
from openai import OpenAI
from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "").strip()
ADMIN_PHONE = os.getenv("ADMIN_PHONE", "+998901234567").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not found in .env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("physical_customs_bot")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

USER_LANG = {}
USER_ROLE = {}
USER_MODE = {}

REG_RULES_RU = """
Уважаемые пассажиры!

Если вы въезжаете на территорию Республики Узбекистан, помните о следующих таможенных правилах.

Через международные аэропорты можно ввозить товары без уплаты таможенных платежей до 2000 долларов США.
Через железнодорожные и речные пункты пропуска — до 1000 долларов США.
Через автодорожные и пешеходные пункты пропуска — до 300 долларов США.

Ограниченные нормы беспошлинного ввоза:
- алкоголь, в том числе пиво — до 2 литров;
- табачные изделия — до 10 пачек;
- духи и туалетная вода — до 3 единиц;
- ювелирные изделия — до 65 граммов.

Вывоз физическими лицами наличной валюты за пределы Узбекистана — не более эквивалента 100 миллионов сумов.

При превышении норм действует единый таможенный платеж: 30 процентов от таможенной стоимости, но не менее 3 долларов США за кг.

Для ряда товаров через автодорожные, пешеходные, железнодорожные и речные пункты пропуска действуют количественные нормы:
- телефонный аппарат — 1 единица в 6 календарных месяцев;
- ноутбук — 1 единица в 6 календарных месяцев;
- планшет — 1 единица в 6 календарных месяцев;
- телевизор — 1 единица в 6 календарных месяцев;
- холодильник — 1 единица в 6 календарных месяцев;
- стиральная машина — 1 единица в 6 календарных месяцев.

При ввозе лекарств важно учитывать состав, количество, назначение и возможные ограничения по отдельным веществам.
Если информации недостаточно или случай нестандартный, предложи обратиться к специалисту.
""".strip()

REG_RULES_UZ = """
Oʻzbekistonga kirishda jismoniy shaxslar uchun asosiy bojxona qoidalari:

- Xalqaro aeroportlar orqali bojsiz olib kirish meʼyori — 2000 AQSH dollarigacha.
- Temir yoʻl va daryo punktlari orqali — 1000 AQSH dollarigacha.
- Avtoyoʻl va piyoda punktlari orqali — 300 AQSH dollarigacha.

Alohida tovarlar uchun cheklovlar:
- alkogol mahsulotlari — 2 litrgacha;
- tamaki mahsulotlari — 10 qutigacha;
- atir va tualet suvi — 3 donagacha;
- zargarlik buyumlari — 65 grammgacha.

Jismoniy shaxslar Oʻzbekistondan naqd valyutani 100 million soʻm ekvivalentidan oshmagan summada olib chiqishlari mumkin.

Meʼyor oshsa, yagona bojxona toʻlovi qoʻllanadi:
bojxona qiymatining 30 foizi, lekin kamida 3 AQSH dollari/kg.

Ayrim texnika va buyumlar uchun miqdoriy meʼyorlar:
- telefon apparati — 6 kalendar oyda 1 dona;
- noutbuk — 6 kalendar oyda 1 dona;
- planshet — 6 kalendar oyda 1 dona;
- televizor — 6 kalendar oyda 1 dona;
- muzlatgich — 6 kalendar oyda 1 dona;
- kir yuvish mashinasi — 6 kalendar oyda 1 dona.

Dori vositalari bo‘yicha tarkib, miqdor, maqsad va cheklovlar hisobga olinadi.
Agar holat aniq bo‘lmasa, mutaxassisga murojaat qilishni tavsiya et.
""".strip()

BORDER_POSTS = [
  {
    "code": "101",
    "name": "Ислом Каримов номидаги \"Тошкент\" халқаро АЭРО чегара божхона пости",
    "address": "Тошкент шаҳар, Сирғали тумани, \"Ислом Каримов номидаги “Тошкент” халқаро аэропорти\" Терминал 2",
    "phone": "+99855 502-86-45"
  },
  {
    "code": "3002",
    "name": "\"Дўстлик\" чегара пости (Андижон)",
    "address": "Андижон вилояти, Хўжаобод тумани, “Манак” ҚФЙ “Дўстлик” МФЙ",
    "phone": "998952014328, 998742247615 (6502,6503)"
  },
  {
    "code": "3003",
    "name": "\"Андижан АЭРОи\"",
    "address": "Андижон шаҳар, Янги айланма кўчаси, 1 уй",
    "phone": "998742247615 (6530,6531,6572,6573)"
  },
  {
    "code": "3009",
    "name": "\"Маданият\" чегара пости",
    "address": "Андижон вилояти, Пахтаобод тумани, Маданият ҚФЙ Тошқўрғон МФЙ",
    "phone": "998742247615 (6550,6551,6552,6554)"
  },
  {
    "code": "3014",
    "name": "\"Савай\" темир йўл чегара пости",
    "address": "Андижон вилояти, Қўрғонтепа тумани, Устоз МФЙ, Бирлик кўча 1 уй",
    "phone": "998742247615 (6540,6541,6542,6543)"
  },
  {
    "code": "6001",
    "name": "\"Бухоро АЭРОи\"",
    "address": "Бухоро вилояти, Бухоро шаҳри, Б.Нақшбанд кўчаси, 251-уй",
    "phone": "998 65 228 91 15"
  },
  {
    "code": "6010",
    "name": "\"Олот\" чегара пости",
    "address": "Бухоро вилояти, Олот тумани, Союн Қоровул МФЙ, Олот чегара божхона пости",
    "phone": "998 65 221 63 23"
  },
  {
    "code": "6011",
    "name": "\"Хўжадавлат\" темир йўл чегара пости",
    "address": "Бухоро вилояти, Олот тумани, Союн қоровул МФЙ, Хўжадавлат темир йўл станцияси",
    "phone": "998 95 600 14 31"
  },
  {
    "code": "8003",
    "name": "\"Учтўрғон\" чегара пости",
    "address": "Жиззах вилояти, Янгиобод тумани, Учтўрғон ахоли пункти, Тошкент-Душанбе М-34 магистрал йўли",
    "phone": ""
  },
  {
    "code": "8007",
    "name": "\"Қўшкент\" чегара пости",
    "address": "Жиззах вилояти, Янгиобод тумани, Қўшкент ахоли пункти, Тошкент-Душанбе М-34 магистрал йўли",
    "phone": ""
  },
  {
    "code": "10008",
    "name": "\"Қарши-Керки\" чегара пости",
    "address": "Қашқадарё вилояти Нишон тумани",
    "phone": "998752211418(8533)"
  },
  {
    "code": "10012",
    "name": "\"Қарши АЭРОи\"",
    "address": "Қашқадарё вилояти Қарши шахар Буюк турон кўчаси 3 уй",
    "phone": ""
  },
  {
    "code": "12002",
    "name": "\"Навоий АЭРОи\"",
    "address": "Навоий вилояти, Кармана тумани, Сардоба маҳалласи, \"Навоий халқаро аэропорти\" МЧЖ ҳудуди",
    "phone": "+998(78)-770-32-52"
  },
  {
    "code": "14002",
    "name": "\"Наманган АЭРОи\"",
    "address": "Namangan viloyati, Namangan shahri, Namangan aeroporti",
    "phone": ""
  },
  {
    "code": "14003",
    "name": "\"Учқўрғон\" чегара пости",
    "address": "Namangan viloyati, Uchqo`rg`on tumani, Yangiyer QFY, Bo`ston MFY",
    "phone": ""
  },
  {
    "code": "14004",
    "name": "\"Косонсой\" чегара пости",
    "address": "Namangan viloyati, Kosonsoy tumani, Obod MFY",
    "phone": ""
  },
  {
    "code": "14005",
    "name": "\"Поп\" чегара пости",
    "address": "Namangan viloyati, Pop tumani, Pungon qishlog`I",
    "phone": ""
  },
  {
    "code": "18001",
    "name": "\"Самарқанд АЭРОи\"",
    "address": "Самарқанд вилояти, Самарқанд шаҳри Ибн Сино кўчаси 1-уй",
    "phone": ""
  },
  {
    "code": "18002",
    "name": "\"Жартепа\" чегара пости",
    "address": "Самарқанд вилояти, Ургут тумани Жартепа қишлоғи",
    "phone": "-"
  },
  {
    "code": "22002",
    "name": "\"Термиз АЭРОи\"",
    "address": "Сурхондарё вилояти, Термиз тумани, “Дўстлик” жамоа хужалиги",
    "phone": ""
  },
  {
    "code": "22003",
    "name": "\"Сариосиё\" чегара пости",
    "address": "Сурхондарё вилояти, Сариосиё тумани \"Суфиён\" ж/х, \"Чумчукли жар\" поселкаси",
    "phone": ""
  },
  {
    "code": "22004",
    "name": "\"Сариосиё\" темир йўл чегара пости",
    "address": "Сурхондарё вилояти, Узун тумани, Хатиб Қахрамон МФЙ Қўрғон қишлоғи",
    "phone": ""
  },
  {
    "code": "22007",
    "name": "\"Гулбаҳор\" чегара пости",
    "address": "Сурхондарё вилояти, Термиз тумани Гулбаҳор махалласи",
    "phone": ""
  },
  {
    "code": "22011",
    "name": "\"Дарё порти\" божхона пости",
    "address": "Сурхондарё вилояти, Термиз шахри, С.Термизий кучаси 58 уй",
    "phone": ""
  },
  {
    "code": "22015",
    "name": "\"Болдир\" темир йўл чегара пости",
    "address": "Сурхондарё вилояти Музрабод тумани, Чегарачи МФЙ Қоракамар қишлоги",
    "phone": ""
  },
  {
    "code": "22017",
    "name": "\"Айритом\" чегара пости",
    "address": "Сурхондарё вилояти, Термиз тумани, “Янгиарик” СФУ",
    "phone": ""
  },
  {
    "code": "24002",
    "name": "\"Ховостобод\" чегара пости",
    "address": "Сирдарё вилояти, Ховос тумани, Ховос қўрғони Карвонсарой маҳалласи",
    "phone": "ички номер (6799)"
  },
  {
    "code": "24004",
    "name": "\"Сирдарё\" чегара пости",
    "address": "Сирдарё вилояти, Сирдарё тумани, Синдоробод СИУ, Қуёш махалласи, Р-35 “Сирдарё-Илъич” автойўлининг 12-км.да",
    "phone": "ички номер (6757; 6785;6795; 6786)"
  },
  {
    "code": "26009",
    "name": "\"Келес\" темир йўл чегара пости",
    "address": "Тошкент вилояти, Тошкент тумани, Оқибат кўчаси 12-уй",
    "phone": ""
  },
  {
    "code": "26013",
    "name": "\"Чуқурсой техник идораси\" темир йўл чегара пости",
    "address": "Тошкент шаҳри, Олмазор тумани, Чуқурсой кўчаси, 82 уй",
    "phone": "71-207-09-56"
  },
  {
    "code": "27001",
    "name": "\"Яллама\" чегара пости",
    "address": "Тошкент вилояти, Чиноз тумани, Яллама қишлоғи",
    "phone": "99871-202-02-72"
  },
  {
    "code": "27008",
    "name": "\"Навоий\" чегара пости",
    "address": "Тошкент вилояти, Тошкент тумани, Чувалачи ҚФЙ, “Гултепа” МФЙ",
    "phone": "99871-202-02-76"
  },
  {
    "code": "27009",
    "name": "\"С. Нажимов\" чегара пости",
    "address": "Тошкент вилояти, Қибрай тумани, Май қишлоғи Туркистон ҚФЙ",
    "phone": "99871-202-02-81"
  },
  {
    "code": "27011",
    "name": "\"Ойбек\" чегара пости",
    "address": "Тошкент вилояти, Бекобод тумани, Ойбек ж/х",
    "phone": "99871-202-02-83"
  },
  {
    "code": "27013",
    "name": "\"Бекобод авто\" чегара пости",
    "address": "Тошкент вилояти, Бекобод тумани",
    "phone": "99871-202-02-74"
  },
  {
    "code": "27021",
    "name": "\"Ғишткўприк\" чегара пости",
    "address": "Тошкент вилояти, Тошкент тумани Ғишткўприк махалласи, Чимкент йўли кўчаси",
    "phone": "99878-120-86-06"
  },
  {
    "code": "27023",
    "name": "\"Фарход\" чегара пости",
    "address": "Тошкент вилояти, Бекобод шаҳри, Сохил йўли, Низомий кўчаси",
    "phone": "99871-202-02-74"
  },
  {
    "code": "27024",
    "name": "\"Бекобод\" темир йўл чегара пости",
    "address": "Тошкент вилояти, Бекобод шаҳри, Бекобод темир йўл станцияси",
    "phone": "99870-214-65-79"
  },
  {
    "code": "27029",
    "name": "\"Ўзбекистон\" темир йўл чегара пости",
    "address": "Тошкент вилояти, Янгийўл тумани, Ўзбекистон темир йўл станцияси",
    "phone": ""
  },
  {
    "code": "30001",
    "name": "\"Фарғона\" чегара пости",
    "address": "Фарғона вилояти, Фарғона шаҳар, Аэропорт кўчаси 16-уй",
    "phone": ""
  },
  {
    "code": "30004",
    "name": "\"Фарғона\" чегара пости",
    "address": "Фарғона вилояти, Фарғона тумани, Юқори Водил қишлоғи, Яхши Ният кўчаси",
    "phone": ""
  },
  {
    "code": "30005",
    "name": "\"Андархон\" чегара пости",
    "address": "Фарғона вилояти, Бешариқ тумани, Андархон қишлоғи",
    "phone": ""
  },
  {
    "code": "30006",
    "name": "\"Риштон\" чегара пости",
    "address": "Фарғона вилояти, Риштон тумани, Риштон шахри, Хўжа Илғор МФЙ, Фарғона кўчаси",
    "phone": ""
  },
  {
    "code": "30008",
    "name": "\"Ровот\" чегара пости",
    "address": "Фарғона вилояти Бешариқ тумани Қашқар ҚФЙ, Воррух қишлоғи",
    "phone": ""
  },
  {
    "code": "30010",
    "name": "\"Ўзбекистон\" чегара пости",
    "address": "Фарғона вилояти, Қувасой шаҳар, Носиробод қишлоғи, Ўзбекистон кўчаси",
    "phone": ""
  },
  {
    "code": "30012",
    "name": "\"Сўх\" чегара пости",
    "address": "Фарғона вилояти, Сўх тумани, Ровон шаҳарчаси, Амир Темур кўчаси, 4Р-149 рақамли автойўлда",
    "phone": ""
  },
  {
    "code": "33001",
    "name": "\"Шовот\" чегара пости",
    "address": "Хоразм вилояти, Шовот тумани, Ўзбекистон қишлоғи, Махтумқули маҳалласи",
    "phone": ""
  },
  {
    "code": "33004",
    "name": "\"Дўстлик\" чегара пости (Хоразм)",
    "address": "Хоразм вилояти, Тупроққалъа тумани, Питнак шаҳри, Питнак қишлоғи, Охунбобоев маҳалласи",
    "phone": ""
  },
  {
    "code": "33011",
    "name": "\"Урганч АЭРОи\"",
    "address": "Хоразм вилояти, Урганч шаҳри, Урганч халқаро аэропорти",
    "phone": ""
  },
  {
    "code": "35001",
    "name": "\"Нукус АЭРОи\"",
    "address": "Нукус шаҳри, А.Досназаров кўчаси",
    "phone": "998 (61) 224-90-84"
  },
  {
    "code": "35003",
    "name": "\"Хожайли\" чегара пости",
    "address": "Хўжайли тумани, “Ходжейли-Куня Ургенч” авто йўли",
    "phone": "998 (61) 224-90-85"
  },
  {
    "code": "35004",
    "name": "\"Даут-ата\" чегара пости",
    "address": "Қўнғирот тумани, А-380 “Гузар-Бухара-Нукус-Бейнеу” автомагистралининг 1204 км",
    "phone": "998 (61) 224-90-82"
  },
  {
    "code": "35010",
    "name": "\"Қорақалпоғистон\" темир йўл чегара пости",
    "address": "Қўнғирот тумани, “Қорақалпоғистон” поселкаси, “ Қорақалпоғистон ” темир йўл станцияси",
    "phone": "998 (61) 224-90-83"
  },
  {
    "code": "3007",
    "name": "\"Хонобод\" чегара пости",
    "address": "Андижон вилояти, Хонобод тумани,“Навоий” МФЙ",
    "phone": "998952014328, 998742247615 (6410,6441)"
  },
  {
    "code": "3005",
    "name": "\"Мингтепа\" чегара пости",
    "address": "Андижон вилояти, Мархамат тумани, “Қорабоғич” ҚФЙ “Дўстлик” МФЙ",
    "phone": "998952014328, 998742247615 (6410,6441)"
  },
  {
    "code": "3006",
    "name": "Қорасув чегара пости",
    "address": "Андижон вилояти, Қўрғонтепа тумани, Қорасув шаҳар",
    "phone": ""
  },
  {
    "code": "3008",
    "name": "\"Пушмон\" чегара пости",
    "address": "Андижон вилояти, Пахтабод тумани Уйғур ҚФЙ, Пушмон махалла",
    "phone": ""
  },
  {
    "code": "3013",
    "name": "Кесканёр чегара пости",
    "address": "Андижон вилояти, Қўрғонтепа тумани, Султонобод қишлоғи",
    "phone": ""
  },
  {
    "code": "24014",
    "name": "\"Малик\" чегара пости",
    "address": "Сирдарё вилояти, Сирдарё тумани, Пахтакор СИУ, М39 автойўлининг 888 км.да",
    "phone": "ички номер (6782; 6783)"
  },
  {
    "code": "24006",
    "name": "\"Оқ олтин\" чегара пости",
    "address": "Сирдарё вилояти, Оқ олтин тумани, Сардоба қўрғони, М39 автойўлининг 912 км.да",
    "phone": "ички номер (6793; 6779; 6784)"
  },
  {
    "code": "110",
    "name": "\"Тошкент-Ҳумо аэропорти\" чегара пости",
    "address": "Тошкент шаҳар, Яшнобод тумани, \"Тошкент-хумо\" халқаро аэропорти",
    "phone": "+99855 502-86-30"
  },
  {
    "code": "33033",
    "name": "\"Шовот чегараолди савдо зонаси\" чегара пости",
    "address": "Хоразм вилояти, Шовот тумани, Ўзбекистон қишлоғи, Махтумқули маҳалласи",
    "phone": "+99862 227-70-11"
  }
]

def get_lang(user_id: int) -> str:
    return USER_LANG.get(user_id, "ru")

def tr(user_id: int, ru: str, uz: str) -> str:
    return uz if get_lang(user_id) == "uz" else ru

def set_mode(user_id: int, mode: str) -> None:
    USER_MODE[user_id] = mode

def get_mode(user_id: int) -> str:
    return USER_MODE.get(user_id, "general")

def clear_mode(user_id: int) -> None:
    USER_MODE[user_id] = "general"

def set_role(user_id: int, role: str) -> None:
    USER_ROLE[user_id] = role

def get_role(user_id: int) -> str:
    return USER_ROLE.get(user_id, "general")

def admin_chat_id_int():
    try:
        return int(ADMIN_CHAT_ID)
    except Exception:
        return None

def support_footer(user_id: int) -> str:
    return (
        "

👨‍💼 <b>" + tr(user_id, "Специалист", "Mutaxassis") + ":</b> <code>" + escape(ADMIN_PHONE) + "</code>
" +
        tr(user_id, "Специалист отвечает бесплатно в течение дня.", "Mutaxassis kun davomida bepul javob beradi.")
    )

class SpecialistState(StatesGroup):
    waiting_name = State()
    waiting_question = State()

lang_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🇷🇺 Русский"), KeyboardButton(text="🇺🇿 O‘zbekcha")]
    ],
    resize_keyboard=True,
)

role_kb_ru = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👤 Для физ лиц")],
        [KeyboardButton(text="🏢 Для юр лиц"), KeyboardButton(text="👨‍💼 Для брокеров (PRO)")],
    ],
    resize_keyboard=True,
)

role_kb_uz = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👤 Jismoniy shaxslar uchun")],
        [KeyboardButton(text="🏢 Yuridik shaxslar uchun"), KeyboardButton(text="👨‍💼 Brokerlar uchun (PRO)")],
    ],
    resize_keyboard=True,
)

physical_menu_kb_ru = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🤖 AI таможенник")],
        [KeyboardButton(text="🏢 Список таможенных постов")],
        [KeyboardButton(text="👨‍💼 Специалист")],
        [KeyboardButton(text="🌐 Сменить язык / роль")],
    ],
    resize_keyboard=True,
)

physical_menu_kb_uz = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🤖 AI bojxonachi")],
        [KeyboardButton(text="🏢 Bojxona postlari ro‘yxati")],
        [KeyboardButton(text="👨‍💼 Mutaxassis")],
        [KeyboardButton(text="🌐 Til / rolni almashtirish")],
    ],
    resize_keyboard=True,
)

ai_menu_kb_ru = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Готовые вопросы"), KeyboardButton(text="✍️ Свой вопрос")],
        [KeyboardButton(text="⬅️ Назад")],
    ],
    resize_keyboard=True,
)

ai_menu_kb_uz = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Tayyor savollar"), KeyboardButton(text="✍️ O‘z savolingiz")],
        [KeyboardButton(text="⬅️ Orqaga")],
    ],
    resize_keyboard=True,
)

physical_faq_kb_ru = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Таможенные правила для физлиц")],
        [KeyboardButton(text="Сколько можно ввозить без пошлины")],
        [KeyboardButton(text="Сколько телефонов можно привезти")],
        [KeyboardButton(text="Можно ли ввозить лекарства")],
        [KeyboardButton(text="Сколько можно вывозить валюты")],
        [KeyboardButton(text="Что будет при превышении нормы")],
        [KeyboardButton(text="⬅️ Назад")],
    ],
    resize_keyboard=True,
)

physical_faq_kb_uz = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Jismoniy shaxslar uchun bojxona qoidalari")],
        [KeyboardButton(text="Bojsiz qancha olib kirish mumkin")],
        [KeyboardButton(text="Nechta telefon olib kirish mumkin")],
        [KeyboardButton(text="Dori olib kirish mumkinmi")],
        [KeyboardButton(text="Qancha valyuta olib chiqish mumkin")],
        [KeyboardButton(text="Norma oshsa nima bo‘ladi")],
        [KeyboardButton(text="⬅️ Orqaga")],
    ],
    resize_keyboard=True,
)

posts_menu_kb_ru = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚧 Приграничные посты")],
        [KeyboardButton(text="📦 ВЭД посты")],
        [KeyboardButton(text="⬅️ Назад")],
    ],
    resize_keyboard=True,
)

posts_menu_kb_uz = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚧 Chegara postlari")],
        [KeyboardButton(text="📦 VED postlari")],
        [KeyboardButton(text="⬅️ Orqaga")],
    ],
    resize_keyboard=True,
)

def role_kb(user_id: int):
    return role_kb_uz if get_lang(user_id) == "uz" else role_kb_ru

def physical_menu_kb(user_id: int):
    return physical_menu_kb_uz if get_lang(user_id) == "uz" else physical_menu_kb_ru

def ai_menu_kb(user_id: int):
    return ai_menu_kb_uz if get_lang(user_id) == "uz" else ai_menu_kb_ru

def physical_faq_kb(user_id: int):
    return physical_faq_kb_uz if get_lang(user_id) == "uz" else physical_faq_kb_ru

def posts_menu_kb(user_id: int):
    return posts_menu_kb_uz if get_lang(user_id) == "uz" else posts_menu_kb_ru

PHYSICAL_FAQ_BY_BUTTON = {
    "Таможенные правила для физлиц": "Для физических лиц при въезде в Узбекистан действуют предельные нормы беспошлинного ввоза: через международные аэропорты — до 2000 USD, через железнодорожные и речные пункты — до 1000 USD, через автодорожные и пешеходные пункты — до 300 USD.",
    "Сколько можно ввозить без пошлины": "Без уплаты таможенных платежей можно ввозить товары в пределах нормы: до 2000 USD через аэропорты, до 1000 USD через железнодорожные и речные пункты и до 300 USD через автодорожные и пешеходные пункты.",
    "Сколько телефонов можно привезти": "Для физических лиц телефонный аппарат обычно рассматривается в количестве 1 единица в 6 календарных месяцев через автодорожные, пешеходные, железнодорожные и речные пункты. Если количество больше, возможна оценка как коммерческого ввоза.",
    "Можно ли ввозить лекарства": "Лекарства можно ввозить, но важно учитывать состав, количество, назначение и возможные ограничения по отдельным веществам. Для точного ответа лучше указать название препарата и количество.",
    "Сколько можно вывозить валюты": "Физические лица могут вывозить наличную валюту за пределы Узбекистана в сумме, не превышающей эквивалент 100 миллионов сумов.",
    "Что будет при превышении нормы": "Если норма беспошлинного ввоза превышена, применяется единый таможенный платеж: 30 процентов от таможенной стоимости, но не менее 3 долларов США за кг, в части превышения нормы.",
    "Jismoniy shaxslar uchun bojxona qoidalari": "Jismoniy shaxslar uchun O‘zbekistonga kirishda bojsiz olib kirish me’yorlari: aeroportlar orqali 2000 USDgacha, temir yo‘l va daryo punktlari orqali 1000 USDgacha, avtoyo‘l va piyoda punktlari orqali 300 USDgacha.",
    "Bojsiz qancha olib kirish mumkin": "Bojsiz olib kirish me’yori: aeroportlar orqali 2000 USDgacha, temir yo‘l va daryo punktlari orqali 1000 USDgacha, avtoyo‘l va piyoda punktlari orqali 300 USDgacha.",
    "Nechta telefon olib kirish mumkin": "Jismoniy shaxslar uchun telefon apparati odatda 6 kalendar oyda 1 dona miqdoriy norma bilan qo‘llanadi. Ko‘p bo‘lsa, bu tijorat importi deb baholanishi mumkin.",
    "Dori olib kirish mumkinmi": "Dorilarni olib kirish mumkin, lekin tarkibi, miqdori, maqsadi va ayrim moddalarga cheklovlar hisobga olinadi. Aniq javob uchun dori nomi va miqdorini yozing.",
    "Qancha valyuta olib chiqish mumkin": "Jismoniy shaxslar O‘zbekistondan naqd valyutani 100 million so‘m ekvivalentidan oshmagan summada olib chiqishlari mumkin.",
    "Norma oshsa nima bo‘ladi": "Agar bojsiz norma oshsa, oshgan qism uchun yagona bojxona to‘lovi qo‘llanadi: bojxona qiymatining 30 foizi, lekin kamida 3 USD/kg.",
}

def chunk_posts(posts, size=10):
    for i in range(0, len(posts), size):
        yield posts[i:i+size]

def format_posts(posts, user_id):
    parts = []
    for i, p in enumerate(posts, start=1):
        parts.append(f"<b>{i})</b> {escape(p['name'])}")
        parts.append(f"• {tr(user_id, 'Код', 'Kodi')}: <code>{escape(p['code'])}</code>")
        if p['address']:
            parts.append(f"• {tr(user_id, 'Адрес', 'Manzil')}: {escape(p['address'])}")
        if p['phone']:
            parts.append(f"• {tr(user_id, 'Телефон', 'Telefon')}: {escape(p['phone'])}")
        parts.append("")
    return "
".join(parts).strip()

async def ai_customs_answer(user_id: int, question: str) -> str:
    if not client:
        return (
            tr(
                user_id,
                "Сейчас AI временно недоступен. Обратитесь к специалисту.",
                "Hozircha AI vaqtincha ishlamayapti. Mutaxassisga murojaat qiling."
            ) + support_footer(user_id)
        )

    rules = REG_RULES_UZ if get_lang(user_id) == "uz" else REG_RULES_RU

    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=OPENAI_MODEL,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты консультант по таможенным правилам Узбекистана для физических лиц. "
                        "Отвечай только на вопросы по таможне. "
                        "Сначала опирайся на эти правила:

" + rules + "

"
                        "Если информации в правилах недостаточно, честно скажи, что нужна дополнительная проверка. "
                        "Не придумывай законов и норм. "
                        "Всегда в конце предложи помощь специалиста."
                    ),
                },
                {"role": "user", "content": question},
            ],
        )
        answer = (response.choices[0].message.content or "").strip()
        if not answer:
            answer = tr(user_id, "Не удалось получить ответ.", "Javobni olishning iloji bo‘lmadi.")
        if "специалист" not in answer.lower() and "mutaxassis" not in answer.lower():
            answer += support_footer(user_id)
        return answer
    except Exception as e:
        logger.warning("AI answer failed: %s", e)
        return (
            tr(
                user_id,
                "Произошла ошибка. Обратитесь к специалисту.",
                "Xatolik yuz berdi. Mutaxassisga murojaat qiling."
            ) + support_footer(user_id)
        )

async def send_admin_text(text: str) -> None:
    chat_id = admin_chat_id_int()
    if not chat_id:
        return
    try:
        await bot.send_message(chat_id, text)
    except Exception as e:
        logger.warning("Admin send failed: %s", e)

@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    clear_mode(message.from_user.id)
    set_role(message.from_user.id, "general")
    await message.answer("Выберите язык / Tilni tanlang", reply_markup=lang_kb)

@router.message(F.text == "🇷🇺 Русский")
async def set_ru(message: Message):
    USER_LANG[message.from_user.id] = "ru"
    await message.answer("Выберите роль:", reply_markup=role_kb(message.from_user.id))

@router.message(F.text == "🇺🇿 O‘zbekcha")
async def set_uz(message: Message):
    USER_LANG[message.from_user.id] = "uz"
    await message.answer("Rolni tanlang:", reply_markup=role_kb(message.from_user.id))

@router.message(F.text.in_(('👤 Для физ лиц', '👤 Jismoniy shaxslar uchun')))
async def physical_menu(message: Message, state: FSMContext):
    await state.clear()
    clear_mode(message.from_user.id)
    set_role(message.from_user.id, "physical")
    await message.answer(
        tr(
            message.from_user.id,
            "Для физических лиц доступно 3 раздела:",
            "Jismoniy shaxslar uchun 3 ta bo‘lim mavjud:"
        ),
        reply_markup=physical_menu_kb(message.from_user.id),
    )

@router.message(F.text.in_(('🏢 Для юр лиц', '🏢 Yuridik shaxslar uchun')))
async def legal_placeholder(message: Message):
    set_role(message.from_user.id, "legal")
    clear_mode(message.from_user.id)
    await message.answer(
        tr(
            message.from_user.id,
            "Раздел для юр лиц не изменялся в этой тестовой версии.",
            "Yuridik shaxslar bo‘limi bu test versiyada o‘zgartirilmagan."
        ),
        reply_markup=role_kb(message.from_user.id),
    )

@router.message(F.text.in_(('👨\u200d💼 Для брокеров (PRO)', '👨\u200d💼 Brokerlar uchun (PRO)')))
async def broker_placeholder(message: Message):
    set_role(message.from_user.id, "broker")
    clear_mode(message.from_user.id)
    await message.answer(
        tr(
            message.from_user.id,
            "Раздел для брокеров не изменялся в этой тестовой версии.",
            "Brokerlar bo‘limi bu test versiyada o‘zgartirilmagan."
        ),
        reply_markup=role_kb(message.from_user.id),
    )

@router.message(F.text.in_(('🤖 AI таможенник', '🤖 AI bojxonachi')))
async def physical_ai_entry(message: Message):
    set_mode(message.from_user.id, "physical_ai_menu")
    text = tr(
        message.from_user.id,
        "🤖 <b>AI таможенник</b>

Быстрые ответы 24/7 по вопросам таможни для физических лиц в Узбекистане.
Выберите формат:",
        "🤖 <b>AI bojxonachi</b>

O‘zbekistonda jismoniy shaxslar uchun bojxona savollariga tezkor javob, 24/7.
Formatni tanlang:"
    )
    await message.answer(text, reply_markup=ai_menu_kb(message.from_user.id))

@router.message(F.text.in_(('📋 Готовые вопросы', '📋 Tayyor savollar')))
async def physical_ready_questions(message: Message):
    set_mode(message.from_user.id, "physical_faq")
    await message.answer(
        tr(message.from_user.id, "Выберите готовый вопрос:", "Tayyor savolni tanlang:"),
        reply_markup=physical_faq_kb(message.from_user.id),
    )

@router.message(F.text.in_(('✍️ Свой вопрос', '✍️ O‘z savolingiz')))
async def physical_own_question(message: Message):
    set_mode(message.from_user.id, "physical_ai")
    await message.answer(
        tr(
            message.from_user.id,
            "Напишите ваш вопрос по таможне для физических лиц.",
            "Jismoniy shaxslar uchun bojxona bo‘yicha savolingizni yozing."
        ),
        reply_markup=physical_menu_kb(message.from_user.id),
    )

@router.message(F.text.in_(set(PHYSICAL_FAQ_BY_BUTTON.keys())))
async def physical_faq_answers(message: Message):
    answer = PHYSICAL_FAQ_BY_BUTTON.get(message.text or "")
    if answer:
        set_mode(message.from_user.id, "physical_ai")
        await message.answer(answer + support_footer(message.from_user.id), reply_markup=physical_faq_kb(message.from_user.id))

@router.message(F.text.in_(('🏢 Список таможенных постов', '🏢 Bojxona postlari ro‘yxati')))
async def posts_entry(message: Message):
    set_mode(message.from_user.id, "posts_menu")
    await message.answer(
        tr(message.from_user.id, "Выберите тип постов:", "Post turini tanlang:"),
        reply_markup=posts_menu_kb(message.from_user.id),
    )

@router.message(F.text.in_(('🚧 Приграничные посты', '🚧 Chegara postlari')))
async def border_posts_handler(message: Message):
    header = tr(message.from_user.id, "🚧 <b>Приграничные посты</b>", "🚧 <b>Chegara postlari</b>")
    chunks = list(chunk_posts(BORDER_POSTS, size=12))
    await message.answer(header, reply_markup=posts_menu_kb(message.from_user.id))
    for chunk in chunks[:3]:
        await message.answer(format_posts(chunk, message.from_user.id), reply_markup=posts_menu_kb(message.from_user.id))

@router.message(F.text.in_(('📦 ВЭД посты', '📦 VED postlari')))
async def ved_posts_handler(message: Message):
    await message.answer(
        tr(
            message.from_user.id,
            "📦 Список ВЭД постов будет подключён следующим шагом отдельным источником.",
            "📦 VED postlari ro‘yxati keyingi bosqichda alohida manba orqali ulanadi."
        ) + support_footer(message.from_user.id),
        reply_markup=posts_menu_kb(message.from_user.id),
    )

@router.message(F.text.in_(('👨\u200d💼 Специалист', '👨\u200d💼 Mutaxassis')))
async def specialist_start(message: Message, state: FSMContext):
    await state.clear()
    set_mode(message.from_user.id, "specialist")
    await state.set_state(SpecialistState.waiting_name)
    await message.answer(
        tr(
            message.from_user.id,
            "Введите ваше имя. Специалист ответит бесплатно в течение дня.",
            "Ismingizni kiriting. Mutaxassis sizga kun davomida bepul javob beradi."
        ),
        reply_markup=physical_menu_kb(message.from_user.id) if get_role(message.from_user.id) == "physical" else role_kb(message.from_user.id),
    )

@router.message(SpecialistState.waiting_name)
async def specialist_name(message: Message, state: FSMContext):
    await state.update_data(name=(message.text or "").strip())
    await state.set_state(SpecialistState.waiting_question)
    await message.answer(
        tr(message.from_user.id, "Напишите ваш вопрос:", "Savolingizni yozing:"),
        reply_markup=physical_menu_kb(message.from_user.id) if get_role(message.from_user.id) == "physical" else role_kb(message.from_user.id),
    )

@router.message(SpecialistState.waiting_question)
async def specialist_question(message: Message, state: FSMContext):
    data = await state.get_data()
    username = f"@{message.from_user.username}" if message.from_user.username else "нет"

    await send_admin_text(
        f"📩 Новая заявка
"
        f"Роль: {get_role(message.from_user.id)}
"
        f"Имя: {data.get('name', '—')}
"
        f"Вопрос: {message.text or '—'}
"
        f"ID: {message.from_user.id}
"
        f"Username: {username}"
    )

    await message.answer(
        tr(
            message.from_user.id,
            "✅ Заявка отправлена специалисту.",
            "✅ So‘rov mutaxassisga yuborildi."
        ),
        reply_markup=physical_menu_kb(message.from_user.id) if get_role(message.from_user.id) == "physical" else role_kb(message.from_user.id),
    )
    await state.clear()
    clear_mode(message.from_user.id)

@router.message(F.text.in_(('🌐 Сменить язык / роль', '🌐 Til / rolni almashtirish')))
async def change_lang_role(message: Message, state: FSMContext):
    await state.clear()
    clear_mode(message.from_user.id)
    set_role(message.from_user.id, "general")
    await message.answer("Выберите язык / Tilni tanlang", reply_markup=lang_kb)

@router.message(F.text.in_(('⬅️ Назад', '⬅️ Orqaga')))
async def back_handler(message: Message, state: FSMContext):
    await state.clear()
    role = get_role(message.from_user.id)
    mode = get_mode(message.from_user.id)

    if role == "physical":
        if mode in ["physical_faq"]:
            set_mode(message.from_user.id, "physical_ai_menu")
            await message.answer(tr(message.from_user.id, "Назад в AI таможенник", "AI bojxonachi bo‘limiga qaytish"), reply_markup=ai_menu_kb(message.from_user.id))
            return
        set_mode(message.from_user.id, "general")
        await message.answer(tr(message.from_user.id, "Меню для физ лиц", "Jismoniy shaxslar menyusi"), reply_markup=physical_menu_kb(message.from_user.id))
        return

    await message.answer(tr(message.from_user.id, "Выберите роль:", "Rolni tanlang:"), reply_markup=role_kb(message.from_user.id))

@router.message()
async def universal_handler(message: Message, state: FSMContext):
    if await state.get_state():
        return

    text = (message.text or "").strip()
    if not text:
        return

    role = get_role(message.from_user.id)
    mode = get_mode(message.from_user.id)

    if role == "physical" and mode in ["physical_ai", "physical_ai_menu", "physical_faq"]:
        answer = await ai_customs_answer(message.from_user.id, text)
        await message.answer(answer, reply_markup=physical_menu_kb(message.from_user.id))
        return

    await message.answer(
        tr(
            message.from_user.id,
            "Выберите раздел из меню.",
            "Menyudan bo‘limni tanlang."
        ),
        reply_markup=physical_menu_kb(message.from_user.id) if role == "physical" else role_kb(message.from_user.id),
    )

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
