
import os, re, json, logging, sqlite3
from datetime import datetime
from typing import Dict, List, Any
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "").strip()
ANALYTICS_DB_PATH = os.getenv("ANALYTICS_DB_PATH", "analytics.db")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

print("\n=== ENV CHECK ===")
print("BOT_TOKEN:", "OK" if BOT_TOKEN else "MISSING")
print("ADMIN_CHAT_ID:", ADMIN_CHAT_ID if ADMIN_CHAT_ID else "MISSING")
print("ANALYTICS_DB_PATH:", ANALYTICS_DB_PATH)
print("OPENAI_API_KEY:", "OK" if OPENAI_API_KEY else "NOT SET")
print("OPENAI_MODEL:", OPENAI_MODEL)
print("=================\n")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())
client = OpenAI(api_key=OPENAI_API_KEY) if (OPENAI_API_KEY and OpenAI) else None

TXT = {
    "ru": {
        "choose_lang":"Выберите язык / Tilni tanlang:",
        "choose_role":"Главное меню:\n\nВыберите раздел:",
        "lang_saved":"Язык сохранён.",
        "saved":"Главное меню:\n\nВыберите раздел:",
        "role_physical":"👤 Для физ лиц",
        "role_legal":"🏢 Для юр лиц",
        "role_broker":"📊 Для брокеров",
        "role_logistics":"🚚 Логистика",
        "chat":"💬 Чат с помощником",
        "faq":"❓ FAQ",
        "docs":"📄 Документы",
        "specialist":"👨‍💼 Специалист",
        "change":"🌐 Сменить язык / роль",
        "tnved":"🔎 ТН ВЭД и ставки",
        "exact":"🎯 Точный код и ставка",
        "broker_cost":"1️⃣ Анализ таможенной стоимости",
        "broker_docs":"2️⃣ Проверка документов перед подачей",
        "broker_cert":"3️⃣ Нюансы по сертификации",
        "broker_tnved_analytics":"4️⃣ Аналитика по ТН ВЭД коду",
        "broker_min_avg":"1) 1 год — минимальная и средняя стоимость",
        "broker_3m":"2) База за 3 месяца по товару",
        "back_menu":"⬅️ Назад в меню",
        "back":"⬅️ Назад",
        "pick_category":"Выберите категорию:",
        "pick_group":"Выберите группу:",
        "pick_item":"Выберите вариант:",
        "enter_code":"Введите код ТН ВЭД. Если введёте 4 цифры, я покажу все найденные варианты по этому префиксу.",
        "nothing_found":"Ничего подходящего не найдено. Попробуйте другой товар или нажмите «Специалист».",
        "possible":"Возможные варианты:",
        "code_result":"Результат по коду",
        "source":"Источник",
        "branch_hint":"Если результат не подошёл — нажмите «Специалист».",
        "physical_intro":"Напишите вопрос простыми словами. Я отвечу по правилам для физлиц.",
        "legal_intro":"Для юридических лиц\n\nНаши специалисты имеют 10–15 лет опыта в таможенной сфере и помогут по вопросам:\n\n• ТН ВЭД и ставок\n• импорта и экспорта\n• документов\n• сертификации\n\nВы можете получить общую информацию сразу в боте, а точный ответ по вашему кейсу специалист даст бесплатно в течение дня.",
        "specialist_intro":"Связь со специалистом\n\nОпишите ваш вопрос, и мы передадим его специалисту.\n\nСпециалист ответит бесплатно в течение дня.",
        "enter_tg":"Укажите ваш Telegram (username или номер):",
        "enter_phone":"Введите номер телефона:",
        "enter_question":"Опишите ваш вопрос:",
        "specialist_done":"✅ Ваша заявка отправлена.\n\nСпециалист свяжется с вами в течение дня.",
        "physical_no_calc":"В режиме физлица я не показываю брокерские коды и ставки по умолчанию.",
        "broker_intro":"Для брокеров\n\nНаши эксперты имеют 10–15 лет практического опыта в таможенной сфере Узбекистана.\n\nМы помогаем:\n• избежать переплат по таможенной стоимости\n• проверить документы до подачи\n• заранее понять требования по сертификации\n• подготовить кейс для специалиста\n\nРазбор кейса: Как не переплатить $1000 на ровном месте\n\nВыберите услугу:",
        "broker_pick":"Выберите услугу:",
        "broker_paid":"Это платная услуга. После заявки специалист свяжется с вами.",
        "enter_name":"Введите ваше имя:",
        "enter_product":"Напишите товар / запрос:",
        "enter_country":"Укажите страну происхождения или отправления:",
        "enter_comment":"Добавьте комментарий, если нужно:",
        "service_min_avg":"Анализ стоимости за 1 год",
        "service_docs":"Проверка документов перед подачей",
        "service_cert":"Нюансы по сертификации",
        "service_tnved_analytics":"Аналитика по ТН ВЭД коду",
        "service_3m":"База за 3 месяца",
        "application_sent":"✅ Заявка отправлена специалисту.",
        "analytics_empty":"Статистика пока пустая.",
        "analytics_title":"📊 Аналитика бота",
        "role_legal_ready":"Для юридических лиц: выберите нужный раздел.",
        "faq_intro":"Частые вопросы:\n• сколько телефонов можно ввезти\n• лимит через аэропорт\n• IMEI регистрация\n• временный ввоз авто\n• документы для юрлица\n• как определить код ТН ВЭД",
        "docs_physical":"Документы для физлица:\n• паспорт\n• чеки/инвойс\n• транспортные документы\n• при необходимости декларация",
        "docs_legal":"Документы для юрлица:\n• контракт\n• инвойс\n• упаковочный лист\n• транспортные документы\n• сертификаты/разрешения\n• код ТН ВЭД",
        "ai_intro":"Чат с помощником\n\nВыберите частый вопрос или задайте свой.\nПомощник отвечает только по вопросам таможни, импорта, экспорта, ТН ВЭД, документов, сертификации, ставок и платежей.\n\nЕсли нужен точный ответ по вашему кейсу, специалист поможет бесплатно.",
        "faq_1":"Какие документы нужны для импорта?",
        "faq_2":"Какие документы нужны для экспорта?",
        "faq_3":"Какие сертификаты нужны для импорта?",
        "faq_4":"Как определяется код ТН ВЭД?",
        "faq_5":"Какие платежи при импорте?",
        "faq_6":"Задать свой вопрос",
        "ask_own":"✍️ Задать свой вопрос",
        "free_specialist":"Если хотите, я могу бесплатно передать ваш вопрос специалисту.",
        "only_customs":"Я помощник только по вопросам таможни, импорта, экспорта, ТН ВЭД, документов и сертификации.",
        "log_intro":"Логистика\n\nМы собираем предложения от проверенных логистов, а вы выбираете лучший вариант.\n\nЧто вы получаете:\n• доставка из Китая, Кореи, Европы и СНГ\n• одна заявка → несколько предложений\n• выбор по цене и срокам\n\nБонус:\nпомощь по документам и растаможке\n\nУ нас есть 10 проверенных логистов.\nМы подберём для вас 3–4 лучших варианта.",
        "log_apply":"📝 Оставить заявку",
        "log_how":"ℹ️ Как это работает",
        "log_how_text":"Как это работает:\n\n1. Вы оставляете заявку\n2. Мы передаём её логистам\n3. Получаем предложения\n4. Отправляем вам 3–4 варианта\n\nВы сами выбираете лучшую цену и сроки.",
        "enter_from":"Откуда груз:",
        "enter_to":"Куда доставить:",
        "enter_weight":"Вес или объём груза:",
        "enter_more":"Дополнительная информация:",
        "log_done":"✅ Ваша заявка принята.\n\nМы подберём варианты и свяжемся с вами."
    },
    "uz": {
        "choose_lang":"Tilni tanlang / Выберите язык:",
        "choose_role":"Asosiy menyu:\n\nBo‘limni tanlang:",
        "lang_saved":"Til saqlandi.",
        "saved":"Asosiy menyu:\n\nBo‘limni tanlang:",
        "role_physical":"👤 Jismoniy shaxslar",
        "role_legal":"🏢 Yuridik shaxslar",
        "role_broker":"📊 Brokerlar",
        "role_logistics":"🚚 Logistika",
        "chat":"💬 Yordamchi bilan chat",
        "faq":"❓ FAQ",
        "docs":"📄 Hujjatlar",
        "specialist":"👨‍💼 Mutaxassis",
        "change":"🌐 Til / rolni almashtirish",
        "tnved":"🔎 TN VED va stavkalar",
        "exact":"🎯 Aniq kod va stavka",
        "broker_cost":"1️⃣ Bojxona qiymati tahlili",
        "broker_docs":"2️⃣ Hujjatlarni topshirishdan oldin tekshirish",
        "broker_cert":"3️⃣ Sertifikatlash нюансlari",
        "broker_tnved_analytics":"4️⃣ TN VED kodi bo‘yicha analitika",
        "broker_min_avg":"1) 1 yil — minimal va o‘rtacha qiymat",
        "broker_3m":"2) Tovar bo‘yicha 3 oylik baza",
        "back_menu":"⬅️ Menyuga qaytish",
        "back":"⬅️ Orqaga",
        "pick_category":"Kategoriyani tanlang:",
        "pick_group":"Guruhni tanlang:",
        "pick_item":"Variantni tanlang:",
        "enter_code":"TN VED kodini kiriting. Agar 4 ta raqam kiritsangiz, shu prefiks bo‘yicha barcha variantlarni ko‘rsataman.",
        "nothing_found":"Mos natija topilmadi. Boshqa tovarni yozing yoki «Mutaxassis» tugmasini bosing.",
        "possible":"Mumkin bo‘lgan variantlar:",
        "code_result":"Kod bo‘yicha natija",
        "source":"Manba",
        "branch_hint":"Natija mos kelmasa — «Mutaxassis» tugmasini bosing.",
        "physical_intro":"Savolni oddiy so‘zlar bilan yozing. Men jismoniy shaxslar uchun yordam beraman.",
        "legal_intro":"Yuridik shaxslar uchun\n\nMutaxassislarimiz bojxona sohasida 10–15 yillik tajribaga ega va quyidagi masalalarda yordam beradi:\n\n• TN VED va stavkalar\n• import va eksport\n• hujjatlar\n• sertifikatlar\n\nSiz umumiy ma’lumotni botdan olishingiz mumkin, aniq javobni esa mutaxassis bir kun ichida bepul beradi.",
        "specialist_intro":"Mutaxassis bilan bog‘lanish\n\nSavolingizni yozing, biz uni mutaxassisga yuboramiz.\n\nMutaxassis bir kun ichida bepul javob beradi.",
        "enter_tg":"Telegramingizni kiriting (username yoki raqam):",
        "enter_phone":"Telefon raqamingizni kiriting:",
        "enter_question":"Savolingizni yozing:",
        "specialist_done":"✅ Arizangiz yuborildi.\n\nMutaxassis siz bilan bir kun ichida bog‘lanadi.",
        "physical_no_calc":"Jismoniy shaxs rejimida brokerlik kodlari va stavkalarini odatda ko‘rsatmayman.",
        "broker_intro":"Brokerlar uchun\n\nMutaxassislarimiz O‘zbekiston bojxona sohasida 10–15 yillik tajribaga ega.\n\nBiz yordam beramiz:\n• bojxona qiymatida ortiqcha to‘lovlarning oldini olish\n• hujjatlarni topshirishdan oldin tekshirish\n• sertifikat talablarini oldindan tushunish\n• кейсni tayyorlash\n\nXizmatni tanlang:",
        "broker_pick":"Xizmatni tanlang:",
        "broker_paid":"Bu pullik xizmat. Ariza yuborilgach, mutaxassis siz bilan bog‘lanadi.",
        "enter_name":"Ismingizni kiriting:",
        "enter_product":"Tovar / so‘rovni yozing:",
        "enter_country":"Kelib chiqish yoki jo‘natish davlatini kiriting:",
        "enter_comment":"Kerak bo‘lsa izoh qoldiring:",
        "service_min_avg":"1 yil bo‘yicha qiymat tahlili",
        "service_docs":"Hujjatlarni tekshirish",
        "service_cert":"Sertifikatlash masalalari",
        "service_tnved_analytics":"TN VED kodi bo‘yicha analitika",
        "service_3m":"Oxirgi 3 oy bazasi",
        "application_sent":"✅ Ariza mutaxassisga yuborildi.",
        "analytics_empty":"Statistika hozircha bo‘sh.",
        "analytics_title":"📊 Bot analitikasi",
        "role_legal_ready":"Yuridik shaxslar uchun kerakli bo‘limni tanlang.",
        "faq_intro":"Ko‘p beriladigan savollar:\n• nechta telefon olib kirish mumkin\n• aeroport limiti\n• IMEI ro‘yxatdan o‘tkazish\n• vaqtinchalik avto olib kirish\n• yuridik shaxs hujjatlari\n• TN VED kodini aniqlash",
        "docs_physical":"Jismoniy shaxs uchun hujjatlar:\n• pasport\n• chek/invoys\n• transport hujjatlari\n• kerak bo‘lsa deklaratsiya",
        "docs_legal":"Yuridik shaxs uchun hujjatlar:\n• kontrakt\n• invoys\n• qadoqlash varaqasi\n• transport hujjatlari\n• sertifikat/ruxsatnomalar\n• TN VED kodi",
        "ai_intro":"Yordamchi bilan chat\n\nTez-tez beriladigan savolni tanlang yoki o‘z savolingizni yozing. Yordamchi faqat bojxona, import, eksport, TN VED, hujjatlar, sertifikat va stavkalar bo‘yicha javob beradi.\n\nAniq javob kerak bo‘lsa, mutaxassis bepul yordam beradi.",
        "faq_1":"Import uchun qaysi hujjatlar kerak?",
        "faq_2":"Eksport uchun qaysi hujjatlar kerak?",
        "faq_3":"Import uchun qanday sertifikatlar kerak?",
        "faq_4":"TN VED kodi qanday aniqlanadi?",
        "faq_5":"Importda qanday to‘lovlar bo‘ladi?",
        "faq_6":"O‘z savolini yozish",
        "ask_own":"✍️ O‘z savolini yozish",
        "free_specialist":"Istasangiz, savolingizni mutaxassisga bepul yuboraman.",
        "only_customs":"Men faqat bojxona, import, eksport, TN VED, hujjatlar va sertifikat masalalari bo‘yicha yordamchiman.",
        "log_intro":"Logistika\n\nBiz tekshirilgan logistlardan takliflar yig‘amiz, siz esa eng yaxshi variantni tanlaysiz.\n\nNimalarni olasiz:\n• Xitoy, Koreya, Yevropa va MDHdan yetkazib berish\n• bitta ariza → bir nechta taklif\n• narx va muddat bo‘yicha tanlov\n\nBonus:\nbojxona hujjatlari va rasmiylashtirish bo‘yicha yordam\n\nBizda 10 ta tekshirilgan logist bor.\nSiz uchun 3–4 ta eng mos variantni tanlaymiz.",
        "log_apply":"📝 Ariza qoldirish",
        "log_how":"ℹ️ Qanday ishlaydi",
        "log_how_text":"Qanday ishlaydi:\n\n1. Siz ariza qoldirasiz\n2. Biz uni logistlarga yuboramiz\n3. Takliflarni olamiz\n4. Sizga 3–4 variant yuboramiz\n\nEng yaxshi narx va muddatni o‘zingiz tanlaysiz.",
        "enter_from":"Yuk qayerdan:",
        "enter_to":"Qayerga yetkazilsin:",
        "enter_weight":"Yukning vazni yoki hajmi:",
        "enter_more":"Qo‘shimcha ma’lumot:",
        "log_done":"✅ Arizangiz qabul qilindi.\n\nVariantlarni tayyorlab siz bilan bog‘lanamiz."
    }
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
              "1512199002",
              "1512"
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
          ],
          [
            "маргарин и жиры",
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
              "2204210000",
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
              "2202100000",
              "2202"
            ]
          ],
          [
            "соки",
            [
              "2009890000",
              "2009"
            ]
          ],
          [
            "безалкогольные напитки",
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
              "3004"
            ]
          ],
          [
            "медицинские препараты",
            [
              "3004",
              "3005",
              "3006"
            ]
          ],
          [
            "фармпрепараты",
            [
              "3002",
              "3003",
              "3004"
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
          ],
          [
            "диагностические товары",
            [
              "3006",
              "90"
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
              "8517130000",
              "8517"
            ]
          ],
          [
            "мобильный телефон",
            [
              "8517130000",
              "8517"
            ]
          ],
          [
            "телефон и аксессуары",
            [
              "8517",
              "8518"
            ]
          ],
          [
            "кнопочный телефон",
            [
              "8517"
            ]
          ],
          [
            "рация и связь",
            [
              "8517"
            ]
          ],
          [
            "устройства связи",
            [
              "8517"
            ]
          ]
        ]
      },
      "audio_video": {
        "ru": "🔊 Аудио и ТВ",
        "uz": "🔊 Audio va TV",
        "items": [
          [
            "колонки",
            [
              "8518210000",
              "8518"
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
              "8518210000",
              "8518"
            ]
          ],
          [
            "наушники",
            [
              "8518"
            ]
          ],
          [
            "телевизор",
            [
              "8528720000",
              "8528"
            ]
          ],
          [
            "smart tv",
            [
              "8528720000",
              "8528"
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
              "8703800000",
              "870380"
            ]
          ],
          [
            "гибрид",
            [
              "8703400000",
              "870340"
            ]
          ],
          [
            "бензиновый авто до 1000 см³",
            [
              "8703211090"
            ]
          ],
          [
            "бензиновый авто 1000–1500 см³",
            [
              "8703221090"
            ]
          ],
          [
            "бензиновый авто 1500–3000 см³",
            [
              "8703231940"
            ]
          ],
          [
            "бензиновый авто свыше 3000 см³",
            [
              "8703241090"
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
              "8708705000",
              "8708"
            ]
          ],
          [
            "тормозные части",
            [
              "8708309100",
              "8708"
            ]
          ],
          [
            "кузовные части",
            [
              "8708299000",
              "8708"
            ]
          ],
          [
            "запчасти авто",
            [
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
          ],
          [
            "табачные изделия",
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
          ],
          [
            "жидкости для вейпа",
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
          ],
          [
            "ром/виски",
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
              "2204210000",
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
          ],
          [
            "игристое вино",
            [
              "2204"
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
              "2710124500",
              "2710"
            ]
          ],
          [
            "дизель",
            [
              "2710194300",
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
          ],
          [
            "керосин",
            [
              "2710"
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
          ],
          [
            "технические масла",
            [
              "2710"
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
          ["лошади", ["0101"]],
          ["крупный рогатый скот", ["0102"]],
          ["свиньи", ["0103"]],
          ["овцы и козы", ["0104"]],
          ["прочие живые животные", ["0106"]],
          ["живой скот", ["01"]],
          ["домашняя птица", ["0105"]],
          ["кролики", ["0106"]]
        ]
      },
      "fruits": {
        "ru": "🍎 Фрукты",
        "uz": "🍎 Mevalar",
        "items": [
          ["бананы", ["0803900000", "0803"]],
          ["яблоки", ["0808100000", "0808"]],
          ["груши", ["0808300000", "0808"]],
          ["апельсины", ["0805100000", "0805"]],
          ["мандарины", ["0805200000", "0805"]],
          ["виноград", ["0806100000", "0806"]],
          ["лимоны", ["0805500000", "0805"]],
          ["свежие фрукты", ["08"]]
        ]
      },
      "vegetables": {
        "ru": "🥔 Овощи",
        "uz": "🥔 Sabzavotlar",
        "items": [
          ["картофель", ["0701900000", "0701"]],
          ["помидоры", ["0702000000", "0702"]],
          ["огурцы", ["0707000000", "0707"]],
          ["лук", ["0703100000", "0703"]],
          ["морковь", ["0706100000", "0706"]],
          ["капуста", ["0704900000", "0704"]],
          ["чеснок", ["0703200000", "0703"]],
          ["свежие овощи", ["07"]]
        ]
      },
      "grain": {
        "ru": "🌾 Зерно и семена",
        "uz": "🌾 Don va urug‘lar",
        "items": [
          ["пшеница", ["1001"]],
          ["ячмень", ["1003"]],
          ["кукуруза", ["1005"]],
          ["рис", ["1006"]],
          ["овёс", ["1004"]],
          ["семена подсолнечника", ["120600"]],
          ["семена льна", ["1204"]],
          ["зерновые культуры", ["10"]]
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
              "9701210000",
              "9701"
            ]
          ],
          [
            "живопись",
            [
              "9701210000",
              "9701"
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
          ],
          [
            "арт-объекты",
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
          ],
          [
            "галерейные работы",
            [
              "9701"
            ]
          ],
          [
            "холсты и картины",
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
          ],
          [
            "производственная техника",
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
          ],
          [
            "спецтехника",
            [
              "87"
            ]
          ]
        ]
      }
    }
  }
}
USER_CTX = {}

MAX_TELEGRAM_MESSAGE = 3800
MAX_RESULTS_SHOW = 5

def ctx(uid: int) -> Dict[str, Any]:
    if uid not in USER_CTX:
        USER_CTX[uid] = {"lang":"ru","role":None,"mode":None,"category":None,"group":None,"pending_form":None,"form_data":{}}
    return USER_CTX[uid]

def reset_mode(uid: int):
    c = ctx(uid)
    c["mode"] = None
    c["category"] = None
    c["group"] = None
    c["pending_form"] = None
    c["form_data"] = {}

def db_conn():
    conn = sqlite3.connect(ANALYTICS_DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,username TEXT,lang TEXT,role TEXT,event_type TEXT,event_value TEXT,created_at TEXT)")
    return conn

def track(uid: int, username: str, lang: str, role: str, etype: str, evalue: str = ""):
    conn = db_conn()
    conn.execute("INSERT INTO events (user_id,username,lang,role,event_type,event_value,created_at) VALUES (?,?,?,?,?,?,?)",
                 (uid, username or "", lang or "", role or "", etype, evalue, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def score_result(item: Dict[str, Any], query: str, category: str = None) -> int:
    q = normalize_text(query)
    name_ru = normalize_text(item.get("name_ru", ""))
    name_uz = normalize_text(item.get("name_uz", ""))
    alias = normalize_text(item.get("alias", ""))
    examples = " ".join(normalize_text(x) for x in item.get("examples", []))
    score = 0

    if item.get("record_kind") == "exact":
        score += 8
    elif item.get("record_kind") in ("alias", "search"):
        score += 5
    elif item.get("record_kind") in ("prefix", "family", "chapter"):
        score += 2

    if category and item.get("category") == category:
        score += 6

    if q == name_ru or q == name_uz or q == alias:
        score += 20
    if q and q in name_ru:
        score += 12
    if q and q in name_uz:
        score += 10
    if q and q in alias:
        score += 10
    if q and q in examples:
        score += 8

    return score

async def send_safe_message(message: types.Message, text_out: str, reply_markup=None):
    chunks = []
    current = ""
    for block in text_out.split("\n\n"):
        candidate = (current + "\n\n" + block).strip() if current else block
        if len(candidate) > MAX_TELEGRAM_MESSAGE:
            if current:
                chunks.append(current)
                current = block
            else:
                # very large single block
                start = 0
                while start < len(block):
                    chunks.append(block[start:start + MAX_TELEGRAM_MESSAGE])
                    start += MAX_TELEGRAM_MESSAGE
                current = ""
        else:
            current = candidate
    if current:
        chunks.append(current)

    for i, chunk in enumerate(chunks):
        await message.answer(chunk, reply_markup=reply_markup if i == len(chunks) - 1 else None)


def analytics_text(lang: str) -> str:
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(DISTINCT user_id) FROM events"); users = cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM events WHERE event_type='message'"); messages = cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM events WHERE event_type='application'"); apps = cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM events WHERE event_type='broker_application'"); bapps = cur.fetchone()[0] or 0
    conn.close()
    if not any([users, messages, apps, bapps]):
        return TXT[lang]["analytics_empty"]
    return f"<b>{TXT[lang]['analytics_title']}</b>\n\n👥 Пользователи: {users}\n💬 Сообщения: {messages}\n📩 Заявки специалисту: {apps}\n💼 PRO-заявки брокеров: {bapps}"

def t(lang: str, key: str) -> str:
    return TXT.get(lang, TXT["ru"]).get(key, key)

def build_lang_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Русский", "O'zbekcha")
    return kb

def role_kb(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "role_physical"), t(lang, "role_legal"))
    kb.add(t(lang, "role_broker"), t(lang, "role_logistics"))
    return kb

def physical_menu(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "chat"), t(lang, "faq"))
    kb.add(t(lang, "docs"), t(lang, "specialist"))
    kb.add(t(lang, "change"))
    return kb

def legal_menu(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "tnved"), t(lang, "exact"))
    kb.add(t(lang, "specialist"), t(lang, "chat"))
    kb.add(t(lang, "back_menu"))
    return kb


def legal_ai_kb(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "faq_1"))
    kb.add(t(lang, "faq_2"))
    kb.add(t(lang, "faq_3"))
    kb.add(t(lang, "faq_4"))
    kb.add(t(lang, "faq_5"))
    kb.add(t(lang, "faq_6"))
    kb.add(t(lang, "ask_own"))
    kb.add(t(lang, "specialist"))
    kb.add(t(lang, "back"), t(lang, "back_menu"))
    return kb

def logistics_menu(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "log_apply"))
    kb.add(t(lang, "log_how"))
    kb.add(t(lang, "back_menu"))
    return kb

def broker_menu(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "broker_cost"))
    kb.add(t(lang, "broker_docs"))
    kb.add(t(lang, "broker_cert"))
    kb.add(t(lang, "broker_tnved_analytics"))
    kb.add(t(lang, "back_menu"))
    return kb

def broker_cost_menu(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "broker_min_avg"), t(lang, "broker_3m"))
    kb.add(t(lang, "back"), t(lang, "back_menu"))
    return kb

def category_kb(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for cid, cat in TREE.items():
        kb.add(cat[lang])
    kb.add(t(lang, "back_menu"))
    return kb

def group_kb(lang: str, cid: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for gid, g in TREE[cid]["groups"].items():
        kb.add(g[lang])
    kb.add(t(lang, "back"), t(lang, "back_menu"))
    return kb

def item_kb(lang: str, cid: str, gid: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for item_name, _codes in TREE[cid]["groups"][gid]["items"]:
        kb.add(item_name)
    kb.add(t(lang, "back"), t(lang, "back_menu"))
    return kb

def normalize_code(v: str) -> str:
    return "".join(ch for ch in str(v) if ch.isdigit())

def normalize_text(v: str) -> str:
    return re.sub(r"\s+", " ", str(v).strip().lower())

DB_FILES = [
    "product_db_part1.json",
    "product_db_part2.json",
    "product_db_part3.json",
    "product_db_part4.json",
    "product_db_part5.json",
    "product_db_part6.json",
]

RECORDS = []
for db_file in DB_FILES:
    db_path = os.path.join(BASE_DIR, db_file)
    print(f"Loading DB file: {db_path}")
    with open(db_path, "r", encoding="utf-8") as f:
        RECORDS.extend(json.load(f))

print(f"Loaded records: {len(RECORDS)}")

# hard aliases for common user words
RECORDS.extend([
    {
        "id": "manual_alias_1512_oil",
        "record_kind": "alias",
        "code": "1512",
        "alias": "растительное масло",
        "name_ru": "Растительное масло - шаблон поиска",
        "name_uz": "O‘simlik moyi - qidiruv shabloni",
        "category": "food",
        "duty": "5-15% / уточнить по подгруппе",
        "vat": "12%",
        "excise": "нет / проверять отдельно",
        "util": "нет / проверять отдельно",
        "examples": ["растительное масло", "подсолнечное масло", "масло"],
        "source_main": "ПП-3818 / шаблон"
    },
    {
        "id": "manual_alias_2402_cigarettes",
        "record_kind": "alias",
        "code": "2402",
        "alias": "сигареты",
        "name_ru": "Сигареты - шаблон поиска",
        "name_uz": "Sigaretalar - qidiruv shabloni",
        "category": "tobacco",
        "duty": "30% / уточнить по виду",
        "vat": "12%",
        "excise": "по НК: табак/сигареты/вейп — проверить вид и ставку",
        "util": "нет / проверять отдельно",
        "examples": ["сигареты", "табак", "табачные изделия"],
        "source_main": "ПП-3818 / шаблон"
    }
])

def dedupe(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set(); out = []
    for item in items:
        key = (item.get("code"), item.get("record_kind"), item.get("name_ru"))
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out

def code_search(code: str) -> List[Dict[str, Any]]:
    n = normalize_code(code)
    if not n:
        return []

    exact = [
        r for r in RECORDS
        if normalize_code(r.get("code","")) == n
        and r.get("record_kind") == "exact"
    ]
    if exact:
        return dedupe(exact)[:MAX_RESULTS_SHOW]

    prefix = [
        r for r in RECORDS
        if normalize_code(r.get("code","")).startswith(n)
    ]
    if prefix:
        prefix = sorted(
            prefix,
            key=lambda r: (
                r.get("record_kind") != "exact",
                len(normalize_code(r.get("code", "")))
            )
        )
        return dedupe(prefix)[:MAX_RESULTS_SHOW]

    for size in (8, 6, 4, 2):
        p = n[:size]
        if not p:
            continue
        prefix = [
            r for r in RECORDS
            if normalize_code(r.get("code","")).startswith(p)
        ]
        if prefix:
            prefix = sorted(
                prefix,
                key=lambda r: (
                    r.get("record_kind") != "exact",
                    len(normalize_code(r.get("code", "")))
                )
            )
            return dedupe(prefix)[:MAX_RESULTS_SHOW]

    return []

def text_search(query: str, category: str = None) -> List[Dict[str, Any]]:
    q = normalize_text(query)
    hits = []
    for r in RECORDS:
        score = score_result(r, q, category)
        if score > 0:
            hits.append((score, r))

    hits = sorted(
        hits,
        key=lambda x: (
            x[0],
            len(normalize_code(x[1].get("code", ""))),
            x[1].get("record_kind") == "exact"
        ),
        reverse=True
    )
    return dedupe([r for _, r in hits])[:MAX_RESULTS_SHOW]

def format_item(item, lang, idx):
    name = item.get("name_ru") if lang == "ru" else item.get("name_uz", item.get("name_ru"))

    code_label = "Код" if lang == "ru" else "Kod"
    duty_label = "Пошлина" if lang == "ru" else "Boj"
    vat_label = "НДС" if lang == "ru" else "QQS"
    excise_label = "Акциз" if lang == "ru" else "Aksiz"
    util_label = "♻️ Утильсбор" if lang == "ru" else "♻️ Util yig‘imi"

    base = (
        f"{idx}) <b>{name}</b>\n"
        f"{code_label}: <code>{item.get('code','')}</code>\n"
        f"{duty_label}: {item.get('duty','уточнить')}\n"
        f"{vat_label}: {item.get('vat','12%')}\n"
        f"{excise_label}: {item.get('excise','нет')}\n"
        f"{util_label}: {item.get('util','нет')}\n"
        f"{t(lang, 'source')}: {item.get('source_main','локальная база')}\n"
    )

    if lang == "ru":
        warning = (
            "\n⚠️ Ставки могут изменяться:\n"
            "• при наличии сертификата происхождения\n"
            "• в зависимости от страны отправления\n\n"
            "📌 Для точного расчёта уточните у специалиста\n"
        )
    else:
        warning = (
            "\n⚠️ Stavkalar o‘zgarishi mumkin:\n"
            "• kelib chiqish sertifikati mavjud bo‘lsa\n"
            "• jo‘natilgan davlatga qarab\n\n"
            "📌 Aniq hisob-kitob uchun mutaxassisga murojaat qiling\n"
        )

    return base + warning

def ai_hint(query: str, items: List[Dict[str, Any]], lang: str) -> str:
    if not client or not items:
        return ""
    try:
        data = [{"code":i.get("code"),"name":i.get("name_ru"),"duty":i.get("duty"),"vat":i.get("vat"),"excise":i.get("excise"),"util":i.get("util")} for i in items[:4]]
        prompt = f"Ответь кратко на {'русском' if lang=='ru' else 'узбекском'} языке. Не придумывай новых кодов. Запрос: {query}. Данные: {json.dumps(data, ensure_ascii=False)}"
        resp = client.responses.create(model=OPENAI_MODEL, input=prompt)
        return (resp.output_text or "").strip()
    except Exception:
        return ""


def extract_code_from_text(text: str) -> str:
    m = re.search(r"\b\d{4,10}\b", text or "")
    return m.group(0) if m else ""

def looks_like_customs_question(text: str) -> bool:
    q = normalize_text(text)
    keywords = [
        "тн вэд", "код", "импорт", "экспорт", "документ", "документы",
        "сертифик", "пошлин", "ндс", "акциз", "утиль", "тамож",
        "ставк", "оформлен", "декларац", "товар", "tn ved", "boj", "qqs"
    ]
    return any(k in q for k in keywords) or bool(extract_code_from_text(text))

def format_rates_for_ai(items: List[Dict[str, Any]], lang: str) -> str:
    if not items:
        return ""
    return "\n".join(format_item(item, lang, i) for i, item in enumerate(items[:MAX_RESULTS_SHOW], 1))

def ai_comment_with_db(query: str, items: List[Dict[str, Any]], lang: str) -> str:
    if not client:
        return ""
    try:
        data = [{"code":i.get("code"),"name":i.get("name_ru"),"duty":i.get("duty"),"vat":i.get("vat"),"excise":i.get("excise"),"util":i.get("util")} for i in items[:MAX_RESULTS_SHOW]]
        prompt = (
            f"Ответь кратко на {'русском' if lang=='ru' else 'узбекском'} языке. "
            "Ты помощник по таможенным вопросам Узбекистана. "
            "Сначала опирайся на найденные ставки и коды. "
            "Не скрывай пошлины, НДС, акциз и утильсбор. "
            "Потом дай короткий комментарий и один уточняющий вопрос. "
            f"Запрос пользователя: {query}. Данные: {json.dumps(data, ensure_ascii=False)}"
        )
        resp = client.responses.create(model=OPENAI_MODEL, input=prompt)
        return (resp.output_text or "").strip()
    except Exception:
        logging.exception("ai_comment_with_db failed")
        return ""


def faq_answer(text: str, lang: str) -> str:
    if text == t(lang, "faq_1"):
        return (
            "Обычно для импорта нужны:\n• контракт\n• инвойс\n• упаковочный лист\n• транспортные документы\n• при необходимости сертификаты и разрешительные документы\n\nУточните, пожалуйста: о каком товаре идёт речь?"
            if lang == "ru" else
            "Import uchun odatda kerak bo‘ladi:\n• kontrakt\n• invoys\n• qadoqlash varaqasi\n• transport hujjatlari\n• zarur bo‘lsa sertifikat va ruxsatnomalar\n\nIltimos, qaysi tovar haqida gap ketayotganini yozing?"
        )
    if text == t(lang, "faq_2"):
        return (
            "Обычно для экспорта нужны:\n• контракт\n• инвойс\n• упаковочный лист\n• транспортные документы\n• при необходимости разрешительные документы\n\nУточните, пожалуйста: о каком товаре идёт речь?"
            if lang == "ru" else
            "Eksport uchun odatda kerak bo‘ladi:\n• kontrakt\n• invoys\n• qadoqlash varaqasi\n• transport hujjatlari\n• zarur bo‘lsa ruxsatnomalar\n\nIltimos, qaysi tovar haqida gap ketayotganini yozing?"
        )
    if text == t(lang, "faq_3"):
        return (
            "Для импорта в зависимости от товара могут понадобиться:\n• сертификат соответствия\n• санитарно-эпидемиологическое заключение\n• разрешительные документы\n• декларация соответствия\n\nУточните, пожалуйста: о каком товаре идёт речь?"
            if lang == "ru" else
            "Importda tovarga qarab quyidagilar kerak bo‘lishi mumkin:\n• muvofiqlik sertifikati\n• sanitariya-epidemiologik xulosa\n• ruxsatnoma\n• deklaratsiya\n\nIltimos, qaysi tovar haqida gap ketayotganini yozing?"
        )
    if text == t(lang, "faq_4"):
        return (
            "Код ТН ВЭД определяется по назначению, составу, материалу, характеристикам и правилам классификации.\n\nУточните, пожалуйста: какой именно товар нужно определить?"
            if lang == "ru" else
            "TN VED kodi vazifa, tarkib, material, xususiyatlar va tasniflash qoidalari bo‘yicha aniqlanadi.\n\nQaysi tovar uchun kod aniqlash kerak?"
        )
    if text == t(lang, "faq_5"):
        return (
            "При импорте обычно применяются:\n• пошлина\n• НДС\n• по некоторым товарам акциз\n• по отдельным товарам утильсбор\n\nУточните, пожалуйста: вы хотите расчёт по конкретному товару?"
            if lang == "ru" else
            "Importda odatda quyidagilar qo‘llanadi:\n• boj\n• QQS\n• ayrim tovarlarda aksiz\n• ayrim tovarlarda util yig‘imi\n\nAniq tovar bo‘yicha hisob-kitob kerakmi?"
        )
    return ""

def physical_answer(q: str, lang: str) -> str:
    q = normalize_text(q)
    if any(x in q for x in ["телефон","iphone","смартфон","phone"]):
        return "Для физлица важны лимит, личное пользование и IMEI-регистрация." if lang == "ru" else "Jismoniy shaxs uchun limit, shaxsiy foydalanish va IMEI ro‘yxatdan o‘tkazish muhim."
    if any(x in q for x in ["авто","машин","byd","tesla","gibrid","электро","mashina","avto"]):
        return "Для физлица по авто важны тип, возраст, объём двигателя, документы и цель ввоза." if lang == "ru" else "Jismoniy shaxs uchun avto bo‘yicha turi, yoshi, dvigatel hajmi, hujjatlar va olib kirish maqsadi muhim."
    return t(lang, "physical_no_calc")

async def send_main_menu(message: types.Message, uid: int):
    c = ctx(uid); lang = c["lang"]; role = c["role"]
    reset_mode(uid); c["lang"] = lang; c["role"] = role
    if role == "physical":
        await message.answer(t(lang, "saved"), reply_markup=physical_menu(lang))
    elif role == "legal":
        await message.answer(t(lang, "saved") + "\n\n" + t(lang, "role_legal_ready"), reply_markup=legal_menu(lang))
    elif role == "broker":
        await message.answer(t(lang, "broker_intro"), reply_markup=broker_menu(lang))
    elif role == "logistics":
        await message.answer(t(lang, "log_intro"), reply_markup=logistics_menu(lang))
    else:
        await message.answer(t(lang, "choose_role"), reply_markup=role_kb(lang))

async def on_startup(_):
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass

@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    USER_CTX[message.from_user.id] = {"lang":"ru","role":None,"mode":"choose_lang","category":None,"group":None,"pending_form":None,"form_data":{}}
    await message.answer(TXT["ru"]["choose_lang"], reply_markup=build_lang_kb())

@dp.message_handler(commands=["myid"])
async def myid_cmd(message: types.Message):
    await message.answer(f"Ваш ID: <code>{message.from_user.id}</code>")

@dp.message_handler(commands=["analytics","stats"])
async def analytics_cmd(message: types.Message):
    if ADMIN_CHAT_ID and str(message.from_user.id) != str(ADMIN_CHAT_ID):
        return
    await message.answer(analytics_text(ctx(message.from_user.id)["lang"]))

@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def router(message: types.Message):
    uid = message.from_user.id
    username = message.from_user.username or ""
    c = ctx(uid); lang = c["lang"]; role = c["role"]; text = message.text.strip()
    track(uid, username, lang, role or "", "message", text)

    if text in ["Русский", "O'zbekcha"]:
        c["lang"] = "ru" if text == "Русский" else "uz"
        c["mode"] = "choose_role"
        await message.answer(t(c["lang"], "lang_saved") + "\n" + t(c["lang"], "choose_role"), reply_markup=role_kb(c["lang"]))
        return

    lang = c["lang"]

    if text in [t(lang, "role_physical"), t(lang, "role_legal"), t(lang, "role_broker"), t(lang, "role_logistics")]:
        c["role"] = "physical" if text == t(lang, "role_physical") else "legal" if text == t(lang, "role_legal") else "broker" if text == t(lang, "role_broker") else "logistics"
        c["mode"] = None
        track(uid, username, lang, c["role"], "role_selected", c["role"])
        await send_main_menu(message, uid)
        return

    if text == t(lang, "change"):
        reset_mode(uid); c["role"] = None; c["mode"] = "choose_lang"
        await message.answer(t(lang, "choose_lang"), reply_markup=build_lang_kb())
        return

    if text == t(lang, "back_menu"):
        if c.get("role") == "broker":
            reset_mode(uid)
            await message.answer(t(lang, "broker_intro"), reply_markup=broker_menu(lang))
            return
        if c.get("role") == "logistics":
            reset_mode(uid)
            await message.answer(t(lang, "log_intro"), reply_markup=logistics_menu(lang))
            return
        await send_main_menu(message, uid)
        return

    if text == t(lang, "back"):
        if c.get("role") == "broker":
            reset_mode(uid)
            await message.answer(t(lang, "broker_intro"), reply_markup=broker_menu(lang))
            return
        if c.get("role") == "logistics":
            reset_mode(uid)
            await message.answer(t(lang, "log_intro"), reply_markup=logistics_menu(lang))
            return
        if c["mode"] == "legal_chat":
            await message.answer(t(lang, "ai_intro"), reply_markup=legal_ai_kb(lang))
            return
        if c["mode"] == "legal_group":
            c["mode"] = "legal_category"
            await message.answer(t(lang, "pick_category"), reply_markup=category_kb(lang))
            return
        if c["mode"] == "legal_item":
            c["mode"] = "legal_group"
            await message.answer(t(lang, "pick_group"), reply_markup=group_kb(lang, c["category"]))
            return
        await send_main_menu(message, uid)
        return

    if text == t(lang, "specialist"):
        reset_mode(uid); c["pending_form"] = "specialist_name"
        await message.answer(t(lang, "specialist_intro") + "\n\n" + t(lang, "enter_name"))
        return

    if role == "physical":
        if text == t(lang, "faq"):
            await message.answer(TXT[lang]["faq_intro"], reply_markup=physical_menu(lang)); return
        if text == t(lang, "docs"):
            await message.answer(TXT[lang]["docs_physical"], reply_markup=physical_menu(lang)); return
        if text == t(lang, "chat"):
            reset_mode(uid); c["mode"] = "physical_chat"
            await message.answer(t(lang, "physical_intro"), reply_markup=physical_menu(lang)); return
        if text in [t(lang, "tnved"), t(lang, "exact"), t(lang, "broker_cost")]:
            await message.answer(t(lang, "physical_no_calc"), reply_markup=physical_menu(lang)); return

    if role == "legal":
        if text == t(lang, "docs"):
            await message.answer(TXT[lang]["docs_legal"], reply_markup=legal_menu(lang)); return
        if text == t(lang, "chat"):
            reset_mode(uid); c["mode"] = "legal_chat"
            await message.answer(t(lang, "ai_intro"), reply_markup=legal_ai_kb(lang)); return
        if text == t(lang, "tnved"):
            reset_mode(uid); c["mode"] = "legal_category"
            await message.answer(t(lang, "pick_category"), reply_markup=category_kb(lang)); return
        if text == t(lang, "exact"):
            reset_mode(uid); c["mode"] = "exact_code"
            await message.answer(t(lang, "enter_code"), reply_markup=legal_menu(lang)); return
        if text == t(lang, "broker_cost"):
            c["role"] = "broker"
            reset_mode(uid)
            await message.answer(t(lang, "broker_intro"), reply_markup=broker_menu(lang))
            return
        if text == "📊 Analytics" and (not ADMIN_CHAT_ID or str(uid) == str(ADMIN_CHAT_ID)):
            await message.answer(analytics_text(lang), reply_markup=legal_menu(lang))
            return

    if role == "broker":
        if text == t(lang, "broker_cost"):
            reset_mode(uid); c["mode"] = "broker_service"
            await message.answer(t(lang, "broker_pick"), reply_markup=broker_cost_menu(lang))
            return
        if text == t(lang, "broker_docs"):
            c["form_data"] = {"service": t(lang, "service_docs")}; c["pending_form"] = "broker_name"; c["mode"] = None
            await message.answer(t(lang, "broker_paid") + "\n\n" + t(lang, "enter_name"), reply_markup=broker_menu(lang))
            return
        if text == t(lang, "broker_cert"):
            c["form_data"] = {"service": t(lang, "service_cert")}; c["pending_form"] = "broker_name"; c["mode"] = None
            await message.answer(t(lang, "broker_paid") + "\n\n" + t(lang, "enter_name"), reply_markup=broker_menu(lang))
            return
        if text == t(lang, "broker_tnved_analytics"):
            c["form_data"] = {"service": t(lang, "service_tnved_analytics")}; c["pending_form"] = "broker_name"; c["mode"] = None
            await message.answer(t(lang, "broker_paid") + "\n\n" + t(lang, "enter_name"), reply_markup=broker_menu(lang))
            return

    if c["mode"] == "legal_category":
        for cid, cat in TREE.items():
            if text == cat[lang]:
                c["category"] = cid
                c["mode"] = "legal_group"
                await message.answer(t(lang, "pick_group"), reply_markup=group_kb(lang, cid))
                return
        await message.answer(t(lang, "pick_category"), reply_markup=category_kb(lang))
        return

    if c["mode"] == "legal_group":
        for gid, g in TREE[c["category"]]["groups"].items():
            if text == g[lang]:
                c["group"] = gid
                c["mode"] = "legal_item"
                await message.answer(t(lang, "pick_item"), reply_markup=item_kb(lang, c["category"], gid))
                return
        await message.answer(t(lang, "pick_group"), reply_markup=group_kb(lang, c["category"]))
        return

    if c["mode"] == "legal_item":
        selected_codes = None
        selected_title = None
        for item_name, codes in TREE[c["category"]]["groups"][c["group"]]["items"]:
            if normalize_text(text) == normalize_text(item_name):
                selected_codes = codes
                selected_title = item_name
                break

        if selected_codes:
            results = []
            for code in selected_codes:
                hits = code_search(code)
                if hits:
                    results.extend(hits)

            results = dedupe(results)[:6]

            # fallback 1: search by selected title inside chosen category
            if not results and selected_title:
                results = text_search(selected_title, c["category"])

            # fallback 2: search by selected title globally
            if not results and selected_title:
                results = text_search(selected_title)

            # fallback 3: search by each code as text
            if not results:
                for code in selected_codes:
                    results.extend(text_search(code, c["category"]))
                results = dedupe(results)[:6]

            if not results:
                await message.answer(t(lang, "nothing_found"), reply_markup=legal_menu(lang))
                return
            out = f"<b>{t(lang, 'possible')}</b>\n\n"
            for i, item in enumerate(results, 1):
                out += format_item(item, lang, i) + "\n"
            hint = ai_hint(selected_title or text, results, lang)
            if hint:
                out += "\n<b>AI:</b>\n" + hint + "\n"
            out += t(lang, "branch_hint")
            await send_safe_message(message, out, reply_markup=legal_menu(lang))
            return

        results = text_search(text, c["category"])
        if not results:
            await message.answer(t(lang, "nothing_found"), reply_markup=legal_menu(lang))
            return
        out = f"<b>{t(lang, 'possible')}</b>\n\n"
        for i, item in enumerate(results, 1):
            out += format_item(item, lang, i) + "\n"
        hint = ai_hint(text, results, lang)
        if hint:
            out += "\n<b>AI:</b>\n" + hint + "\n"
        out += t(lang, "branch_hint")
        await send_safe_message(message, out, reply_markup=legal_menu(lang))
        return

    if c["mode"] == "exact_code":
        query_code = normalize_code(text)
        if len(query_code) < 4 or len(query_code) > 6:
            await message.answer(t(lang, "enter_code"), reply_markup=legal_menu(lang))
            return

        items = code_search(query_code)
        track(uid, username, lang, role or "", "code_search", query_code)

        if not items:
            items = [r for r in RECORDS if normalize_code(r.get("code", "")).startswith(query_code)]
            items = dedupe(items)[:MAX_RESULTS_SHOW]

        if not items:
            await message.answer(t(lang, "nothing_found"), reply_markup=legal_menu(lang))
            return

        out = f"<b>{t(lang, 'code_result')}</b>\n\n"
        for i, item in enumerate(items[:MAX_RESULTS_SHOW], 1):
            out += format_item(item, lang, i) + "\n"

        hint = ai_hint(text, items[:MAX_RESULTS_SHOW], lang)
        if hint:
            out += "\n<b>AI:</b>\n" + hint
        await send_safe_message(message, out, reply_markup=legal_menu(lang))
        return

    if c["mode"] == "legal_chat":
        faq_text = faq_answer(text, lang)
        if faq_text:
            await message.answer(
                faq_text + "\n\n" + t(lang, "free_specialist"),
                reply_markup=legal_ai_kb(lang)
            )
            return

        if text == t(lang, "faq_6") or text == t(lang, "ask_own"):
            await message.answer("Напишите свой вопрос." if lang == "ru" else "Savolingizni yozing.", reply_markup=legal_ai_kb(lang))
            return

        if not looks_like_customs_question(text):
            await message.answer(t(lang, "only_customs"), reply_markup=legal_ai_kb(lang))
            return

        found_code = extract_code_from_text(text)
        items = code_search(found_code) if found_code else text_search(text)

        if items:
            rates_block = format_rates_for_ai(items, lang)
            ai_block = ai_comment_with_db(text, items, lang)
            final_text = ""
            if rates_block:
                final_text += ("<b>Найдено в базе:</b>\n\n" if lang == "ru" else "<b>Bazada topildi:</b>\n\n") + rates_block
            if ai_block:
                final_text += "\n\n<b>AI-комментарий:</b>\n" + ai_block
            final_text += "\n\n" + t(lang, "free_specialist")
            await send_safe_message(message, final_text, reply_markup=legal_ai_kb(lang))
            return

        if client:
            try:
                prompt = (
                    f"Ответь кратко на {'русском' if lang=='ru' else 'узбекском'} языке как помощник по таможенным вопросам Узбекистана. "
                    "Отвечай только по теме таможни, импорта, экспорта, ТН ВЭД, документов, сертификации и ставок. "
                    "После ответа задай 1 уточняющий вопрос. "
                    f"Запрос: {text}"
                )
                resp = client.responses.create(model=OPENAI_MODEL, input=prompt)
                ai_text = (resp.output_text or "").strip()
                if ai_text:
                    await message.answer(
                        ai_text + "\n\n" + t(lang, "free_specialist"),
                        reply_markup=legal_ai_kb(lang)
                    )
                    return
            except Exception:
                logging.exception("legal_chat fallback AI failed")

        await message.answer(t(lang, "nothing_found"), reply_markup=legal_ai_kb(lang))
        return

    if c["mode"] == "physical_chat":
        if client:
            try:
                resp = client.responses.create(model=OPENAI_MODEL, input=f"Ответь кратко на {'русском' if lang=='ru' else 'узбекском'} языке как помощник по физлицам Узбекистана. Не показывай брокерские ставки по умолчанию. Запрос: {text}")
                ans = (resp.output_text or "").strip()
                await message.answer(ans or physical_answer(text, lang), reply_markup=physical_menu(lang))
            except Exception:
                await message.answer(physical_answer(text, lang), reply_markup=physical_menu(lang))
        else:
            await message.answer(physical_answer(text, lang), reply_markup=physical_menu(lang))
        return

    if c["pending_form"] == "specialist_name":
        c["form_data"]["name"] = text; c["pending_form"] = "specialist_tg"
        await message.answer(t(lang, "enter_tg")); return

    if c["pending_form"] == "specialist_tg":
        c["form_data"]["tg"] = text; c["pending_form"] = "specialist_phone"
        await message.answer(t(lang, "enter_phone")); return

    if c["pending_form"] == "specialist_phone":
        c["form_data"]["phone"] = text; c["pending_form"] = "specialist_product"
        await message.answer(t(lang, "enter_question")); return

    if c["pending_form"] == "specialist_product":
        c["form_data"]["product"] = text; c["pending_form"] = None
        msg = f"📩 <b>Новая заявка специалисту</b>\n\nИмя: {c['form_data'].get('name','')}\nTelegram: {c['form_data'].get('tg','')}\nТелефон: {c['form_data'].get('phone','')}\nВопрос: {c['form_data'].get('product','')}\nРежим: {role or '-'}\nID: <code>{uid}</code>\nUsername: @{username or '-'}"
        if ADMIN_CHAT_ID:
            try:
                await bot.send_message(int(ADMIN_CHAT_ID), msg)
            except Exception:
                pass
        track(uid, username, lang, role or "", "application", c['form_data'].get('product',''))
        await message.answer(t(lang, "specialist_done"))
        await send_main_menu(message, uid)
        return

    if c["mode"] == "broker_service":
        if text == t(lang, "broker_min_avg"):
            c["form_data"] = {"service": t(lang, "service_min_avg")}; c["pending_form"] = "broker_name"; c["mode"] = None
            await message.answer(t(lang, "broker_paid") + "\n\n" + t(lang, "enter_name"), reply_markup=broker_menu(lang)); return
        if text == t(lang, "broker_3m"):
            c["form_data"] = {"service": t(lang, "service_3m")}; c["pending_form"] = "broker_name"; c["mode"] = None
            await message.answer(t(lang, "broker_paid") + "\n\n" + t(lang, "enter_name"), reply_markup=broker_menu(lang)); return
        await message.answer(t(lang, "broker_pick"), reply_markup=broker_cost_menu(lang)); return

    if c["pending_form"] == "broker_name":
        c["form_data"]["name"] = text; c["pending_form"] = "broker_product"
        await message.answer(t(lang, "enter_product"), reply_markup=broker_menu(lang)); return

    if c["pending_form"] == "broker_product":
        c["form_data"]["product"] = text; c["pending_form"] = "broker_country"
        await message.answer(t(lang, "enter_country"), reply_markup=broker_menu(lang)); return

    if c["pending_form"] == "broker_country":
        c["form_data"]["country"] = text; c["pending_form"] = "broker_comment"
        await message.answer(t(lang, "enter_comment"), reply_markup=broker_menu(lang)); return

    if c["pending_form"] == "broker_comment":
        c["form_data"]["comment"] = text; c["pending_form"] = None
        msg = f"💼 <b>Новая PRO-заявка</b>\n\nУслуга: {c['form_data'].get('service','')}\nИмя: {c['form_data'].get('name','')}\nТовар: {c['form_data'].get('product','')}\nСтрана: {c['form_data'].get('country','')}\nКомментарий: {c['form_data'].get('comment','')}\nID: <code>{uid}</code>\nUsername: @{username or '-'}"
        if ADMIN_CHAT_ID:
            try:
                await bot.send_message(int(ADMIN_CHAT_ID), msg)
            except Exception:
                pass
        track(uid, username, lang, role or "", "broker_application", c['form_data'].get('service',''))
        await message.answer(t(lang, "application_sent"), reply_markup=broker_menu(lang))
        await send_main_menu(message, uid)
        return

    if role == "logistics":
        if text == t(lang, "log_how"):
            await message.answer(t(lang, "log_how_text"), reply_markup=logistics_menu(lang))
            return
        if text == t(lang, "log_apply"):
            reset_mode(uid); c["pending_form"] = "log_name"
            await message.answer(t(lang, "enter_name"), reply_markup=logistics_menu(lang))
            return

    if c["pending_form"] == "log_name":
        c["form_data"]["name"] = text; c["pending_form"] = "log_tg"
        await message.answer(t(lang, "enter_tg"), reply_markup=logistics_menu(lang)); return

    if c["pending_form"] == "log_tg":
        c["form_data"]["tg"] = text; c["pending_form"] = "log_phone"
        await message.answer(t(lang, "enter_phone"), reply_markup=logistics_menu(lang)); return

    if c["pending_form"] == "log_phone":
        c["form_data"]["phone"] = text; c["pending_form"] = "log_from"
        await message.answer(t(lang, "enter_from"), reply_markup=logistics_menu(lang)); return

    if c["pending_form"] == "log_from":
        c["form_data"]["from"] = text; c["pending_form"] = "log_to"
        await message.answer(t(lang, "enter_to"), reply_markup=logistics_menu(lang)); return

    if c["pending_form"] == "log_to":
        c["form_data"]["to"] = text; c["pending_form"] = "log_product"
        await message.answer("Какой товар:" if lang=="ru" else "Qanday tovar:", reply_markup=logistics_menu(lang)); return

    if c["pending_form"] == "log_product":
        c["form_data"]["product"] = text; c["pending_form"] = "log_weight"
        await message.answer(t(lang, "enter_weight"), reply_markup=logistics_menu(lang)); return

    if c["pending_form"] == "log_weight":
        c["form_data"]["weight"] = text; c["pending_form"] = "log_comment"
        await message.answer(t(lang, "enter_more"), reply_markup=logistics_menu(lang)); return

    if c["pending_form"] == "log_comment":
        c["form_data"]["comment"] = text; c["pending_form"] = None
        msg = f"🚚 <b>Новая заявка по логистике</b>\n\nИмя: {c['form_data'].get('name','')}\nTelegram: {c['form_data'].get('tg','')}\nТелефон: {c['form_data'].get('phone','')}\nОткуда: {c['form_data'].get('from','')}\nКуда: {c['form_data'].get('to','')}\nТовар: {c['form_data'].get('product','')}\nВес / объём: {c['form_data'].get('weight','')}\nКомментарий: {c['form_data'].get('comment','')}\nID: <code>{uid}</code>\nUsername: @{username or '-'}"
        if ADMIN_CHAT_ID:
            try:
                await bot.send_message(int(ADMIN_CHAT_ID), msg)
            except Exception:
                pass
        track(uid, username, lang, role or "", "logistics_application", c['form_data'].get('product',''))
        await message.answer(t(lang, "log_done"), reply_markup=logistics_menu(lang))
        await send_main_menu(message, uid)
        return

    if role == "physical":
        await message.answer(t(lang, "physical_no_calc"), reply_markup=physical_menu(lang))
    elif role == "legal":
        await message.answer(t(lang, "saved"), reply_markup=legal_menu(lang))
    elif role == "broker":
        await message.answer(t(lang, "broker_intro"), reply_markup=broker_menu(lang))
    elif role == "logistics":
        await message.answer(t(lang, "log_intro"), reply_markup=logistics_menu(lang))
    else:
        await message.answer(t(lang, "choose_lang"), reply_markup=build_lang_kb())

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
