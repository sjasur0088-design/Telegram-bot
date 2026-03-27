import os, re, json, logging, sqlite3
from datetime import datetime
from typing import Dict
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")
PRODUCT_DB_PATH = os.getenv("PRODUCT_DB_PATH", "product_db_500_plus.json")
ANALYTICS_DB_PATH = os.getenv("ANALYTICS_DB_PATH", "analytics.db")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())
client = OpenAI(api_key=OPENAI_API_KEY) if (OPENAI_API_KEY and OpenAI) else None

TXT = {
"ru":{"choose_lang":"Выберите язык:","choose_role":"Выберите режим:","lang_saved":"Язык сохранён.","saved":"Готово. Выберите раздел:","role_physical":"👤 Физическое лицо","role_legal":"🏢 Юридическое лицо","role_broker":"👨‍💼 Для брокеров (PRO)","chat":"💬 Чат с помощником","faq":"❓ FAQ","docs":"📄 Документы","specialist":"👨‍💼 Специалист","change":"🌐 Сменить язык / роль","tnved":"🔎 ТН ВЭД и ставки","exact":"🎯 Точный код и ставка","broker_cost":"💰 Узнать таможенную стоимость","broker_min_avg":"📉 Мин. и средняя стоимость","broker_3m":"📊 База за 3 месяца","back_menu":"⬅️ Назад в меню","back":"⬅️ Назад","pick_category":"Выберите категорию:","pick_group":"Выберите группу:","pick_item":"Выберите вариант:","enter_code":"Введите код ТН ВЭД: 4, 6, 8 или 10 цифр.","nothing_found":"Ничего подходящего не найдено. Попробуйте другой товар или нажмите «Специалист».","possible":"Возможные варианты:","code_result":"Результат по коду","source":"Источник","branch_hint":"Если результат не подошёл — нажмите «Специалист».","physical_intro":"Напишите вопрос простыми словами. Я отвечу по правилам для физлиц.","legal_intro":"Напишите товар или вопрос простыми словами. Я покажу 3–4 возможных варианта.","physical_no_calc":"В режиме физлица я не показываю брокерские коды и ставки по умолчанию.","broker_intro":"Раздел для брокеров (PRO).\n\nДоступна платная услуга:","broker_pick":"Выберите услугу:","broker_paid":"Это платная услуга. После заявки специалист свяжется с вами.","enter_name":"Введите ваше имя:","enter_product":"Напишите товар / запрос:","enter_country":"Укажите страну происхождения или отправления:","enter_comment":"Добавьте комментарий, если нужно:","service_min_avg":"Мин. и средняя стоимость","service_3m":"База за 3 месяца","application_sent":"✅ Заявка отправлена специалисту.","analytics_empty":"Статистика пока пустая.","analytics_title":"📊 Аналитика бота","role_legal_ready":"Режим юрлица: сначала категории и варианты, отдельная кнопка для точного кода.","faq_intro":"Частые вопросы:\n• сколько телефонов можно ввезти\n• лимит через аэропорт\n• IMEI регистрация\n• временный ввоз авто\n• документы для юрлица\n• как определить код ТН ВЭД","docs_physical":"Документы для физлица:\n• паспорт\n• чеки/инвойс при наличии\n• пассажирская декларация при необходимости\n• документы на авто/телефон в нужных случаях","docs_legal":"Документы для юрлица:\n• контракт\n• инвойс\n• упаковочный лист\n• транспортные документы\n• сертификаты/разрешения при необходимости\n• код ТН ВЭД"},
"uz":{"choose_lang":"Tilni tanlang:","choose_role":"Rejimni tanlang:","lang_saved":"Til saqlandi.","saved":"Tayyor. Bo‘limni tanlang:","role_physical":"👤 Jismoniy shaxs","role_legal":"🏢 Yuridik shaxs","role_broker":"👨‍💼 Brokerlar uchun (PRO)","chat":"💬 Yordamchi bilan chat","faq":"❓ FAQ","docs":"📄 Hujjatlar","specialist":"👨‍💼 Mutaxassis","change":"🌐 Til / rolni almashtirish","tnved":"🔎 TN VED va stavkalar","exact":"🎯 Aniq kod va stavka","broker_cost":"💰 Bojxona qiymatini bilish","broker_min_avg":"📉 Min. va o‘rtacha qiymat","broker_3m":"📊 Oxirgi 3 oy bazasi","back_menu":"⬅️ Menyuga qaytish","back":"⬅️ Orqaga","pick_category":"Kategoriyani tanlang:","pick_group":"Guruhni tanlang:","pick_item":"Variantni tanlang:","enter_code":"TN VED kodini kiriting: 4, 6, 8 yoki 10 ta raqam.","nothing_found":"Mos natija topilmadi. Boshqa tovarni yozing yoki «Mutaxassis» tugmasini bosing.","possible":"Mumkin bo‘lgan variantlar:","code_result":"Kod bo‘yicha natija","source":"Manba","branch_hint":"Natija mos kelmasa — «Mutaxassis» tugmasini bosing.","physical_intro":"Savolni oddiy so‘zlar bilan yozing. Men jismoniy shaxslar uchun yordam beraman.","legal_intro":"Tovar yoki savolni oddiy so‘zlar bilan yozing. Men 3–4 variant ko‘rsataman.","physical_no_calc":"Jismoniy shaxs rejimida brokerlik kodlari va stavkalarini odatda ko‘rsatmayman.","broker_intro":"Brokerlar uchun bo‘lim (PRO).\n\nPullik xizmat mavjud:","broker_pick":"Xizmatni tanlang:","broker_paid":"Bu pullik xizmat. Ariza yuborilgach, mutaxassis siz bilan bog‘lanadi.","enter_name":"Ismingizni kiriting:","enter_product":"Tovar / so‘rovni yozing:","enter_country":"Kelib chiqish yoki jo‘natish davlatini kiriting:","enter_comment":"Kerak bo‘lsa izoh qoldiring:","service_min_avg":"Min. va o‘rtacha qiymat","service_3m":"Oxirgi 3 oy bazasi","application_sent":"✅ Ariza mutaxassisga yuborildi.","analytics_empty":"Statistika hozircha bo‘sh.","analytics_title":"📊 Bot analitikasi","role_legal_ready":"Yuridik shaxs rejimi: avval kategoriyalar va variantlar, aniq kod uchun alohida tugma.","faq_intro":"Ko‘p beriladigan savollar:\n• nechta telefon olib kirish mumkin\n• aeroport limiti\n• IMEI ro‘yxatdan o‘tkazish\n• vaqtinchalik auto olib kirish\n• yuridik shaxs hujjatlari\n• TN VED kodini aniqlash","docs_physical":"Jismoniy shaxs uchun hujjatlar:\n• pasport\n• chek/invoys bo‘lsa\n• kerak bo‘lsa yo‘lovchi deklaratsiyasi\n• ayrim holatlarda auto/telefon hujjatlari","docs_legal":"Yuridik shaxs uchun hujjatlar:\n• kontrakt\n• invoys\n• qadoqlash varaqasi\n• transport hujjatlari\n• zarur bo‘lsa sertifikat/ruxsatnomalar\n• TN VED kodi"}
}

TREE = {
  "food": {
    "ru": "🫒 Продукты и масла",
    "uz": "🫒 Oziq-ovqat va moylar",
    "groups": {
      "oils": {
        "ru": "🌻 Масла и жиры",
        "uz": "🌻 Moylar va yog‘lar",
        "items": [
          [
            "подсолнечное масло",
            [
              "1512",
              "1512199002"
            ]
          ],
          [
            "растительное масло",
            [
              "1512"
            ]
          ],
          [
            "рафинированное масло",
            [
              "1512199002"
            ]
          ],
          [
            "пищевые масла",
            [
              "1512"
            ]
          ],
          [
            "масла и жиры",
            [
              "1512"
            ]
          ]
        ]
      },
      "drinks": {
        "ru": "🍺 Напитки",
        "uz": "🍺 Ichimliklar",
        "items": [
          [
            "пиво",
            [
              "2203000000",
              "2203"
            ]
          ],
          [
            "вино",
            [
              "2204"
            ]
          ],
          [
            "энергетики",
            [
              "2202"
            ]
          ],
          [
            "сладкие напитки",
            [
              "2202"
            ]
          ],
          [
            "соки и напитки",
            [
              "2202"
            ]
          ]
        ]
      }
    }
  },
  "medicine": {
    "ru": "💊 Медицина",
    "uz": "💊 Tibbiyot",
    "groups": {
      "tablets": {
        "ru": "💊 Таблетки и витамины",
        "uz": "💊 Tabletkalar va vitaminlar",
        "items": [
          [
            "парацетамол",
            [
              "3004900000"
            ]
          ],
          [
            "витамины",
            [
              "3004500000"
            ]
          ],
          [
            "антибиотики",
            [
              "3004100000"
            ]
          ],
          [
            "лекарства в таблетках",
            [
              "3004900000",
              "3004500000",
              "3004100000"
            ]
          ],
          [
            "медицинские препараты",
            [
              "3004",
              "3005",
              "3006"
            ]
          ]
        ]
      },
      "other_med": {
        "ru": "🧴 Сиропы и медизделия",
        "uz": "🧴 Sirop va tibbiy buyumlar",
        "items": [
          [
            "сиропы",
            [
              "3004"
            ]
          ],
          [
            "перевязочные материалы",
            [
              "3005"
            ]
          ],
          [
            "медицинские изделия",
            [
              "3006"
            ]
          ],
          [
            "аптечные товары",
            [
              "3004",
              "3005",
              "3006"
            ]
          ],
          [
            "лекарственные средства",
            [
              "3002",
              "3003",
              "3004"
            ]
          ]
        ]
      }
    }
  },
  "electronics": {
    "ru": "📱 Электроника",
    "uz": "📱 Elektronika",
    "groups": {
      "phones": {
        "ru": "📱 Телефоны",
        "uz": "📱 Telefonlar",
        "items": [
          [
            "смартфон",
            [
              "8517130000"
            ]
          ],
          [
            "iphone",
            [
              "8517130000"
            ]
          ],
          [
            "samsung",
            [
              "8517130000"
            ]
          ],
          [
            "мобильный телефон",
            [
              "8517130000"
            ]
          ],
          [
            "кнопочный телефон",
            [
              "8517"
            ]
          ]
        ]
      },
      "audio": {
        "ru": "🔊 Аудио и колонки",
        "uz": "🔊 Audio va kolonkalar",
        "items": [
          [
            "колонки",
            [
              "8518210000"
            ]
          ],
          [
            "bluetooth колонка",
            [
              "8518210000"
            ]
          ],
          [
            "громкоговорители",
            [
              "8518210000"
            ]
          ],
          [
            "наушники",
            [
              "8518"
            ]
          ],
          [
            "аудиотехника",
            [
              "8518",
              "8518210000"
            ]
          ]
        ]
      }
    }
  },
  "auto": {
    "ru": "🚗 Авто и запчасти",
    "uz": "🚗 Avto va ehtiyot qismlar",
    "groups": {
      "cars": {
        "ru": "🚘 Легковые авто",
        "uz": "🚘 Yengil avtomobillar",
        "items": [
          [
            "электромобиль",
            [
              "8703800001",
              "870380101"
            ]
          ],
          [
            "гибрид",
            [
              "8703400000",
              "870340101"
            ]
          ],
          [
            "бензиновый авто",
            [
              "8703",
              "870321101",
              "870322101",
              "870323194",
              "870324101"
            ]
          ],
          [
            "легковой автомобиль",
            [
              "8703"
            ]
          ],
          [
            "автомобиль BYD/Tesla/Prius",
            [
              "8703800001",
              "8703400000",
              "8703"
            ]
          ]
        ]
      },
      "parts": {
        "ru": "🛞 Шины и запчасти",
        "uz": "🛞 Shinalar va ehtiyot qismlar",
        "items": [
          [
            "шины",
            [
              "4011100000",
              "4011"
            ]
          ],
          [
            "автошины",
            [
              "4011100000"
            ]
          ],
          [
            "диски и колёса",
            [
              "870870500",
              "8708"
            ]
          ],
          [
            "тормозные части",
            [
              "870830910",
              "8708"
            ]
          ],
          [
            "кузовные части",
            [
              "870829900",
              "870810900",
              "8708"
            ]
          ]
        ]
      }
    }
  },
  "tobacco": {
    "ru": "🚬 Табак и вейпы",
    "uz": "🚬 Tamaki va veyp",
    "groups": {
      "smoke": {
        "ru": "🚬 Сигареты и табак",
        "uz": "🚬 Sigareta va tamaki",
        "items": [
          [
            "сигареты",
            [
              "2402209000",
              "2402"
            ]
          ],
          [
            "табак",
            [
              "2402",
              "24"
            ]
          ],
          [
            "табак для кальяна",
            [
              "24"
            ]
          ],
          [
            "снюс",
            [
              "24"
            ]
          ],
          [
            "сигары",
            [
              "24"
            ]
          ]
        ]
      },
      "vape": {
        "ru": "💨 Вейпы и жидкости",
        "uz": "💨 Veyp va suyuqlik",
        "items": [
          [
            "вейп жидкость",
            [
              "24"
            ]
          ],
          [
            "никотиновая жидкость",
            [
              "24"
            ]
          ],
          [
            "электронные сигареты",
            [
              "24"
            ]
          ],
          [
            "картриджи",
            [
              "24"
            ]
          ],
          [
            "никотиновые товары",
            [
              "24"
            ]
          ]
        ]
      }
    }
  },
  "alcohol": {
    "ru": "🍷 Алкоголь",
    "uz": "🍷 Alkogol",
    "groups": {
      "spirits": {
        "ru": "🥃 Крепкий алкоголь",
        "uz": "🥃 Kuchli alkogol",
        "items": [
          [
            "водка",
            [
              "2208"
            ]
          ],
          [
            "коньяк",
            [
              "2208"
            ]
          ],
          [
            "спирт",
            [
              "2207"
            ]
          ],
          [
            "алкоголь крепкий",
            [
              "2208"
            ]
          ],
          [
            "ликёры",
            [
              "2208"
            ]
          ]
        ]
      },
      "wine_beer": {
        "ru": "🍺 Пиво и вино",
        "uz": "🍺 Pivo va vino",
        "items": [
          [
            "пиво",
            [
              "2203000000",
              "2203"
            ]
          ],
          [
            "вино",
            [
              "2204"
            ]
          ],
          [
            "вермут",
            [
              "2205"
            ]
          ],
          [
            "натуральное вино",
            [
              "2204"
            ]
          ],
          [
            "алкогольные напитки",
            [
              "2203",
              "2204",
              "2208"
            ]
          ]
        ]
      }
    }
  },
  "fuel": {
    "ru": "⛽ Топливо и масла",
    "uz": "⛽ Yoqilg‘i va moy",
    "groups": {
      "fuel_main": {
        "ru": "⛽ Топливо",
        "uz": "⛽ Yoqilg‘i",
        "items": [
          [
            "бензин",
            [
              "2710"
            ]
          ],
          [
            "дизель",
            [
              "2710"
            ]
          ],
          [
            "авиакеросин",
            [
              "2710"
            ]
          ],
          [
            "сжиженный газ",
            [
              "2711"
            ]
          ],
          [
            "сжатый газ",
            [
              "2711"
            ]
          ]
        ]
      },
      "lubricants": {
        "ru": "🛢 Моторные масла",
        "uz": "🛢 Motor moylari",
        "items": [
          [
            "моторное масло",
            [
              "2710"
            ]
          ],
          [
            "масло для двигателя",
            [
              "2710"
            ]
          ],
          [
            "дизельное масло",
            [
              "2710"
            ]
          ],
          [
            "смазочные материалы",
            [
              "2710"
            ]
          ],
          [
            "нефтепродукты",
            [
              "2710",
              "2711"
            ]
          ]
        ]
      }
    }
  },
  "agro": {
    "ru": "🌾 Сельхозтовары",
    "uz": "🌾 Qishloq xo‘jaligi tovarlari",
    "groups": {
      "animals": {
        "ru": "🐄 Животные",
        "uz": "🐄 Hayvonlar",
        "items": [
          [
            "лошади",
            [
              "0101"
            ]
          ],
          [
            "крупный рогатый скот",
            [
              "0102"
            ]
          ],
          [
            "свиньи",
            [
              "0103"
            ]
          ],
          [
            "овцы и козы",
            [
              "0104"
            ]
          ],
          [
            "прочие живые животные",
            [
              "0106"
            ]
          ]
        ]
      },
      "birds_fruit": {
        "ru": "🐓 Птица и фрукты",
        "uz": "🐓 Parranda va meva",
        "items": [
          [
            "птица",
            [
              "0105"
            ]
          ],
          [
            "бананы",
            [
              "0803"
            ]
          ],
          [
            "цитрусовые",
            [
              "0805"
            ]
          ],
          [
            "виноград",
            [
              "0806"
            ]
          ],
          [
            "яблоки и груши",
            [
              "0808"
            ]
          ]
        ]
      }
    }
  },
  "art": {
    "ru": "🖼 Искусство и коллекции",
    "uz": "🖼 San’at va kolleksiya",
    "groups": {
      "paintings": {
        "ru": "🖼 Картины",
        "uz": "🖼 Rasmlar",
        "items": [
          [
            "картины",
            [
              "9701"
            ]
          ],
          [
            "живопись",
            [
              "970121000",
              "970191000"
            ]
          ],
          [
            "рисунки",
            [
              "9701"
            ]
          ],
          [
            "коллекционные картины",
            [
              "9701"
            ]
          ],
          [
            "произведения искусства",
            [
              "9701"
            ]
          ]
        ]
      },
      "collectibles": {
        "ru": "🎨 Коллекционные предметы",
        "uz": "🎨 Kolleksiya buyumlari",
        "items": [
          [
            "арт-объекты",
            [
              "9701"
            ]
          ],
          [
            "гравюры",
            [
              "9701"
            ]
          ],
          [
            "оригинальные рисунки",
            [
              "9701"
            ]
          ],
          [
            "художественные работы",
            [
              "9701"
            ]
          ],
          [
            "коллекционные предметы",
            [
              "9701"
            ]
          ]
        ]
      }
    }
  },
  "machines": {
    "ru": "⚙️ Машины и оборудование",
    "uz": "⚙️ Mashina va uskunalar",
    "groups": {
      "general": {
        "ru": "⚙️ Оборудование",
        "uz": "⚙️ Uskunalar",
        "items": [
          [
            "оборудование",
            [
              "84"
            ]
          ],
          [
            "машины",
            [
              "84"
            ]
          ],
          [
            "промышленное оборудование",
            [
              "84"
            ]
          ],
          [
            "станки",
            [
              "84"
            ]
          ],
          [
            "запчасти оборудования",
            [
              "84"
            ]
          ]
        ]
      },
      "transport_machines": {
        "ru": "🚜 Техника",
        "uz": "🚜 Texnika",
        "items": [
          [
            "тракторы",
            [
              "8701"
            ]
          ],
          [
            "автобусы",
            [
              "8702"
            ]
          ],
          [
            "грузовики",
            [
              "8704"
            ]
          ],
          [
            "мотоциклы",
            [
              "8711"
            ]
          ],
          [
            "транспортная техника",
            [
              "8701",
              "8702",
              "8704",
              "8711"
            ]
          ]
        ]
      }
    }
  }
}

USER_CTX={}

def ctx(uid):
    if uid not in USER_CTX:
        USER_CTX[uid]={"lang":"ru","role":None,"mode":None,"category":None,"group":None,"position":None,"pending_form":None,"form_data":{}}
    return USER_CTX[uid]

def reset_mode(uid):
    c=ctx(uid)
    c["mode"]=None; c["category"]=None; c["group"]=None; c["position"]=None; c["pending_form"]=None; c["form_data"]={}

def db_conn():
    conn=sqlite3.connect(ANALYTICS_DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,username TEXT,lang TEXT,role TEXT,event_type TEXT,event_value TEXT,created_at TEXT)")
    return conn

def track(uid, username, lang, role, etype, evalue=""):
    conn=db_conn()
    conn.execute("INSERT INTO events (user_id,username,lang,role,event_type,event_value,created_at) VALUES (?,?,?,?,?,?,?)",(uid,username or "",lang or "",role or "",etype,evalue,datetime.utcnow().isoformat()))
    conn.commit(); conn.close()

def analytics_text(lang):
    conn=db_conn(); cur=conn.cursor()
    cur.execute("SELECT COUNT(DISTINCT user_id) FROM events"); users=cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM events WHERE event_type='message'"); messages=cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM events WHERE event_type='application'"); apps=cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM events WHERE event_type='broker_application'"); bapps=cur.fetchone()[0] or 0
    conn.close()
    if not any([users,messages,apps,bapps]): return TXT[lang]["analytics_empty"]
    return f"<b>{TXT[lang]['analytics_title']}</b>\n\n👥 Пользователи: {users}\n💬 Сообщения: {messages}\n📩 Заявки специалисту: {apps}\n💼 PRO-заявки брокеров: {bapps}"

def t(lang,key): return TXT.get(lang,TXT["ru"]).get(key,key)

def build_lang_kb():
    kb=ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Русский","O'zbekcha")
    return kb

def role_kb(lang):
    kb=ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang,"role_physical"),t(lang,"role_legal"))
    kb.add(t(lang,"role_broker"))
    return kb

def physical_menu(lang):
    kb=ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang,"chat"),t(lang,"faq"))
    kb.add(t(lang,"docs"),t(lang,"specialist"))
    kb.add(t(lang,"change"))
    return kb

def legal_menu(lang):
    kb=ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang,"tnved"),t(lang,"exact"))
    kb.add(t(lang,"chat"),t(lang,"docs"))
    kb.add(t(lang,"broker_cost"),t(lang,"specialist"))
    kb.add("📊 Analytics",t(lang,"change"))
    return kb

def broker_menu(lang):
    kb=ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang,"broker_cost"))
    kb.add(t(lang,"back_menu"))
    return kb

def broker_cost_menu(lang):
    kb=ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang,"broker_min_avg"),t(lang,"broker_3m"))
    kb.add(t(lang,"back_menu"))
    return kb

def category_kb(lang):
    kb=ReplyKeyboardMarkup(resize_keyboard=True)
    for cid,cat in TREE.items():
        kb.add(cat[lang])
    kb.add(t(lang,"back_menu"))
    return kb

def group_kb(lang,cid):
    kb=ReplyKeyboardMarkup(resize_keyboard=True)
    for gid,g in TREE[cid]["groups"].items():
        kb.add(g[lang])
    kb.add(t(lang,"back"),t(lang,"back_menu"))
    return kb

def item_kb(lang,cid,gid):
    kb=ReplyKeyboardMarkup(resize_keyboard=True)
    for item_name,_codes in TREE[cid]["groups"][gid]["items"]:
        kb.add(item_name)
    kb.add(t(lang,"back"),t(lang,"back_menu"))
    return kb

def normalize_code(v): return "".join(ch for ch in str(v) if ch.isdigit())
def normalize_text(v): return re.sub(r"\s+"," ",v.strip().lower())

with open(PRODUCT_DB_PATH,"r",encoding="utf-8") as f:
    RECORDS=json.load(f)

def dedupe(items):
    seen=set(); out=[]
    for item in items:
        key=(item.get("code"), item.get("record_kind"), item.get("name_ru"))
        if key in seen: continue
        seen.add(key); out.append(item)
    return out

def code_search(code):
    n=normalize_code(code)
    exact=[r for r in RECORDS if normalize_code(r.get("code",""))==n and r.get("record_kind")=="exact"]
    if exact: return dedupe(exact)[:4]
    pref=[r for r in RECORDS if normalize_code(r.get("code","")).startswith(n) and r.get("record_kind") in ("exact","prefix")]
    return dedupe(pref)[:4]

def text_search(query, category=None):
    q=normalize_text(query); hits=[]
    for r in RECORDS:
        hay=" ".join([normalize_text(r.get("name_ru","")), normalize_text(r.get("name_uz","")), normalize_text(r.get("alias",""))] + [normalize_text(x) for x in r.get("examples",[])])
        if q and q in hay:
            score=0
            if r.get("record_kind")=="exact": score+=3
            if category and r.get("category")==category: score+=3
            hits.append((score,r))
    hits=sorted(hits,key=lambda x:x[0], reverse=True)
    return dedupe([r for _,r in hits])[:4]

def format_item(item,lang,idx):
    name=item.get("name_ru") if lang=="ru" else item.get("name_uz",item.get("name_ru"))
    return f"{idx}) <b>{name}</b>\nКод: <code>{item.get('code','')}</code>\nПошлина: {item.get('duty','уточнить')}\nНДС: {item.get('vat','12%')}\nАкциз: {item.get('excise','нет')}\n♻️ Утильсбор: {item.get('util','нет')}\n{t(lang,'source')}: {item.get('source_main','локальная база')}\n"

def ai_hint(query, items, lang):
    if not client or not items: return ""
    try:
        data=[{"code":i.get("code"),"name":i.get("name_ru"),"duty":i.get("duty"),"vat":i.get("vat"),"excise":i.get("excise"),"util":i.get("util")} for i in items[:4]]
        prompt=f"Ответь кратко на {'русском' if lang=='ru' else 'узбекском'} языке. Не придумывай новых кодов. Запрос: {query}. Данные: {json.dumps(data, ensure_ascii=False)}"
        resp=client.responses.create(model=OPENAI_MODEL, input=prompt)
        return (resp.output_text or "").strip()
    except Exception:
        return ""

def physical_answer(q,lang):
    q=normalize_text(q)
    if any(x in q for x in ["телефон","iphone","смартфон","phone"]): return "Для физлица важны лимит, личное пользование и IMEI-регистрация." if lang=="ru" else "Jismoniy shaxs uchun limit, shaxsiy foydalanish va IMEI ro‘yxatdan o‘tkazish muhim."
    if any(x in q for x in ["авто","машин","byd","tesla","gibrid","электро","mashina","avto"]): return "Для физлица по авто важны тип, возраст, объём двигателя, документы и цель ввоза." if lang=="ru" else "Jismoniy shaxs uchun avto bo‘yicha turi, yoshi, dvigatel hajmi, hujjatlar va olib kirish maqsadi muhim."
    return t(lang,"physical_no_calc")

async def send_main_menu(message, uid):
    c=ctx(uid); lang=c["lang"]; role=c["role"]; reset_mode(uid); c["lang"]=lang; c["role"]=role
    if role=="physical": await message.answer(t(lang,"saved"), reply_markup=physical_menu(lang))
    elif role=="legal": await message.answer(t(lang,"saved")+"\n\n"+t(lang,"role_legal_ready"), reply_markup=legal_menu(lang))
    elif role=="broker": await message.answer(t(lang,"broker_intro"), reply_markup=broker_menu(lang))
    else: await message.answer(t(lang,"choose_role"), reply_markup=role_kb(lang))

@dp.message_handler(commands=["start"])
async def start_cmd(message):
    USER_CTX[message.from_user.id]={"lang":"ru","role":None,"mode":"choose_lang","category":None,"group":None,"position":None,"pending_form":None,"form_data":{}}
    await message.answer(TXT["ru"]["choose_lang"], reply_markup=build_lang_kb())

@dp.message_handler(commands=["myid"])
async def myid_cmd(message):
    await message.answer(f"Ваш ID: <code>{message.from_user.id}</code>")

@dp.message_handler(commands=["analytics","stats"])
async def analytics_cmd(message):
    if ADMIN_CHAT_ID and str(message.from_user.id)!=str(ADMIN_CHAT_ID): return
    await message.answer(analytics_text(ctx(message.from_user.id)["lang"]))

@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def router(message):
    uid=message.from_user.id; username=message.from_user.username or ""; c=ctx(uid); lang=c["lang"]; role=c["role"]; text=message.text.strip()
    track(uid, username, lang, role or "", "message", text)

    if text in ["Русский","O'zbekcha"]:
        c["lang"]="ru" if text=="Русский" else "uz"; c["mode"]="choose_role"
        await message.answer(t(c["lang"],"lang_saved")+"\n"+t(c["lang"],"choose_role"), reply_markup=role_kb(c["lang"]))
        return

    lang=c["lang"]

    if text in [t(lang,"role_physical"),t(lang,"role_legal"),t(lang,"role_broker")]:
        c["role"]="physical" if text==t(lang,"role_physical") else "legal" if text==t(lang,"role_legal") else "broker"
        c["mode"]=None; track(uid, username, lang, c["role"], "role_selected", c["role"])
        await send_main_menu(message, uid); return

    if text==t(lang,"change"):
        reset_mode(uid); c["role"]=None; c["mode"]="choose_lang"
        await message.answer(t(lang,"choose_lang"), reply_markup=build_lang_kb()); return

    if text==t(lang,"back_menu"):
        # fix broker back: always return to current role main menu
        await send_main_menu(message, uid); return

    if text==t(lang,"back"):
        if c["mode"]=="legal_group":
            c["mode"]="legal_category"; await message.answer(t(lang,"pick_category"), reply_markup=category_kb(lang)); return
        if c["mode"]=="legal_item":
            c["mode"]="legal_group"; await message.answer(t(lang,"pick_group"), reply_markup=group_kb(lang,c["category"])); return
        if c["role"]=="broker":
            reset_mode(uid); await message.answer(t(lang,"broker_intro"), reply_markup=broker_menu(lang)); return
        await send_main_menu(message, uid); return

    if text==t(lang,"specialist"):
        reset_mode(uid); c["pending_form"]="specialist_name"; await message.answer(t(lang,"enter_name")); return

    if role=="physical":
        if text==t(lang,"faq"): await message.answer(TXT[lang]["faq_intro"], reply_markup=physical_menu(lang)); return
        if text==t(lang,"docs"): await message.answer(TXT[lang]["docs_physical"], reply_markup=physical_menu(lang)); return
        if text==t(lang,"chat"): reset_mode(uid); c["mode"]="physical_chat"; await message.answer(t(lang,"physical_intro"), reply_markup=physical_menu(lang)); return
        if text in [t(lang,"tnved"),t(lang,"exact"),t(lang,"broker_cost")]: await message.answer(t(lang,"physical_no_calc"), reply_markup=physical_menu(lang)); return

    if role=="legal":
        if text==t(lang,"faq"): await message.answer(TXT[lang]["faq_intro"], reply_markup=legal_menu(lang)); return
        if text==t(lang,"docs"): await message.answer(TXT[lang]["docs_legal"], reply_markup=legal_menu(lang)); return
        if text==t(lang,"chat"): reset_mode(uid); c["mode"]="legal_chat"; await message.answer(t(lang,"legal_intro"), reply_markup=legal_menu(lang)); return
        if text==t(lang,"tnved"): reset_mode(uid); c["mode"]="legal_category"; await message.answer(t(lang,"pick_category"), reply_markup=category_kb(lang)); return
        if text==t(lang,"exact"): reset_mode(uid); c["mode"]="exact_code"; await message.answer(t(lang,"enter_code"), reply_markup=legal_menu(lang)); return
        if text==t(lang,"broker_cost"): c["role"]="broker"; reset_mode(uid); await message.answer(t(lang,"broker_intro"), reply_markup=broker_menu(lang)); return
        if text=="📊 Analytics" and (not ADMIN_CHAT_ID or str(uid)==str(ADMIN_CHAT_ID)): await message.answer(analytics_text(lang), reply_markup=legal_menu(lang)); return

    if role=="broker":
        if text==t(lang,"broker_cost"):
            reset_mode(uid); c["mode"]="broker_service"; await message.answer(t(lang,"broker_pick"), reply_markup=broker_cost_menu(lang)); return

    if c["mode"]=="legal_category":
        for cid,cat in TREE.items():
            if text==cat[lang]:
                c["category"]=cid; c["mode"]="legal_group"; await message.answer(t(lang,"pick_group"), reply_markup=group_kb(lang,cid)); return
        await message.answer(t(lang,"pick_category"), reply_markup=category_kb(lang)); return

    if c["mode"]=="legal_group":
        for gid,g in TREE[c["category"]]["groups"].items():
            if text==g[lang]:
                c["group"]=gid; c["mode"]="legal_item"; await message.answer(t(lang,"pick_item"), reply_markup=item_kb(lang,c["category"],gid)); return
        await message.answer(t(lang,"pick_group"), reply_markup=group_kb(lang,c["category"])); return

    if c["mode"]=="legal_item":
        # first handle curated item click
        for item_name,codes in TREE[c["category"]]["groups"][c["group"]]["items"]:
            if text==item_name:
                items=[]
                for code in codes:
                    items += code_search(code) if normalize_code(code) else text_search(code, c["category"])
                items=dedupe(items)[:4]
                if not items:
                    await message.answer(t(lang,"nothing_found"), reply_markup=legal_menu(lang)); return
                out=f"<b>{t(lang,'possible')}</b>\n\n"
                for i,item in enumerate(items,1): out += format_item(item,lang,i)+"\n"
                hint=ai_hint(text,items,lang)
                if hint: out += "\n<b>AI:</b>\n"+hint+"\n"
                out += t(lang,"branch_hint")
                await message.answer(out, reply_markup=legal_menu(lang)); return
        # fallback manual text in category
        items=text_search(text,c["category"])
        if not items:
            await message.answer(t(lang,"nothing_found"), reply_markup=legal_menu(lang)); return
        out=f"<b>{t(lang,'possible')}</b>\n\n"
        for i,item in enumerate(items,1): out += format_item(item,lang,i)+"\n"
        hint=ai_hint(text,items,lang)
        if hint: out += "\n<b>AI:</b>\n"+hint+"\n"
        out += t(lang,"branch_hint")
        await message.answer(out, reply_markup=legal_menu(lang)); return

    if c["mode"]=="exact_code":
        items=code_search(text)
        track(uid, username, lang, role or "", "code_search", normalize_code(text))
        if not items:
            await message.answer(t(lang,"nothing_found"), reply_markup=legal_menu(lang)); return
        out=f"<b>{t(lang,'code_result')}</b>\n\n"
        for i,item in enumerate(items,1): out += format_item(item,lang,i)+"\n"
        hint=ai_hint(text,items,lang)
        if hint: out += "\n<b>AI:</b>\n"+hint
        await message.answer(out, reply_markup=legal_menu(lang)); return

    if c["mode"]=="legal_chat":
        items=text_search(text)
        if not items:
            if client:
                try:
                    resp=client.responses.create(model=OPENAI_MODEL, input=f"Ответь кратко на {'русском' if lang=='ru' else 'узбекском'} языке. Если данных не хватает — честно скажи это. Запрос: {text}")
                    await message.answer((resp.output_text or "").strip() or t(lang,"nothing_found"), reply_markup=legal_menu(lang))
                except Exception:
                    await message.answer(t(lang,"nothing_found"), reply_markup=legal_menu(lang))
            else:
                await message.answer(t(lang,"nothing_found"), reply_markup=legal_menu(lang))
            return
        out=f"<b>{t(lang,'possible')}</b>\n\n"
        for i,item in enumerate(items,1): out += format_item(item,lang,i)+"\n"
        hint=ai_hint(text,items,lang)
        if hint: out += "\n<b>AI:</b>\n"+hint+"\n"
        out += t(lang,"branch_hint")
        await message.answer(out, reply_markup=legal_menu(lang)); return

    if c["mode"]=="physical_chat":
        if client:
            try:
                resp=client.responses.create(model=OPENAI_MODEL, input=f"Ответь кратко на {'русском' if lang=='ru' else 'узбекском'} языке как помощник по физлицам Узбекистана. Не показывай брокерские ставки по умолчанию. Запрос: {text}")
                ans=(resp.output_text or "").strip()
                await message.answer(ans or physical_answer(text,lang), reply_markup=physical_menu(lang))
            except Exception:
                await message.answer(physical_answer(text,lang), reply_markup=physical_menu(lang))
        else:
            await message.answer(physical_answer(text,lang), reply_markup=physical_menu(lang))
        return

    if c["pending_form"]=="specialist_name":
        c["form_data"]["name"]=text; c["pending_form"]="specialist_product"; await message.answer(t(lang,"enter_product")); return
    if c["pending_form"]=="specialist_product":
        c["form_data"]["product"]=text; c["pending_form"]=None
        msg=f"📩 <b>Новая заявка специалисту</b>\n\nИмя: {c['form_data'].get('name','')}\nЗапрос: {c['form_data'].get('product','')}\nРежим: {role or '-'}\nID: <code>{uid}</code>\nUsername: @{username or '-'}"
        if ADMIN_CHAT_ID:
            try: await bot.send_message(ADMIN_CHAT_ID,msg)
            except Exception: pass
        track(uid, username, lang, role or "", "application", c['form_data'].get('product',''))
        await message.answer(t(lang,"application_sent")); await send_main_menu(message, uid); return

    if c["mode"]=="broker_service":
        if text==t(lang,"broker_min_avg"):
            c["form_data"]={"service":t(lang,"service_min_avg")}; c["pending_form"]="broker_name"; c["mode"]=None
            await message.answer(t(lang,"broker_paid")+"\n\n"+t(lang,"enter_name"), reply_markup=broker_menu(lang)); return
        if text==t(lang,"broker_3m"):
            c["form_data"]={"service":t(lang,"service_3m")}; c["pending_form"]="broker_name"; c["mode"]=None
            await message.answer(t(lang,"broker_paid")+"\n\n"+t(lang,"enter_name"), reply_markup=broker_menu(lang)); return
        if text==t(lang,"back_menu"):
            reset_mode(uid); await message.answer(t(lang,"broker_intro"), reply_markup=broker_menu(lang)); return
        await message.answer(t(lang,"broker_pick"), reply_markup=broker_cost_menu(lang)); return

    if c["pending_form"]=="broker_name":
        c["form_data"]["name"]=text; c["pending_form"]="broker_product"; await message.answer(t(lang,"enter_product"), reply_markup=broker_menu(lang)); return
    if c["pending_form"]=="broker_product":
        c["form_data"]["product"]=text; c["pending_form"]="broker_country"; await message.answer(t(lang,"enter_country"), reply_markup=broker_menu(lang)); return
    if c["pending_form"]=="broker_country":
        c["form_data"]["country"]=text; c["pending_form"]="broker_comment"; await message.answer(t(lang,"enter_comment"), reply_markup=broker_menu(lang)); return
    if c["pending_form"]=="broker_comment":
        c["form_data"]["comment"]=text; c["pending_form"]=None
        msg=f"💼 <b>Новая PRO-заявка</b>\n\nУслуга: {c['form_data'].get('service','')}\nИмя: {c['form_data'].get('name','')}\nТовар: {c['form_data'].get('product','')}\nСтрана: {c['form_data'].get('country','')}\nКомментарий: {c['form_data'].get('comment','')}\nID: <code>{uid}</code>\nUsername: @{username or '-'}"
        if ADMIN_CHAT_ID:
            try: await bot.send_message(ADMIN_CHAT_ID,msg)
            except Exception: pass
        track(uid, username, lang, role or "", "broker_application", c['form_data'].get('service',''))
        await message.answer(t(lang,"application_sent"), reply_markup=broker_menu(lang)); await send_main_menu(message, uid); return

    if role=="physical": await message.answer(t(lang,"physical_no_calc"), reply_markup=physical_menu(lang))
    elif role=="legal": await message.answer(t(lang,"saved"), reply_markup=legal_menu(lang))
    elif role=="broker": await message.answer(t(lang,"broker_intro"), reply_markup=broker_menu(lang))
    else: await message.answer(t(lang,"choose_lang"), reply_markup=build_lang_kb())

if __name__=="__main__":
    executor.start_polling(dp, skip_updates=True)
