
import os, re, json, logging, sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from modules.specialist_admin import (
    apply_extra_txt,
    admin_apps_menu_kb as _admin_apps_menu_kb,
    admin_apps_text as _admin_apps_text,
    admin_app_status_kb as _admin_app_status_kb,
    get_application as _get_application,
    is_admin as _helper_is_admin,
    send_specialist_application_to_admin as _send_specialist_application_to_admin,
    status_text as _status_text,
    update_application_status as _update_application_status,
)

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
client = None
if OPENAI_API_KEY and OpenAI:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        client = None

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
        "broker_min_avg":"📉 1 год: минимальная и средняя стоимость",
        "broker_3m":"📊 3 месяца: конкретная база по товару",
        "back_menu":"⬅️ Назад в главное меню",
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
        "legal_intro":"Для юридических лиц\n\nНаши специалисты имеют 10–15 лет опыта в таможенной сфере и помогают по вопросам:\n\n• ТН ВЭД и ставок\n• импорта и экспорта\n• документов\n• сертификации\n\nВы можете получить:\n• общую информацию сразу в боте\n• точный ответ по вашему кейсу бесплатно через специалиста\n\n📩 Специалист отвечает в течение дня\n\nВыберите нужный раздел:",
        "physical_no_calc":"В режиме физлица я не показываю брокерские коды и ставки по умолчанию.",
        "broker_intro":"Профессиональная поддержка для брокеров и импортеров\n\nНаши эксперты имеют 10–15 лет практического опыта в таможенной сфере Узбекистана.\n\nМы помогаем:\n• избежать переплат по таможенной стоимости\n• проверить документы до подачи\n• заранее понять требования по сертификации\n• подготовить кейс для специалиста\n\nВыберите услугу:",
        "broker_pick":"Выберите услугу:",
        "broker_paid":"Это платная услуга. После заявки специалист свяжется с вами.",
        "enter_name":"Введите ваше имя:",
        "enter_product":"Напишите товар / запрос:",
        "enter_country":"Укажите страну происхождения или отправления:",
        "enter_comment":"Добавьте комментарий, если нужно:",
        "service_min_avg":"Мин. и средняя стоимость",
        "service_3m":"База за 3 месяца",
        "application_sent":"✅ Ваша заявка отправлена.",
        "broker_cost_text":"Анализ таможенной стоимости\n\nНеверная таможенная стоимость может привести к переплатам, корректировкам и задержкам при оформлении.\n\nМы предлагаем 2 платные услуги:\n\n1) Узнать самую низкую таможенную стоимость — 300 000 сум\n2) Узнать конкретную базу за последние 3 месяца — 600 000 сум\n\nВыберите нужную услугу:",
        "broker_cost_low":"1️⃣ Самая низкая таможенная стоимость",
        "broker_cost_3m":"2️⃣ База за последние 3 месяца",
        "broker_docs_text":"Проверка документов перед подачей ГТД\n\nМногие бизнесмены теряют деньги и время из-за ошибок в документах при таможенном оформлении.\n\nДаже небольшая ошибка в:\n• инвойсе\n• контракте\n• упаковочном листе\n• транспортных документах\n\nможет привести к:\n• задержке груза\n• дополнительным проверкам\n• штрафам\n• увеличению таможенной стоимости\n\n👨‍💼 Наши специалисты с опытом 10–15 лет:\n• проверят ваши документы перед подачей\n• найдут ошибки и риски\n• дадут рекомендации по исправлению\n\n⏱ Срок проверки: до 3 часов\n💰 Стоимость: 200 000 сум\n\nНажмите кнопку ниже, чтобы отправить документы на проверку.",
        "broker_docs_apply":"📝 Оставить заявку на проверку",
        "broker_finish_upload":"✅ Завершить загрузку документов",
        "broker_send_more_docs":"Загрузите документы по одному сообщением:\n• TTH / CMR\n• Invoice\n• Packing List\n• Контракт\n• дополнительные документы (до 2–3 шт.)\n\nКогда закончите, нажмите «✅ Завершить загрузку документов».",
        "broker_need_doc":"Пожалуйста, загрузите хотя бы 1 документ перед завершением.",
        "broker_doc_saved":"Документ сохранён. Можете отправить следующий файл или нажать «✅ Завершить загрузку документов».",
        "broker_cert_text":"Нюансы по сертификации\n\nСертификация — один из самых важных этапов перед импортом. Ошибка на этом этапе может привести к задержке груза, лишним расходам и потере времени.\n\nМы предлагаем 2 услуги:\n\n1) Узнать по ТН ВЭД, на какие сертификаты попадает товар — 200 000 сум\n2) Подать заявку от имени импортёра на конкретную услугу\n\nНаши специалисты имеют хороший опыт в этой сфере и помогут правильно направить ваш запрос.\n\nВыберите нужную услугу:",
        "broker_cert_check":"1️⃣ Узнать сертификаты по ТН ВЭД",
        "broker_cert_apply":"2️⃣ Подать заявку от имени импортёра",
        "broker_cert_check_text":"Узнать по ТН ВЭД, на какие сертификаты попадает ваш товар\n\nМы проверим, какие сертификаты, разрешения или согласования могут потребоваться именно по вашему коду ТН ВЭД.\n\n💰 Стоимость: 200 000 сум\n\nНажмите кнопку ниже, чтобы оставить заявку.",
        "broker_cert_apply_text":"Подача заявки от имени импортёра\n\nНаши специалисты имеют хороший опыт по таким услугам и помогут правильно оформить запрос.\n\nМы хорошо знаем порядок работы и нюансы подачи, поэтому ваш запрос будет приоритетно подготовлен для дальнейшей работы.\n\n⏱ Время ответа зависит от конкретного товара.\n\nВыберите учреждение:",
        "broker_cert_apply_btn":"📝 Оставить заявку",
        "broker_agency_plant":"1️⃣ Агентство по карантину и защите растений Республики Узбекистан",
        "broker_agency_vet":"2️⃣ Государственный комитет ветеринарии и развития животноводства Республики Узбекистан",
        "broker_agency_cert":"3️⃣ Аккредитованные органы по сертификации",
        "broker_service_quarantine":"1. Карантинное разрешение (на импорт)",
        "broker_service_akd":"2. АКД",
        "broker_service_vet":"1. Ветеринарное разрешение",
        "broker_service_conformity":"1. Сертификат соответствия",
        "broker_analytics_text":"Аналитика по ТН ВЭД коду\n\nУзнать и анализировать рынок — это одна из самых важных частей бизнеса.\n\nПо ТН ВЭД коду можно понять:\n• сколько и какие товары проходили за год\n• активность по конкретной нише\n• общий объём движения товара\n\nЭто помогает принимать более точные решения перед импортом.\n\n💰 Стоимость услуги: 1 000 000 сум за 1 код\n\nНажмите кнопку ниже, чтобы оставить заявку.",
        "broker_analytics_apply":"📝 Оставить заявку на аналитику",
        "enter_tnved":"Введите код ТН ВЭД товара:",
        "enter_description":"Напишите описание товара:",
        "enter_dispatch_country":"Укажите страну отправления:",
        "enter_origin_country":"Укажите страну происхождения:",
        "enter_comment_optional":"Добавьте комментарий, если нужно. Если нет — напишите: нет",
        "enter_phone_broker":"Введите номер телефона:",
        "choose_agency":"Выберите учреждение:",
        "choose_service":"Выберите услугу:",
        "broker_application_received":"✅ Ваша заявка отправлена.\n\nНаш специалист свяжется с вами.",
        "broker_application_received_3h":"✅ Ваша заявка принята.\n\nСпециалист проверит документы и ответит в течение 3 часов.",
        "broker_admin_confirm":"✅ Заявка получена",
        "broker_client_confirmed":"✅ Ваша заявка получена специалистом.\nМы уже взяли её в работу.",
        "analytics_empty":"Статистика пока пустая.",
        "analytics_title":"📊 Аналитика бота",
        "role_legal_ready":"Для юридических лиц: выберите нужный раздел.",
        "faq_intro":"Частые вопросы:\n• сколько телефонов можно ввезти\n• лимит через аэропорт\n• IMEI регистрация\n• временный ввоз авто\n• документы для юрлица\n• как определить код ТН ВЭД",
        "docs_physical":"Документы для физлица:\n• паспорт\n• чеки/инвойс\n• транспортные документы\n• при необходимости декларация",
        "docs_legal":"Документы для юрлица:\n• контракт\n• инвойс\n• упаковочный лист\n• транспортные документы\n• сертификаты/разрешения\n• код ТН ВЭД",
        "specialist_intro":"Связь со специалистом\n\nОпишите ваш вопрос, и мы передадим его специалисту.\n\nСпециалист ответит бесплатно в течение дня.",
        "enter_tg":"Укажите ваш Telegram (username или номер):",
        "enter_phone":"Введите номер телефона:",
        "enter_question":"Опишите ваш вопрос:",
        "specialist_done":"✅ Ваша заявка отправлена.\n\nСпециалист свяжется с вами в течение дня.",
        "ai_intro":"Чат с помощником\n\nВыберите готовый вопрос или напишите свой.\n\nПомощник отвечает по темам:\n• ТН ВЭД\n• ставки\n• импорт и экспорт\n• документы\n• сертификация\n• таможенные платежи",
        "faq_1":"Какие документы нужны для импорта?",
        "faq_2":"Какие документы нужны для экспорта?",
        "faq_3":"Какие сертификаты нужны для импорта?",
        "faq_4":"Как определяется код ТН ВЭД?",
        "faq_5":"Какие платежи при импорте?",
        "faq_6":"Задать свой вопрос",
        "ask_own":"✍️ Задать свой вопрос",
        "free_specialist":"Точную информацию по вашему кейсу можно получить бесплатно через специалиста.",
        "only_customs":"Я помощник только по вопросам таможни, импорта, экспорта, ТН ВЭД, документов и сертификации.",
        "log_intro":"Логистика\n\nМы собираем предложения от проверенных логистов, а вы выбираете лучший вариант.\n\nЧто вы получаете:\n• доставка из Китая, Кореи, Европы и СНГ\n• одна заявка → несколько предложений\n• выбор по цене и срокам\n\nБонус:\nпомощь по документам и растаможке\n\nУ нас есть 10 проверенных логистов.\nМы подберём для вас 3–4 лучших варианта.",
        "log_apply":"📝 Оставить заявку",
        "log_how":"ℹ️ Как это работает",
        "log_how_text":"Как это работает:\n\n1. Вы оставляете заявку\n2. Мы передаём её логистам\n3. Получаем предложения\n4. Отправляем вам 3–4 варианта\n\nВы сами выбираете лучшую цену и сроки.",
        "enter_from":"Откуда груз:",
        "enter_to":"Куда доставить:",
        "enter_weight":"Вес или объём груза:",
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
        "broker_cert":"3️⃣ Sertifikatlash bo‘yicha nuanslar",
        "broker_tnved_analytics":"4️⃣ TN VED kod bo‘yicha analitika",
        "broker_min_avg":"📉 Min. va o‘rtacha qiymat",
        "broker_3m":"📊 Oxirgi 3 oy bazasi",
        "back_menu":"⬅️ Asosiy menyuga qaytish",
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
        "legal_intro":"Yuridik shaxslar uchun\n\nMutaxassislarimiz bojxona sohasida 10–15 yillik tajribaga ega va quyidagi masalalarda yordam beradi:\n\n• TN VED va stavkalar\n• import va eksport\n• hujjatlar\n• sertifikatlash\n\nSiz quyidagilarni olishingiz mumkin:\n• bot ichida umumiy ma’lumot\n• aynan sizning holatingiz bo‘yicha mutaxassisdan bepul aniq javob\n\n📩 Mutaxassis bir kun ichida javob beradi\n\nKerakli bo‘limni tanlang:",
        "physical_no_calc":"Jismoniy shaxs rejimida brokerlik kodlari va stavkalarini odatda ko‘rsatmayman.",
        "broker_intro":"Brokerlar uchun bo‘lim (PRO).\n\nPullik xizmat mavjud:",
        "broker_pick":"Xizmatni tanlang:",
        "broker_paid":"Bu pullik xizmat. Ariza yuborilgach, mutaxassis siz bilan bog‘lanadi.",
        "enter_name":"Ismingizni kiriting:",
        "enter_product":"Tovar / so‘rovni yozing:",
        "enter_country":"Kelib chiqish yoki jo‘natish davlatini kiriting:",
        "enter_comment":"Kerak bo‘lsa izoh qoldiring:",
        "service_min_avg":"Min. va o‘rtacha qiymat",
        "service_3m":"Oxirgi 3 oy bazasi",
        "application_sent":"✅ Ariza mutaxassisga yuborildi.",
        "broker_cost_text":"Bojxona qiymati tahlili\n\nKerakli xizmatni tanlang:",
        "broker_cost_low":"1️⃣ Eng past bojxona qiymati",
        "broker_cost_3m":"2️⃣ Oxirgi 3 oy bazasi",
        "broker_docs_text":"Hujjatlarni topshirishdan oldin tekshirish\n\n💰 Narx: 200 000 so‘m\n⏱ Javob: 3 soatgacha",
        "broker_docs_apply":"📝 Ariza qoldirish",
        "broker_finish_upload":"✅ Hujjat yuklashni tugatish",
        "broker_send_more_docs":"Hujjatlarni birma-bir yuboring, so‘ng «✅ Hujjat yuklashni tugatish» tugmasini bosing.",
        "broker_need_doc":"Avval kamida bitta hujjat yuklang.",
        "broker_doc_saved":"Hujjat saqlandi. Yana yuborishingiz yoki tugatishingiz mumkin.",
        "broker_cert_text":"Sertifikatlash bo‘yicha xizmatni tanlang:",
        "broker_cert_check":"1️⃣ TN VED bo‘yicha sertifikatlarni bilish",
        "broker_cert_apply":"2️⃣ Importyor nomidan ariza topshirish",
        "broker_cert_check_text":"TN VED bo‘yicha kerakli sertifikatlarni aniqlash\n\n💰 Narx: 200 000 so‘m",
        "broker_cert_apply_text":"Importyor nomidan ariza topshirish\n\nTovar turiga qarab javob muddati farq qiladi.",
        "broker_cert_apply_btn":"📝 Ariza qoldirish",
        "broker_agency_plant":"1️⃣ O‘simliklar karantini va himoyasi agentligi",
        "broker_agency_vet":"2️⃣ Veterinariya qo‘mitasi",
        "broker_agency_cert":"3️⃣ Sertifikatlash organlari",
        "broker_service_quarantine":"1. Karantin ruxsatnomasi (import uchun)",
        "broker_service_akd":"2. AKD",
        "broker_service_vet":"1. Veterinariya ruxsatnomasi",
        "broker_service_conformity":"1. Muvofiqlik sertifikati",
        "broker_analytics_text":"TN VED kod bo‘yicha analitika\n\n💰 Narx: 1 000 000 so‘m / 1 kod",
        "broker_analytics_apply":"📝 Analitika uchun ariza",
        "enter_tnved":"TN VED kodini kiriting:",
        "enter_description":"Tovar tavsifini yozing:",
        "enter_dispatch_country":"Jo‘natish mamlakatini kiriting:",
        "enter_origin_country":"Kelib chiqish mamlakatini kiriting:",
        "enter_comment_optional":"Izoh kiriting. Bo‘lmasa: yo‘q",
        "enter_phone_broker":"Telefon raqamingizni kiriting:",
        "choose_agency":"Muassasani tanlang:",
        "choose_service":"Xizmatni tanlang:",
        "broker_application_received":"✅ Arizangiz yuborildi.\n\nMutaxassis siz bilan bog‘lanadi.",
        "broker_application_received_3h":"✅ Arizangiz qabul qilindi.\n\nMutaxassis 3 soat ichida javob beradi.",
        "broker_admin_confirm":"✅ Ariza olindi",
        "broker_client_confirmed":"✅ Arizangiz mutaxassis tomonidan olindi.\nIshga olindi.",
        "analytics_empty":"Statistika hozircha bo‘sh.",
        "analytics_title":"📊 Bot analitikasi",
        "role_legal_ready":"Yuridik shaxs rejimi: avval kategoriyalar va variantlar, aniq kod uchun alohida tugma.",
        "faq_intro":"Ko‘p beriladigan savollar:\n• nechta telefon olib kirish mumkin\n• aeroport limiti\n• IMEI ro‘yxatdan o‘tkazish\n• vaqtinchalik avto olib kirish\n• yuridik shaxs hujjatlari\n• TN VED kodini aniqlash",
        "docs_physical":"Jismoniy shaxs uchun hujjatlar:\n• pasport\n• chek/invoys\n• transport hujjatlari\n• kerak bo‘lsa deklaratsiya",
        "docs_legal":"Yuridik shaxs uchun hujjatlar:\n• kontrakt\n• invoys\n• qadoqlash varaqasi\n• transport hujjatlari\n• sertifikat/ruxsatnomalar\n• TN VED kodi",
        "specialist_intro":"Mutaxassis bilan aloqa\n\nSavolingizni yozing, biz uni mutaxassisga yuboramiz.\n\nMutaxassis bir kun ichida bepul javob beradi.",
        "enter_tg":"Telegramingizni kiriting (username yoki raqam):",
        "enter_phone":"Telefon raqamingizni kiriting:",
        "enter_question":"Savolingizni yozing:",
        "specialist_done":"✅ Arizangiz yuborildi.\n\nMutaxassis siz bilan bog‘lanadi.",
        "ai_intro":"Yordamchi bilan chat\n\nTayyor savolni tanlang yoki o‘zingiz yozing.\n\nYordamchi quyidagi mavzularda javob beradi:\n• TN VED\n• stavkalar\n• import va eksport\n• hujjatlar\n• sertifikatlash\n• bojxona to‘lovlari",
        "faq_1":"Import uchun qaysi hujjatlar kerak?",
        "faq_2":"Eksport uchun qaysi hujjatlar kerak?",
        "faq_3":"Import uchun qaysi sertifikatlar kerak?",
        "faq_4":"TN VED kodi qanday aniqlanadi?",
        "faq_5":"Importdagi to‘lovlar qanday?",
        "faq_6":"O‘z savolini yozish",
        "ask_own":"✍️ O‘z savolini yozish",
        "free_specialist":"Aniq ma’lumotni mutaxassis orqali bepul olishingiz mumkin.",
        "only_customs":"Men faqat bojxona, import, eksport, TN VED, hujjatlar va sertifikat masalalari bo‘yicha yordamchiman.",
        "log_intro":"Logistika\n\nBiz tekshirilgan logistlardan takliflar yig‘amiz, siz esa eng yaxshi variantni tanlaysiz.\n\nNimalarni olasiz:\n• Xitoy, Koreya, Yevropa va MDHdan yetkazib berish\n• bitta ariza → bir nechta taklif\n• narx va muddat bo‘yicha tanlov\n\nBonus:\nbojxona hujjatlari va rasmiylashtirish bo‘yicha yordam\n\nBizda 10 ta tekshirilgan logist bor.\nSiz uchun 3–4 ta eng mos variantni tanlaymiz.",
        "log_apply":"📝 Ariza qoldirish",
        "log_how":"ℹ️ Qanday ishlaydi",
        "log_how_text":"Qanday ishlaydi:\n\n1. Siz ariza qoldirasiz\n2. Biz uni logistlarga yuboramiz\n3. Takliflarni olamiz\n4. Sizga 3–4 variant yuboramiz\n\nEng yaxshi narx va muddatni o‘zingiz tanlaysiz.",
        "enter_from":"Yuk qayerdan:",
        "enter_to":"Qayerga yetkazilsin:",
        "enter_weight":"Yukning vazni yoki hajmi:",
        "log_done":"✅ Arizangiz qabul qilindi.\n\nVariantlarni tayyorlab siz bilan bog‘lanamiz."
    }
}

TXT["ru"].update({
    "admin_title": "🛠 Админ-панель",
    "admin_open": "🛠 Админка",
    "admin_overview": "📊 Общая статистика",
    "admin_today": "📅 За сегодня",
    "admin_week": "🗓 За 7 дней",
    "admin_popular": "🔥 Популярное",
    "admin_users": "👥 Новые / активные",
    "admin_close": "❌ Закрыть админку",
    "admin_access_denied": "У вас нет доступа к админке.",
    "admin_closed": "Админка закрыта.",
    "admin_empty": "Статистика пока пустая.",
})

TXT["uz"].update({
    "admin_title": "🛠 Admin panel",
    "admin_open": "🛠 Adminka",
    "admin_overview": "📊 Umumiy statistika",
    "admin_today": "📅 Bugun",
    "admin_week": "🗓 7 kun",
    "admin_popular": "🔥 Ommabop",
    "admin_users": "👥 Yangi / faol foydalanuvchilar",
    "admin_close": "❌ Adminkani yopish",
    "admin_access_denied": "Sizda adminkaga kirish huquqi yo‘q.",
    "admin_closed": "Adminka yopildi.",
    "admin_empty": "Statistika hozircha bo‘sh.",
})

apply_extra_txt(TXT)

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
          ],
          [
            "живой скот",
            [
              "01"
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
              "0803900000",
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
          ],
          [
            "свежие фрукты",
            [
              "08"
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



PHYSICAL_FAQ = {
    "ru": {
        "Таможенные правила для физлиц": (
            "Для физических лиц при въезде в Узбекистан действуют нормы беспошлинного ввоза. "
            "Через аэропорты лимит выше, чем через автодорожные пункты. "
            "Также есть отдельные ограничения по алкоголю, табачным изделиям, парфюмерии и некоторым товарам.\n\n"
            "Если хотите, напишите, через какой пункт пропуска вы въезжаете, и я объясню точнее."
        ),
        "Сколько можно ввозить без пошлины": (
            "Это зависит от способа въезда: аэропорт, поезд, авто или пеший переход. "
            "Для личного пользования действуют разные лимиты. "
            "Если напишете, откуда и как именно въезжаете, я отвечу точнее."
        ),
        "Сколько телефонов можно привезти": (
            "Если телефон ввозится для личного пользования, обычно важны количество, частота ввоза и признаки коммерческой партии. "
            "Если это 1 телефон для себя, ситуация обычно проще. "
            "Если телефонов несколько, таможня может расценить это как не для личного пользования.\n\n"
            "Напишите, сколько телефонов и какие модели вы везёте."
        ),
        "Можно ли ввозить лекарства": (
            "Да, для личного пользования лекарства ввозить можно, но важны состав, количество и назначение. "
            "По отдельным препаратам могут потребоваться дополнительные документы или ограничения.\n\n"
            "Напишите название лекарства и количество, я объясню точнее."
        ),
        "Сколько можно вывозить валюты": (
            "Для вывоза наличной валюты действуют установленные правила и лимиты. "
            "Для точного ответа важно понимать сумму и вид валюты.\n\n"
            "Напишите, сколько и какой валюты вы хотите вывезти."
        ),
        "Что будет при превышении нормы": (
            "Если норма беспошлинного ввоза превышена, могут применяться таможенные платежи. "
            "Точный расчёт зависит от товара, стоимости, веса и способа ввоза.\n\n"
            "Напишите, какой именно товар и на какую сумму вы ввозите."
        ),
    },
    "uz": {
        "Jismoniy shaxslar uchun bojxona qoidalari": (
            "Jismoniy shaxslar uchun O‘zbekistonga kirishda bojsiz olib kirish me’yorlari mavjud. "
            "Aeroport, avtoyo‘l, temir yo‘l va boshqa yo‘nalishlarda me’yorlar farq qilishi mumkin. "
            "Shuningdek, alkogol, tamaki, atir-upa va ayrim tovarlar bo‘yicha alohida cheklovlar bor.\n\n"
            "Qaysi post yoki qaysi yo‘l orqali kirayotganingizni yozsangiz, aniqroq tushuntiraman."
        ),
        "Bojsiz qancha olib kirish mumkin": (
            "Bu kirish usuliga bog‘liq: aeroport, poyezd, avtoyo‘l yoki piyoda o‘tish. "
            "Shaxsiy foydalanish uchun turli limitlar qo‘llanadi.\n\n"
            "Qayerdan va qaysi yo‘l bilan kirayotganingizni yozing, aniqroq javob beraman."
        ),
        "Nechta telefon olib kirish mumkin": (
            "Telefonni shaxsiy foydalanish uchun olib kirishda soni, tez-tez olib kirish holati va tijorat alomatlari muhim. "
            "Agar 1 dona telefon o‘zingiz uchun bo‘lsa, odatda masala osonroq bo‘ladi. "
            "Agar bir nechta telefon bo‘lsa, bojxona buni tijorat olib kirish deb baholashi mumkin.\n\n"
            "Nechta telefon va qaysi modellar ekanini yozing."
        ),
        "Dori olib kirish mumkinmi": (
            "Ha, shaxsiy foydalanish uchun dori olib kirish mumkin, lekin tarkibi, miqdori va maqsadi muhim. "
            "Ayrim dori vositalari uchun qo‘shimcha cheklovlar yoki hujjatlar kerak bo‘lishi mumkin.\n\n"
            "Dori nomi va miqdorini yozing, aniqroq tushuntiraman."
        ),
        "Qancha valyuta olib chiqish mumkin": (
            "Naqd valyutani olib chiqish bo‘yicha belgilangan qoidalar va limitlar bor. "
            "Aniq javob uchun summa va valyuta turini bilish kerak.\n\n"
            "Qancha va qaysi valyutani olib chiqmoqchisiz?"
        ),
        "Norma oshsa nima bo‘ladi": (
            "Agar bojsiz me’yor oshsa, bojxona to‘lovlari qo‘llanishi mumkin. "
            "Aniq hisob-kitob tovar turi, qiymati, vazni va olib kirish usuliga bog‘liq.\n\n"
            "Qaysi tovarni va taxminan qanday summada olib kirayotganingizni yozing."
        ),
    }
}

BORDER_POSTS = [{'code': '101',
  'contact': '+99855 502-86-45',
  'info': 'Тошкент шаҳар, Сирғали тумани, "Ислом Каримов номидаги “Тошкент” халқаро аэропорти" Терминал 2',
  'kind': 'border',
  'lat': 41.26061352557067,
  'lon': 69.27932553018901,
  'name': '"Тошкент" халқаро АЭРО чегара божхона пости(Аеропорт)',
  'num': '1'},
 {'code': '3002',
  'contact': '998952014328, 998742247615 (6502,6503)',
  'info': 'Андижон вилояти, Хўжаобод тумани, “Манак” ҚФЙ “Дўстлик” МФЙ',
  'kind': 'border',
  'lat': 40.57304041392973,
  'lon': 72.75951242414465,
  'name': '"Дўстлик" чегара пости (Андижон)',
  'num': '2'},
 {'code': '3003',
  'contact': '998742247615 (6530,6531,6572,6573)',
  'info': 'Андижон шаҳар, Янги айланма кўчаси, 1 уй',
  'kind': 'border',
  'lat': 40.73963255412306,
  'lon': 72.31459094518725,
  'name': '"Андижан АЭРОи"',
  'num': '3'},
 {'code': '3009',
  'contact': '998742247615 (6550,6551,6552,6554)',
  'info': 'Андижон вилояти, Пахтаобод тумани, Маданият ҚФЙ Тошқўрғон МФЙ',
  'kind': 'border',
  'lat': 40.70590116535886,
  'lon': 72.7673875599405,
  'name': '"Маданият" чегара пости',
  'num': '4'},
 {'code': '3014',
  'contact': '998742247615 (6540,6541,6542,6543)',
  'info': 'Андижон вилояти, Қўрғонтепа тумани, Устоз МФЙ, Бирлик кўча 1 уй',
  'kind': 'border',
  'lat': 40.70590116535886,
  'lon': 72.7673875599405,
  'name': '"Савай" темир йўл чегара пости',
  'num': '5'},
 {'code': '6001',
  'contact': '998 65 228 91 15',
  'info': 'Бухоро вилояти, Бухоро шаҳри, Б.Нақшбанд кўчаси, 251-уй',
  'kind': 'border',
  'lat': 39.767014,
  'lon': 64.475331,
  'name': '"Бухоро АЭРОи"',
  'num': '6'},
 {'code': '6010',
  'contact': '998 65 221 63 23',
  'info': 'Бухоро вилояти, Олот тумани, Союн Қоровул МФЙ, Олот чегара божхона пости',
  'kind': 'border',
  'lat': 39.228677,
  'lon': 63.715553,
  'name': '"Олот" чегара пости',
  'num': '7'},
 {'code': '6011',
  'contact': '998 95 600 14 31',
  'info': 'Бухоро вилояти, Олот тумани, Союн қоровул МФЙ, Хўжадавлат темир йўл станцияси',
  'kind': 'border',
  'lat': 39.327254,
  'lon': 63.746029,
  'name': '"Хўжадавлат" темир йўл чегара пости',
  'num': '8'},
 {'code': '8003',
  'contact': '',
  'info': 'Жиззах вилояти, Янгиобод тумани, Учтўрғон ахоли пункти, Тошкент-Душанбе М-34 магистрал йўли',
  'kind': 'border',
  'lat': 39.89045948796673,
  'lon': 68.9008070718586,
  'name': '"Учтўрғон" чегара пости',
  'num': '9'},
 {'code': '8007',
  'contact': '',
  'info': 'Жиззах вилояти, Янгиобод тумани, Қўшкент ахоли пункти, Тошкент-Душанбе М-34 магистрал йўли',
  'kind': 'border',
  'lat': 40.06193959705847,
  'lon': 68.94852952716137,
  'name': '"Қўшкент" чегара пости',
  'num': '10'},
 {'code': '10008',
  'contact': '998752211418(8533)',
  'info': 'Қашқадарё вилояти Нишон тумани',
  'kind': 'border',
  'lat': 38.352268091912244,
  'lon': 65.46760305641187,
  'name': '"Қарши-Керки" чегара пости',
  'num': '11'},
 {'code': '10012',
  'contact': '',
  'info': 'Қашқадарё вилояти Қарши шахар Буюк турон кўчаси 3 уй',
  'kind': 'border',
  'lat': None,
  'lon': None,
  'name': '"Қарши АЭРОи"',
  'num': '12'},
 {'code': '12002',
  'contact': '+998(78)-770-32-52',
  'info': 'Навоий вилояти, Кармана тумани, Сардоба маҳалласи, "Навоий халқаро аэропорти" МЧЖ ҳудуди',
  'kind': 'border',
  'lat': 40.12293550299368,
  'lon': 65.17915808969198,
  'name': '"Навоий АЭРОи"',
  'num': '13'},
 {'code': '14002',
  'contact': '',
  'info': 'Namangan viloyati, Namangan shahri, Namangan aeroporti',
  'kind': 'border',
  'lat': 40.98399875766145,
  'lon': 71.56476040643386,
  'name': '"Наманган АЭРОи"',
  'num': '14'},
 {'code': '14003',
  'contact': '',
  'info': 'Namangan viloyati, Uchqo`rg`on tumani, Yangiyer QFY, Bo`ston MFY',
  'kind': 'border',
  'lat': 41.09936504064733,
  'lon': 72.18558228669939,
  'name': '"Учқўрғон" чегара пости',
  'num': '15'},
 {'code': '14004',
  'contact': '',
  'info': 'Namangan viloyati, Kosonsoy tumani, Obod MFY',
  'kind': 'border',
  'lat': 41.29212077376505,
  'lon': 71.5397015658033,
  'name': '"Косонсой" чегара пости',
  'num': '16'},
 {'code': '14005',
  'contact': '',
  'info': 'Namangan viloyati, Pop tumani, Pungon qishlog`I',
  'kind': 'border',
  'lat': 40.765770531817594,
  'lon': 70.7343496241337,
  'name': '"Поп" чегара пости',
  'num': '17'},
 {'code': '18001',
  'contact': '',
  'info': 'Самарқанд вилояти, Самарқанд шаҳри Ибн Сино кўчаси 1-уй',
  'kind': 'border',
  'lat': 39.696105,
  'lon': 66.990976,
  'name': '"Самарқанд АЭРОи"',
  'num': '18'},
 {'code': '18002',
  'contact': '-',
  'info': 'Самарқанд вилояти, Ургут тумани Жартепа қишлоғи',
  'kind': 'border',
  'lat': 39.51856,
  'lon': 67.398137,
  'name': '"Жартепа" чегара пости',
  'num': '19'},
 {'code': '22002',
  'contact': '',
  'info': 'Сурхондарё вилояти, Термиз тумани, “Дўстлик” жамоа хужалиги',
  'kind': 'border',
  'lat': 37.28370297597932,
  'lon': 67.32476348617432,
  'name': '"Термиз АЭРОи"',
  'num': '20'},
 {'code': '22003',
  'contact': '',
  'info': 'Сурхондарё вилояти, Сариосиё тумани "Суфиён" ж/х, "Чумчукли жар" поселкаси',
  'kind': 'border',
  'lat': 38.41297484521007,
  'lon': 67.95690825425373,
  'name': '"Сариосиё" чегара пости',
  'num': '21'},
 {'code': '22004',
  'contact': '',
  'info': 'Сурхондарё вилояти, Узун тумани, Хатиб Қахрамон МФЙ Қўрғон қишлоғи',
  'kind': 'border',
  'lat': 38.405630794381345,
  'lon': 68.06478564518724,
  'name': '"Сариосиё" темир йўл чегара пости',
  'num': '22'},
 {'code': '22007',
  'contact': '',
  'info': 'Сурхондарё вилояти, Термиз тумани Гулбаҳор махалласи',
  'kind': 'border',
  'lat': 37.189633505960884,
  'lon': 67.79702099153711,
  'name': '"Гулбаҳор" чегара пости',
  'num': '23'},
 {'code': '22011',
  'contact': '',
  'info': 'Сурхондарё вилояти, Термиз шахри, С.Термизий кучаси 58 уй',
  'kind': 'border',
  'lat': None,
  'lon': None,
  'name': '"Дарё порти" божхона пости',
  'num': '24'},
 {'code': '22015',
  'contact': '',
  'info': 'Сурхондарё вилояти Музрабод тумани, Чегарачи МФЙ Қоракамар қишлоги',
  'kind': 'border',
  'lat': 37.401245158718055,
  'lon': 66.73061115855786,
  'name': '"Болдир" темир йўл чегара пости',
  'num': '25'},
 {'code': '22017',
  'contact': '',
  'info': 'Сурхондарё вилояти, Термиз тумани, “Янгиарик” СФУ',
  'kind': 'border',
  'lat': 37.23383709558547,
  'lon': 67.42679029204352,
  'name': '"Айритом" чегара пости',
  'num': '26'},
 {'code': '24002',
  'contact': 'ички номер (6799)',
  'info': 'Сирдарё вилояти, Ховос тумани, Ховос қўрғони Карвонсарой маҳалласи',
  'kind': 'border',
  'lat': 40.19726513721907,
  'lon': 68.85147519530977,
  'name': '"Ховостобод" чегара пости',
  'num': '27'},
 {'code': '24004',
  'contact': 'ички номер (6757; 6785;6795; 6786)',
  'info': 'Сирдарё вилояти, Сирдарё тумани, Синдоробод СИУ, Қуёш махалласи, Р-35 “Сирдарё-Илъич” автойўлининг 12-км.да',
  'kind': 'border',
  'lat': 40.83635982268926,
  'lon': 68.56707282716135,
  'name': '"Сирдарё" чегара пости',
  'num': '28'},
 {'code': '26009',
  'contact': '',
  'info': 'Тошкент вилояти, Тошкент тумани, Оқибат кўчаси 12-уй',
  'kind': 'border',
  'lat': 41.40751666026892,
  'lon': 69.20602713746936,
  'name': '"Келес" темир йўл чегара пости',
  'num': '29'},
 {'code': '26013',
  'contact': '71-207-09-56',
  'info': 'Тошкент шаҳри, Олмазор тумани, Чуқурсой кўчаси, 82 уй',
  'kind': 'border',
  'lat': 41.37785063707594,
  'lon': 69.24069565762181,
  'name': '"Чуқурсой техник идораси" темир йўл чегара пости',
  'num': '30'},
 {'code': '27001',
  'contact': '99871-202-02-72',
  'info': 'Тошкент вилояти, Чиноз тумани, Яллама қишлоғи',
  'kind': 'border',
  'lat': 40.967979,
  'lon': 68.727522,
  'name': '"Яллама" чегара пости',
  'num': '31'},
 {'code': '27008',
  'contact': '99871-202-02-76',
  'info': 'Тошкент вилояти, Тошкент тумани, Чувалачи ҚФЙ, “Гултепа” МФЙ',
  'kind': 'border',
  'lat': 41.45502874983215,
  'lon': 69.21253288851943,
  'name': '"Навоий" (Капланбек) чегара пости',
  'num': '32'},
 {'code': '27009',
  'contact': '99871-202-02-81',
  'info': 'Тошкент вилояти, Қибрай тумани, Май қишлоғи Туркистон ҚФЙ',
  'kind': 'border',
  'lat': 41.52207085934578,
  'lon': 69.40999879264473,
  'name': '"С. Нажимов"(Майский) чегара пости',
  'num': '33'},
 {'code': '27011',
  'contact': '99871-202-02-83',
  'info': 'Тошкент вилояти, Бекобод тумани, Ойбек ж/х',
  'kind': 'border',
  'lat': 40.547996,
  'lon': 69.208787,
  'name': '"Ойбек" чегара пости',
  'num': '34'},
 {'code': '27013',
  'contact': '99871-202-02-74',
  'info': 'Тошкент вилояти, Бекобод тумани',
  'kind': 'border',
  'lat': 40.21224,
  'lon': 69.205079,
  'name': '"Бекобод авто" чегара пости',
  'num': '35'},
 {'code': '27021',
  'contact': '99878-120-86-06',
  'info': 'Тошкент вилояти, Тошкент тумани Ғишткўприк махалласи, Чимкент йўли кўчаси',
  'kind': 'border',
  'lat': 41.469887,
  'lon': 69.357331,
  'name': '"Ғишткўприк"(Черняевка) чегара пости',
  'num': '36'},
 {'code': '27023',
  'contact': '99871-202-02-74',
  'info': 'Тошкент вилояти, Бекобод шаҳри, Сохил йўли, Низомий кўчаси',
  'kind': 'border',
  'lat': 40.19837636992406,
  'lon': 69.2996544920371,
  'name': '"Фарход" чегара пости',
  'num': '37'},
 {'code': '27024',
  'contact': '99870-214-65-79',
  'info': 'Тошкент вилояти, Бекобод шаҳри, Бекобод темир йўл станцияси',
  'kind': 'border',
  'lat': 40.214873,
  'lon': 69.227569,
  'name': '"Бекобод" темир йўл чегара пости',
  'num': '38'},
 {'code': '27029',
  'contact': '',
  'info': 'Тошкент вилояти, Янгийўл тумани, Ўзбекистон темир йўл станцияси',
  'kind': 'border',
  'lat': 41.161947,
  'lon': 69.103444,
  'name': '"Ўзбекистон" темир йўл чегара пости',
  'num': '39'},
 {'code': '30001',
  'contact': '',
  'info': 'Фарғона вилояти, Фарғона шаҳар, Аэропорт кўчаси 16-уй',
  'kind': 'border',
  'lat': 40.375821,
  'lon': 71.75155,
  'name': '"Фарғона" Аеропорти',
  'num': '40'},
 {'code': '30004',
  'contact': '',
  'info': 'Фарғона вилояти, Фарғона тумани, Юқори Водил қишлоғи, Яхши Ният кўчаси',
  'kind': 'border',
  'lat': 40.15065439270264,
  'lon': 71.73130989676778,
  'name': '"Фарғона" чегара пости',
  'num': '41'},
 {'code': '30005',
  'contact': '',
  'info': 'Фарғона вилояти, Бешариқ тумани, Андархон қишлоғи',
  'kind': 'border',
  'lat': 40.366229432478576,
  'lon': 70.45726956077178,
  'name': '"Андархон" чегара пости',
  'num': '42'},
 {'code': '30006',
  'contact': '',
  'info': 'Фарғона вилояти, Риштон тумани, Риштон шахри, Хўжа Илғор МФЙ, Фарғона кўчаси',
  'kind': 'border',
  'lat': 40.34409727045343,
  'lon': 71.274035144846,
  'name': '"Риштон" чегара пости',
  'num': '43'},
 {'code': '30008',
  'contact': '',
  'info': 'Фарғона вилояти Бешариқ тумани Қашқар ҚФЙ, Воррух қишлоғи',
  'kind': 'border',
  'lat': 40.32092365957019,
  'lon': 70.56451847493875,
  'name': '"Ровот" чегара пости',
  'num': '44'},
 {'code': '30010',
  'contact': '',
  'info': 'Фарғона вилояти, Қувасой шаҳар, Носиробод қишлоғи, Ўзбекистон кўчаси',
  'kind': 'border',
  'lat': 40.27583732505237,
  'lon': 72.04168207516355,
  'name': '"Ўзбекистон" чегара пости',
  'num': '45'},
 {'code': '30012',
  'contact': '',
  'info': 'Фарғона вилояти, Сўх тумани, Ровон шаҳарчаси, Амир Темур кўчаси, 4Р-149 рақамли автойўлда',
  'kind': 'border',
  'lat': 40.124879697964815,
  'lon': 71.08120389340729,
  'name': '"Сўх" чегара пости',
  'num': '46'},
 {'code': '33001',
  'contact': '',
  'info': 'Хоразм вилояти, Шовот тумани, Ўзбекистон қишлоғи, Махтумқули маҳалласи',
  'kind': 'border',
  'lat': 41.76907546739091,
  'lon': 60.0838617530042,
  'name': '"Шовот" чегара пости',
  'num': '47'},
 {'code': '33004',
  'contact': '',
  'info': 'Хоразм вилояти, Тупроққалъа тумани, Питнак шаҳри, Питнак қишлоғи, Охунбобоев маҳалласи',
  'kind': 'border',
  'lat': 41.18308324775138,
  'lon': 61.3728098280889,
  'name': '"Дўстлик" чегара пости (Хоразм)',
  'num': '48'},
 {'code': '33011',
  'contact': '',
  'info': 'Хоразм вилояти, Урганч шаҳри, Урганч халқаро аэропорти',
  'kind': 'border',
  'lat': 41.58523218697116,
  'lon': 60.64277532271613,
  'name': '"Урганч АЭРОи"',
  'num': '49'},
 {'code': '35001',
  'contact': '998 (61) 224-90-84',
  'info': 'Нукус шаҳри, А.Досназаров кўчаси',
  'kind': 'border',
  'lat': 42.482215532528095,
  'lon': 59.618314560771786,
  'name': '"Нукус АЭРОи"',
  'num': '50'},
 {'code': '35003',
  'contact': '998 (61) 224-90-85',
  'info': 'Хўжайли тумани, “Ходжейли-Куня Ургенч” авто йўли',
  'kind': 'border',
  'lat': 42.37376395715382,
  'lon': 59.301668093337646,
  'name': '"Хожайли" чегара пости',
  'num': '51'},
 {'code': '35004',
  'contact': '998 (61) 224-90-82',
  'info': 'Қўнғирот тумани, А-380 “Гузар-Бухара-Нукус-Бейнеу” автомагистралининг 1204 км',
  'kind': 'border',
  'lat': 44.89345934570517,
  'lon': 56.00240792037103,
  'name': '"Даут-ата" чегара пости',
  'num': '52'},
 {'code': '35010',
  'contact': '998 (61) 224-90-83',
  'info': 'Қўнғирот тумани, “Қорақалпоғистон” поселкаси, “ Қорақалпоғистон ” темир йўл станцияси',
  'kind': 'border',
  'lat': 44.766702361484896,
  'lon': 56.19542231097961,
  'name': '"Қорақалпоғистон" темир йўл чегара пости',
  'num': '53'},
 {'code': '3007',
  'contact': '998952014328, 998742247615 (6410,6441)',
  'info': 'Андижон вилояти, Хонобод тумани,“Навоий” МФЙ',
  'kind': 'border',
  'lat': 40.82256468440951,
  'lon': 72.9791879572124,
  'name': '"Хонобод" чегара пости',
  'num': '54'},
 {'code': '3005',
  'contact': '998952014328, 998742247615 (6410,6441)',
  'info': 'Андижон вилояти, Мархамат тумани, “Қорабоғич” ҚФЙ “Дўстлик” МФЙ',
  'kind': 'border',
  'lat': 40.63304156774797,
  'lon': 71.92483722035874,
  'name': '"Мингтепа" чегара пости',
  'num': '55'},
 {'code': '3006',
  'contact': '',
  'info': 'Андижон вилояти, Қўрғонтепа тумани, Қорасув шаҳар',
  'kind': 'border',
  'lat': 40.71995959920882,
  'lon': 72.89353815100151,
  'name': 'Қорасув чегара пости',
  'num': '56'},
 {'code': '3008',
  'contact': '',
  'info': 'Андижон вилояти, Пахтабод тумани Уйғур ҚФЙ, Пушмон махалла',
  'kind': 'border',
  'lat': 40.92795504509091,
  'lon': 72.54365919978952,
  'name': '"Пушмон" чегара пости',
  'num': '57'},
 {'code': '3013',
  'contact': '',
  'info': 'Андижон вилояти, Қўрғонтепа тумани, Султонобод қишлоғи',
  'kind': 'border',
  'lat': 40.72937707372828,
  'lon': 72.69972172886747,
  'name': 'Кесканёр чегара пости',
  'num': '58'},
 {'code': '24014',
  'contact': 'ички номер (6782; 6783)',
  'info': 'Сирдарё вилояти, Сирдарё тумани, Пахтакор СИУ, М39 автойўлининг 888 км.да',
  'kind': 'border',
  'lat': 40.79173591288273,
  'lon': 68.5828898299402,
  'name': '"Малик" чегара пости',
  'num': '59'},
 {'code': '24006',
  'contact': 'ички номер (6793; 6779; 6784)',
  'info': 'Сирдарё вилояти, Оқ олтин тумани, Сардоба қўрғони, М39 автойўлининг 912 км.да',
  'kind': 'border',
  'lat': 40.60809432984875,
  'lon': 68.4155277189425,
  'name': '"Оқ олтин" чегара пости',
  'num': '60'},
 {'code': '110',
  'contact': '+99855 502-86-30',
  'info': 'Тошкент шаҳар, Яшнобод тумани, "Тошкент-хумо" халқаро аэропорти',
  'kind': 'border',
  'lat': 41.3182159483729,
  'lon': 69.38980982802111,
  'name': '"Тошкент-Ҳумо аэропорти" чегара пости',
  'num': '61'},
 {'code': '33033',
  'contact': '+99862 227-70-11',
  'info': 'Хоразм вилояти, Шовот тумани, Ўзбекистон қишлоғи, Махтумқули маҳалласи',
  'kind': 'border',
  'lat': 41.77131388184346,
  'lon': 60.0879175859293,
  'name': '"Шовот чегараолди савдо зонаси" чегара пости',
  'num': '62'}]
VED_POSTS = [{'num': '1', 'code': '102', 'name': '"Авиа юклар" ТИФ', 'info': 'Тошкент, шаҳар, Сирғали тумани, "Ислом Каримов номидаги “Тошкент” халқаро аэропорти" худудида', 'contact': '+99855 502-86-43', 'lat': 41.26945712620506, 'lon': 69.27572996628209}, {'num': '2', 'code': '3011', 'name': '"Андижон" ТИФ', 'info': 'Андижон шаҳар, АЮлдашев кўчаси, 55 уй', 'contact': '998742247615 (6570,6571,6572,6573)', 'lat': None, 'lon': None}, {'num': '3', 'code': '3015', 'name': '"Асака" ТИФ', 'info': 'Андижон вилояти, Асака шаҳар, ЖМангуберди кўчаси, 36 “а”- уй', 'contact': '998742247615 (6580,6581,6582,6583, 6584)', 'lat': None, 'lon': None}, {'num': '4', 'code': '6006', 'name': '"Бухоро" ТИФ', 'info': 'Бухоро вилояти, Бухоро шахар, Саноатчилар кўчаси 2 уй', 'contact': '998 65 225 38 30', 'lat': 39.75834089005041, 'lon': 64.45357722025166}, {'num': '5', 'code': '6009', 'name': '"Қоракўл" ТИФ', 'info': 'Бухоро вилояти, Қоракўл туман. Бухоро кўчаси 9-уй', 'contact': '998 95 600 99 50', 'lat': None, 'lon': None}, {'num': '6', 'code': '8004', 'name': '"Жизах" ТИФ', 'info': 'Жиззах вилояти, Жиззах шаҳар, "А" саноат худуди, 10 уй', 'contact': '', 'lat': None, 'lon': None}, {'num': '7', 'code': '10002', 'name': '"Насаф" ТИФ', 'info': 'Қашқадарё вилояти Қарши шахар Ёг завод кучаси 2 уй', 'contact': '', 'lat': None, 'lon': None}, {'num': '8', 'code': '10007', 'name': '"Қамаши-Ғузор" ТИФ', 'info': 'Қашқадарё вилояти, Ғузор тумани, А-380 йўли яқинида, Шўртан қўрғони', 'contact': '998752211418(8524,8527)', 'lat': None, 'lon': None}, {'num': '9', 'code': '12003', 'name': '"Навоий" ТИФ', 'info': 'Навоий вилояти, Навоий шаҳар, Навоий кўчаси 5-уй', 'contact': '+998(79)-229-28-00', 'lat': None, 'lon': None}, {'num': '10', 'code': '12008', 'name': '"Зарафшон" ТИФ', 'info': 'Навоий вилояти, Зарафшон шаҳар, шаҳарга кириш ҳудуди', 'contact': '+998(79)-573-43-68', 'lat': None, 'lon': None}, {'num': '11', 'code': '14010', 'name': '"Наманган" ТИФ', 'info': 'Namangan viloyati, Namangan shahri, Yuqori Rovuston ko`chasi.', 'contact': '998692267600 (6971, 6972)', 'lat': 40.982346440573984, 'lon': 71.59484365227664}, {'num': '13', 'code': '18005', 'name': '"Самарқанд" ТИФ', 'info': 'Самарқанд вилояти, Самарканд тумани Ўзбеккент маҳалласи', 'contact': '-', 'lat': None, 'lon': None}, {'num': '14', 'code': '18007', 'name': '"Улуғбек" ТИФ', 'info': 'Самарқанд вилояти, Пастдарғом тумани Чархин қўрғони', 'contact': '', 'lat': 39.696246662550855, 'lon': 66.83491339215041}, {'num': '15', 'code': '22005', 'name': '"Термиз" ТИФ', 'info': 'Сурхондарё вилояти, Термиз тумани, Айритом махалласи', 'contact': '', 'lat': 37.25425491848949, 'lon': 67.42291059452586}, {'num': '16', 'code': '22006', 'name': '"Денов" ТИФ', 'info': 'Сурхондарё вилояти, Денов шахри, Фаррухий кўчаси 2 уй', 'contact': '', 'lat': None, 'lon': None}, {'num': '17', 'code': '24009', 'name': '"Гулистон" ТИФ', 'info': 'Сирдарё вилояти, Гулистон шахри, Аноров кўчаси 1-уй', 'contact': 'ички номер (6787; 6788)', 'lat': None, 'lon': None}, {'num': '18', 'code': '26002', 'name': '"Тошкент-товар" ТИФ', 'info': 'Тошкент шаҳар, Яшнобод тумани, Фарғона йўли кўчаси, 13/11-уй', 'contact': '71-207-09-72', 'lat': 41.296295396393454, 'lon': 69.29984891849823}, {'num': '19', 'code': '26003', 'name': '"Арқбулоқ" ТИФ', 'info': 'Тошкент вилояти, Зангиота тумани, Эркин ҚФЙ, Тариқ тешар маҳалласи', 'contact': '71-207-09-40', 'lat': 41.223198440181974, 'lon': 69.1416128822776}, {'num': '20', 'code': '26004', 'name': '"Чуқурсой" ТИФ', 'info': 'Тошкент шаҳар, Олмазор тумани, Чуқурсой кўчаси 92Б уй', 'contact': '71-207-09-74', 'lat': 41.384004257446946, 'lon': 69.23281321598888}, {'num': '21', 'code': '26010', 'name': '"Сирғали" ТИФ божхона пости', 'info': 'Тошкент шаҳар, Сирғали тумани, Суғдиёна кўчаси 3-уй', 'contact': '71-207-08-52', 'lat': 41.22248952578655, 'lon': 69.23343394073085}, {'num': '22', 'code': '27014', 'name': '"Чирчиқ" ТИФ', 'info': 'Тошкент вилояти, Чирчиқ шаҳри, Рамазон кўчаси 52 уй', 'contact': '99871-202-07-61', 'lat': 41.46330864601329, 'lon': 69.58185538802414}, {'num': '23', 'code': '27015', 'name': '"Олмалиқ" ТИФ', 'info': 'Тошкент вилояти, Олмалиқ шаҳар, Фахрийлар кўчаси, 29 уй', 'contact': '99871-202-02-80', 'lat': 40.83857384277283, 'lon': 69.6165425060102}, {'num': '24', 'code': '27016', 'name': '"Янгийўл" ТИФ', 'info': 'Тошкент вилояти, Зангиота тумани, Ўртаоул МФЙ, Файз маҳалласи', 'contact': '99871-202-02-82', 'lat': 41.10801907579423, 'lon': 69.05615859638715}, {'num': '25', 'code': '27019', 'name': '"Назарбек" ТИФ', 'info': 'Тошкент вилояти, Зангиота тум., Назарбек қфй, Лойихачи кўча 11', 'contact': '99878-150-88-56', 'lat': 41.28787504872319, 'lon': 69.11463091141255}, {'num': '26', 'code': '27020', 'name': '"Келес" ТИФ', 'info': 'Тошкент вилояти, Тошкент тум., Оқибат кўчаси 140 уй', 'contact': '99871-202-02-77', 'lat': 41.400858291646074, 'lon': 69.219152465546}, {'num': '27', 'code': '27028', 'name': '"Ангрен" ТИФ', 'info': 'Тошкент вилояти, Ангрен шаҳри, Саноат ҳудуди, Ипак-йўли кўчаси 1 уй,', 'contact': '', 'lat': 40.975358933102214, 'lon': 70.04598756610751}, {'num': '28', 'code': '30002', 'name': '"Қўқон" ТИФ', 'info': 'Фарғона вилояти, Қўқон шаҳар, Шохрухобод кўчаси 2-уй', 'contact': '', 'lat': 40.51901491317192, 'lon': 70.93230848292609}, {'num': '29', 'code': '30009', 'name': '"Водий" ТИФ', 'info': 'Фарғона вилояти, Фарғона шаҳар, Ёруғлик кўчаси 19-уй', 'contact': '', 'lat': 40.38000884654385, 'lon': 71.83458264049966}, {'num': '30', 'code': '33007', 'name': '"Урганч" ТИФ', 'info': 'Хоразм вилояти, Урганч шаҳар “Хонқа” кўчаси 62/1-уй', 'contact': '', 'lat': 41.5348813555841, 'lon': 60.65356054836766}, {'num': '31', 'code': '35002', 'name': '"Нукус" ТИФ', 'info': 'Нукус шаҳри, Қиз кеткен МФЙ Жанубий саноат зонаси рақамсиз уй (“Умид Нукус” МЧЖ маъмурий биносида)', 'contact': '+998 (61) 224-95-59', 'lat': None, 'lon': None}, {'num': '32', 'code': '107', 'name': '"Бош почтампт" ТИФ', 'info': 'Тошкент шаҳар, Сирғали тумани, Қумариқ кўчаси 102-уй', 'contact': '71-207-14-03', 'lat': 41.26237947477917, 'lon': 69.25475090569257}, {'num': '33', 'code': '22022', 'name': '“Термиз халқаро савдо маркази” ТИФ божхона пости', 'info': 'Сурхондарё вилояти, Термиз тумани, "Айритом" МФЙ', 'contact': '998762299595, (8895)', 'lat': 37.25425491848949, 'lon': 67.42291059452586}]

# BORDER_POSTS fallback removed to preserve coordinates from the primary list


def get_posts(kind: str) -> List[Dict[str, Any]]:
    return BORDER_POSTS if kind == "border" else VED_POSTS

def find_post_by_num(kind: str, num_text: str) -> Dict[str, Any] | None:
    num = normalize_text(num_text)
    for item in get_posts(kind):
        if normalize_text(str(item.get("num",""))) == num:
            return item
    return None

def posts_list_text(lang: str, kind: str) -> str:
    items = get_posts(kind)
    title = t(lang, "physical_posts_border_intro") if kind == "border" else t(lang, "physical_posts_ved_intro")
    lines = [title, ""]
    for item in items:
        lines.append(f"{item.get('num')}. {item.get('name')}")
    return "\n".join(lines)

def post_card_text(lang: str, item: Dict[str, Any]) -> str:
    num_label = "№"
    code_label = "Код поста" if lang == "ru" else "Post kodi"
    info_label = "Информация" if lang == "ru" else "Ma’lumot"
    contact_label = "Контакт" if lang == "ru" else "Kontakt"
    lines = [
        f"<b>{item.get('name','')}</b>",
        "",
        f"{num_label}: {item.get('num','-')}",
        f"{code_label}: {item.get('code','-')}",
        f"{info_label}: {item.get('info','-')}",
    ]
    if item.get('contact'):
        lines.append(f"{contact_label}: {item.get('contact')}")
    return "\n".join(lines)

USER_CTX = {}

MAX_TELEGRAM_MESSAGE = 3800
MAX_RESULTS_SHOW = 10

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
    conn.execute(
        "CREATE TABLE IF NOT EXISTS applications ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "app_type TEXT,"
        "title TEXT,"
        "user_id INTEGER,"
        "username TEXT,"
        "lang TEXT,"
        "role TEXT,"
        "status TEXT DEFAULT 'new',"
        "payload_json TEXT,"
        "created_at TEXT,"
        "updated_at TEXT"
        ")"
    )
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
    cur.execute("SELECT COUNT(*) FROM events WHERE event_type='logistics_application'"); lapps = cur.fetchone()[0] or 0
    conn.close()
    if not any([users, messages, apps, bapps, lapps]):
        return TXT[lang]["analytics_empty"]
    return (
        f"<b>{TXT[lang]['analytics_title']}</b>\n\n"
        f"👥 Пользователи: {users}\n"
        f"💬 Сообщения: {messages}\n"
        f"📩 Заявки специалисту: {apps}\n"
        f"💼 PRO-заявки брокеров: {bapps}\n"
        f"🚚 Заявки по логистике: {lapps}"
    )


def is_admin(uid: int) -> bool:
    return _helper_is_admin(ADMIN_CHAT_ID, uid)


def admin_menu_kb(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "admin_overview"), t(lang, "admin_today"))
    kb.add(t(lang, "admin_week"), t(lang, "admin_popular"))
    kb.add(t(lang, "admin_users"), t(lang, "admin_apps"))
    kb.add(t(lang, "admin_close"))
    return kb


def _period_since(days: int = 0) -> str:
    base = datetime.utcnow() - timedelta(days=days)
    return base.isoformat()


def _count(cur, query: str, params=()):
    cur.execute(query, params)
    row = cur.fetchone()
    return (row[0] if row and row[0] is not None else 0)


def admin_overview_text(lang: str) -> str:
    conn = db_conn()
    cur = conn.cursor()
    users = _count(cur, "SELECT COUNT(DISTINCT user_id) FROM events")
    messages = _count(cur, "SELECT COUNT(*) FROM events WHERE event_type='message'")
    roles = _count(cur, "SELECT COUNT(*) FROM events WHERE event_type='role_selected'")
    searches = _count(cur, "SELECT COUNT(*) FROM events WHERE event_type='code_search'")
    specialist = _count(cur, "SELECT COUNT(*) FROM events WHERE event_type='application'")
    broker = _count(cur, "SELECT COUNT(*) FROM events WHERE event_type='broker_application'")
    logistics = _count(cur, "SELECT COUNT(*) FROM events WHERE event_type='logistics_application'")
    conn.close()
    if not any([users, messages, roles, searches, specialist, broker, logistics]):
        return t(lang, "admin_empty")
    return (
        f"<b>{t(lang, 'admin_title')}</b>\n\n"
        f"👥 Уникальные пользователи: {users}\n"
        f"💬 Всего сообщений: {messages}\n"
        f"🎯 Выбор роли: {roles}\n"
        f"🔎 Поиск кодов: {searches}\n"
        f"📩 Заявки специалисту: {specialist}\n"
        f"💼 Broker PRO заявки: {broker}\n"
        f"🚚 Логистика заявки: {logistics}"
    )


def admin_period_text(lang: str, days: int) -> str:
    since = _period_since(days)
    title = t(lang, "admin_today") if days == 0 else t(lang, "admin_week")
    conn = db_conn()
    cur = conn.cursor()
    users = _count(cur, "SELECT COUNT(DISTINCT user_id) FROM events WHERE created_at >= ?", (since,))
    messages = _count(cur, "SELECT COUNT(*) FROM events WHERE event_type='message' AND created_at >= ?", (since,))
    searches = _count(cur, "SELECT COUNT(*) FROM events WHERE event_type='code_search' AND created_at >= ?", (since,))
    specialist = _count(cur, "SELECT COUNT(*) FROM events WHERE event_type='application' AND created_at >= ?", (since,))
    broker = _count(cur, "SELECT COUNT(*) FROM events WHERE event_type='broker_application' AND created_at >= ?", (since,))
    logistics = _count(cur, "SELECT COUNT(*) FROM events WHERE event_type='logistics_application' AND created_at >= ?", (since,))
    conn.close()
    if not any([users, messages, searches, specialist, broker, logistics]):
        return t(lang, "admin_empty")
    return (
        f"<b>{title}</b>\n\n"
        f"👥 Активные пользователи: {users}\n"
        f"💬 Сообщения: {messages}\n"
        f"🔎 Поиск кодов: {searches}\n"
        f"📩 Специалист: {specialist}\n"
        f"💼 Broker PRO: {broker}\n"
        f"🚚 Логистика: {logistics}"
    )


def admin_popular_text(lang: str) -> str:
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT role, COUNT(*) cnt FROM events WHERE event_type='role_selected' GROUP BY role ORDER BY cnt DESC LIMIT 10")
    roles = cur.fetchall()
    cur.execute("SELECT event_value, COUNT(*) cnt FROM events WHERE event_type='message' AND TRIM(event_value) != '' GROUP BY event_value ORDER BY cnt DESC LIMIT 10")
    messages = cur.fetchall()
    conn.close()
    parts = [f"<b>{t(lang, 'admin_popular')}</b>"]
    if roles:
        parts.append("\n🎭 Популярные роли:")
        for role, cnt in roles:
            parts.append(f"• {role or '-'} — {cnt}")
    if messages:
        parts.append("\n💬 Частые сообщения:")
        for value, cnt in messages[:5]:
            show = (value or '').replace('<', '').replace('>', '')[:50]
            parts.append(f"• {show} — {cnt}")
    return "\n".join(parts) if len(parts) > 1 else t(lang, "admin_empty")


def admin_users_text(lang: str) -> str:
    since = _period_since(7)
    conn = db_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, MAX(username), COUNT(*) cnt, MAX(created_at) last_at "
        "FROM events WHERE created_at >= ? GROUP BY user_id ORDER BY last_at DESC LIMIT 15",
        (since,)
    )
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return t(lang, "admin_empty")
    out = [f"<b>{t(lang, 'admin_users')}</b>", "", "Последние активные пользователи за 7 дней:"]
    for user_id, username, cnt, last_at in rows:
        uname = f"@{username}" if username else "-"
        out.append(f"• ID <code>{user_id}</code> | {uname} | {cnt} действий")
    return "\n".join(out)


# =========================
# PHYSICAL UI PATCHES
# =========================
TXT["ru"].update({
    "physical_ai": "🤖 AI таможенник",
    "physical_posts": "🏢 Список таможенных постов",
    "physical_ready": "📋 Готовые вопросы",
    "physical_own": "✍️ Свой вопрос",
    "physical_ai_intro": "🤖 <b>AI таможенник</b>\n\nБыстрые ответы по таможенным вопросам для физических лиц.\n\nВыберите вариант:",
    "physical_ready_intro": "Выберите готовый вопрос:",
    "physical_ask_own_intro": "Напишите свой вопрос по таможне для физических лиц.",
    "physical_free_specialist": "Если хотите, специалист ответит бесплатно в течение дня.",
    "physical_only_customs": "Я отвечаю только на вопросы, связанные с таможней Узбекистана.",
    "physical_posts_intro": "Выберите тип постов:",
    "physical_posts_border": "🚧 Пограничные посты",
    "physical_posts_ved": "📦 ВЭД посты",
    "physical_posts_border_intro": "🚧 Пограничные посты\n\nОтправьте номер поста, чтобы увидеть подробную информацию.",
    "physical_posts_ved_intro": "📦 ВЭД посты\n\nОтправьте номер поста, чтобы увидеть подробную информацию.",
    "physical_post_not_found": "Пост не найден. Отправьте номер из списка.",
    "physical_location": "📍 Локация",
    "physical_location_sent": "Геопозиция отправлена.",
    "physical_location_missing": "Для этого поста геопозиция пока не указана.",
    "physical_pick_post_first": "Сначала выберите пост по номеру.",
    "physical_q1": "Таможенные правила для физлиц",
    "physical_q2": "Сколько можно ввозить без пошлины",
    "physical_q3": "Сколько телефонов можно привезти",
    "physical_q4": "Можно ли ввозить лекарства",
    "physical_q5": "Сколько можно вывозить валюты",
    "physical_q6": "Что будет при превышении нормы",
})
TXT["uz"].update({
    "physical_ai": "🤖 AI bojxonachi",
    "physical_posts": "🏢 Bojxona postlari ro‘yxati",
    "physical_ready": "📋 Tayyor savollar",
    "physical_own": "✍️ O‘z savolingiz",
    "physical_ai_intro": "🤖 <b>AI bojxonachi</b>\n\nJismoniy shaxslar uchun bojxona savollariga tezkor javob.\n\nVariantni tanlang:",
    "physical_ready_intro": "Tayyor savolni tanlang:",
    "physical_ask_own_intro": "Jismoniy shaxslar uchun bojxona bo‘yicha savolingizni yozing.",
    "physical_free_specialist": "Xohlasangiz, mutaxassis sizga kun davomida bepul javob beradi.",
    "physical_only_customs": "Men faqat O‘zbekiston bojxonasiga oid savollarga javob beraman.",
    "physical_posts_intro": "Post turini tanlang:",
    "physical_posts_border": "🚧 Chegara postlari",
    "physical_posts_ved": "📦 VED postlari",
    "physical_posts_border_intro": "🚧 Chegara postlari\n\nBatafsil ma’lumot uchun post raqamini yuboring.",
    "physical_posts_ved_intro": "📦 VED postlari\n\nBatafsil ma’lumot uchun post raqamini yuboring.",
    "physical_post_not_found": "Post topilmadi. Ro‘yxatdagi raqamni yuboring.",
    "physical_location": "📍 Lokatsiya",
    "physical_location_sent": "Geolokatsiya yuborildi.",
    "physical_location_missing": "Bu post uchun geolokatsiya hali kiritilmagan.",
    "physical_pick_post_first": "Avval postni raqami bo‘yicha tanlang.",
    "physical_q1": "Jismoniy shaxslar uchun bojxona qoidalari",
    "physical_q2": "Bojsiz qancha olib kirish mumkin",
    "physical_q3": "Nechta telefon olib kirish mumkin",
    "physical_q4": "Dori olib kirish mumkinmi",
    "physical_q5": "Qancha valyuta olib chiqish mumkin",
    "physical_q6": "Norma oshsa nima bo‘ladi",
})


def t(lang: str, key: str) -> str:
    return TXT.get(lang, TXT["ru"]).get(key, key)


def admin_apps_menu_kb(lang: str):
    return _admin_apps_menu_kb(t, lang)

def admin_apps_text(lang: str, app_type: str = None, status: str = None) -> str:
    return _admin_apps_text(ANALYTICS_DB_PATH, t, lang, app_type=app_type, status=status)

def admin_app_status_kb(app_id: int, current_status: str = "new"):
    return _admin_app_status_kb(app_id, current_status)

def get_application(app_id: int):
    return _get_application(ANALYTICS_DB_PATH, app_id)

def update_application_status(app_id: int, status: str):
    return _update_application_status(ANALYTICS_DB_PATH, app_id, status)

def status_text(lang: str, status: str) -> str:
    return _status_text(t, lang, status)

async def send_specialist_application_to_admin(uid: int, username: str, form_data: Dict[str, Any]):
    c_lang = form_data.get("lang", "ru")
    c_role = form_data.get("role", "")
    return await _send_specialist_application_to_admin(
        bot=bot,
        admin_chat_id=ADMIN_CHAT_ID,
        db_path=ANALYTICS_DB_PATH,
        uid=uid,
        username=username,
        form_data=form_data,
        role=c_role,
        lang=c_lang,
    )

def build_lang_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Русский", "O'zbekcha")
    return kb

def role_kb(lang: str, uid: int = None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "role_physical"), t(lang, "role_legal"))
    kb.add(t(lang, "role_broker"), t(lang, "role_logistics"))
    if uid is not None and is_admin(uid):
        kb.add(t(lang, "admin_open"))
    return kb

def physical_menu(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "physical_ai"))
    kb.add(t(lang, "physical_posts"))
    kb.add(t(lang, "specialist"))
    kb.add(t(lang, "change"))
    return kb

def physical_ai_kb(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "physical_ready"), t(lang, "physical_own"))
    kb.add(t(lang, "back"), t(lang, "specialist"))
    kb.add(t(lang, "back_menu"))
    return kb

def physical_ready_kb(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "physical_q1"))
    kb.add(t(lang, "physical_q2"))
    kb.add(t(lang, "physical_q3"))
    kb.add(t(lang, "physical_q4"))
    kb.add(t(lang, "physical_q5"))
    kb.add(t(lang, "physical_q6"))
    kb.add(t(lang, "back"), t(lang, "specialist"))
    kb.add(t(lang, "back_menu"))
    return kb

def physical_posts_menu_kb(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "physical_posts_border"), t(lang, "physical_posts_ved"))
    kb.add(t(lang, "back"), t(lang, "back_menu"))
    return kb

def physical_post_card_kb(lang: str, has_location: bool):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    if has_location:
        kb.add(t(lang, "physical_location"))
    kb.add(t(lang, "back"), t(lang, "back_menu"))
    return kb

def legal_menu(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "tnved"), t(lang, "exact"))
    kb.add(t(lang, "chat"), t(lang, "specialist"))
    kb.add(t(lang, "change"))
    return kb


def legal_ai_kb(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "faq_1"))
    kb.add(t(lang, "faq_2"))
    kb.add(t(lang, "faq_3"))
    kb.add(t(lang, "faq_4"))
    kb.add(t(lang, "faq_5"))
    kb.add(t(lang, "ask_own"))
    kb.add(t(lang, "back"), t(lang, "specialist"))
    kb.add(t(lang, "back_menu"))
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

def broker_main_menu(lang: str):
    return broker_menu(lang)

def broker_cost_submenu(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "broker_cost_low"))
    kb.add(t(lang, "broker_cost_3m"))
    kb.add(t(lang, "back"), t(lang, "back_menu"))
    return kb

def broker_docs_apply_kb(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "broker_docs_apply"))
    kb.add(t(lang, "back"), t(lang, "back_menu"))
    return kb

def broker_docs_upload_kb(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "broker_finish_upload"))
    kb.add(t(lang, "back"), t(lang, "back_menu"))
    return kb

def broker_cert_submenu(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "broker_cert_check"))
    kb.add(t(lang, "broker_cert_apply"))
    kb.add(t(lang, "back"), t(lang, "back_menu"))
    return kb

def broker_cert_apply_kb(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "broker_cert_apply_btn"))
    kb.add(t(lang, "back"), t(lang, "back_menu"))
    return kb

def broker_agency_kb(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "broker_agency_plant"))
    kb.add(t(lang, "broker_agency_vet"))
    kb.add(t(lang, "broker_agency_cert"))
    kb.add(t(lang, "back"), t(lang, "back_menu"))
    return kb

def broker_plant_services_kb(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "broker_service_quarantine"))
    kb.add(t(lang, "broker_service_akd"))
    kb.add(t(lang, "back"), t(lang, "back_menu"))
    return kb

def broker_vet_services_kb(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "broker_service_vet"))
    kb.add(t(lang, "back"), t(lang, "back_menu"))
    return kb

def broker_cert_services_kb(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "broker_service_conformity"))
    kb.add(t(lang, "back"), t(lang, "back_menu"))
    return kb

def broker_analytics_apply_kb(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t(lang, "broker_analytics_apply"))
    kb.add(t(lang, "back"), t(lang, "back_menu"))
    return kb

def broker_admin_confirm_kb(app_id: int, current_status: str = "new"):
    return admin_app_status_kb(app_id, current_status)

async def send_broker_application_to_admin(uid: int, username: str, form_data: Dict[str, Any], title: str):
    msg = f"💼 <b>{title}</b>\n\n"

    ordered_keys = [
        ("service", "Услуга"),
        ("price", "Стоимость"),
        ("name", "Имя"),
        ("tnved", "Код ТН ВЭД"),
        ("product", "Описание товара"),
        ("dispatch_country", "Страна отправления"),
        ("origin_country", "Страна происхождения"),
        ("agency", "Учреждение"),
        ("subservice", "Подуслуга"),
        ("phone", "Телефон"),
        ("comment", "Комментарий"),
    ]

    for key, label in ordered_keys:
        value = form_data.get(key)
        if value:
            msg += f"{label}: {value}\n"

    docs = form_data.get("documents", [])
    if docs:
        msg += "\n📎 Документы:\n"
        for i, d in enumerate(docs, 1):
            msg += f"{i}) {d.get('file_name','файл')}\n"

    msg += f"\nID клиента: <code>{uid}</code>\nUsername: @{username or '-'}"

    if ADMIN_CHAT_ID:
        try:
            await bot.send_message(
                int(ADMIN_CHAT_ID),
                msg,
                reply_markup=broker_admin_confirm_kb(uid)
            )
        except Exception:
            logging.exception("Telegram send failed")

    if ADMIN_CHAT_ID and docs:
        for d in docs:
            try:
                await bot.send_document(
                    int(ADMIN_CHAT_ID),
                    d["file_id"],
                    caption=f"Файл по заявке клиента {uid}: {d.get('file_name','document')}"
                )
            except Exception:
                pass

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


def extract_code_from_text(text: str) -> str:
    m = re.search(r"(?<!\d)(\d{4,10})(?!\d)", text or "")
    return m.group(1) if m else ""


def looks_like_customs_question(text: str) -> bool:
    q = normalize_text(text)
    keywords = [
        "тн вэд", "тнвед", "код", "код товара", "пошлина", "ндс", "акциз", "утиль",
        "импорт", "экспорт", "тамож", "декларац", "сертифик", "разреш", "оформлен",
        "контракт", "инвойс", "упаковоч", "транспортн", "ставк", "платеж", "ввоз", "вывоз",
        "tn ved", "bojxona", "import", "eksport", "kod", "stavka", "qqs", "aksiz",
        "sertifikat", "ruxsat", "deklar", "hujjat", "to'lov", "tolov", "util", "rasmiylasht"
    ]
    return bool(extract_code_from_text(text)) or any(k in q for k in keywords)

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

def faq_answer(text: str, lang: str) -> str:
    if text == t(lang, "faq_1"):
        return "Обычно для импорта нужны:\n• контракт\n• инвойс\n• упаковочный лист\n• транспортные документы\n• при необходимости сертификаты и разрешительные документы\n\nУточните, пожалуйста: о каком товаре идёт речь?" if lang == "ru" else "Import uchun odatda kerak bo‘ladi:\n• kontrakt\n• invoys\n• qadoqlash varaqasi\n• transport hujjatlari\n• zarur bo‘lsa sertifikat va ruxsatnomalar\n\nIltimos, qaysi tovar haqida gap ketayotganini yozing?"
    if text == t(lang, "faq_2"):
        return "Обычно для экспорта нужны:\n• контракт\n• инвойс\n• упаковочный лист\n• транспортные документы\n• при необходимости разрешительные документы\n\nУточните, пожалуйста: о каком товаре идёт речь?" if lang == "ru" else "Eksport uchun odatda kerak bo‘ladi:\n• kontrakt\n• invoys\n• qadoqlash varaqasi\n• transport hujjatlari\n• zarur bo‘lsa ruxsatnomalar\n\nIltimos, qaysi tovar haqida gap ketayotganini yozing?"
    if text == t(lang, "faq_3"):
        return "В зависимости от товара могут понадобиться:\n• сертификат соответствия\n• санитарно-эпидемиологическое заключение\n• разрешительные документы\n• декларация соответствия\n\nУточните, пожалуйста: о каком товаре идёт речь?" if lang == "ru" else "Tovarga qarab quyidagilar kerak bo‘lishi mumkin:\n• muvofiqlik sertifikati\n• sanitariya-epidemiologik xulosa\n• ruxsatnoma\n• muvofiqlik deklaratsiyasi\n\nIltimos, qaysi tovar haqida gap ketayotganini yozing?"
    if text == t(lang, "faq_4"):
        return "Код ТН ВЭД определяется по назначению, составу, материалу, характеристикам и правилам классификации.\n\nУточните, пожалуйста: какой именно товар нужно определить?" if lang == "ru" else "TN VED kodi vazifa, tarkib, material va xususiyatlarga ko‘ra aniqlanadi.\n\nQaysi tovar uchun kod aniqlash kerak?"
    if text == t(lang, "faq_5"):
        return "При импорте обычно применяются пошлина, НДС, а по некоторым товарам — акциз и утильсбор.\n\nУточните, пожалуйста: вы хотите расчёт по конкретному товару?" if lang == "ru" else "Importda odatda boj va QQS, ayrim tovarlarda aksiz va util yig‘imi qo‘llanadi.\n\nAniq tovar bo‘yicha hisob-kitob kerakmi?"
    return ""

def physical_answer(q: str, lang: str) -> str:
    q = normalize_text(q)
    if any(x in q for x in ["телефон","iphone","смартфон","phone"]):
        return "Для физлица важны лимит, личное пользование и IMEI-регистрация." if lang == "ru" else "Jismoniy shaxs uchun limit, shaxsiy foydalanish va IMEI ro‘yxatdan o‘tkazish muhim."
    if any(x in q for x in ["авто","машин","byd","tesla","gibrid","электро","mashina","avto"]):
        return "Для физлица по авто важны тип, возраст, объём двигателя, документы и цель ввоза." if lang == "ru" else "Jismoniy shaxs uchun avto bo‘yicha turi, yoshi, dvigatel hajmi, hujjatlar va olib kirish maqsadi muhim."
    return t(lang, "physical_no_calc")

async def send_main_menu(message: types.Message, uid: int):
    c = ctx(uid)
    lang = c["lang"]
    c["mode"] = None
    c["category"] = None
    c["group"] = None
    c["pending_form"] = None
    c["form_data"] = {}
    await message.answer(t(lang, "saved"), reply_markup=role_kb(lang, uid))

async def send_role_menu(message: types.Message, uid: int):
    c = ctx(uid)
    lang = c["lang"]
    role = c["role"]
    c["mode"] = None
    c["category"] = None
    c["group"] = None
    c["pending_form"] = None
    c["form_data"] = {}

    if c.get("pending_form") == "broker_docs_files" and text == t(lang, "broker_finish_upload"):
        docs = (c.get("form_data") or {}).get("documents", [])
        if not docs:
            await message.answer(t(lang, "broker_need_doc"), reply_markup=broker_docs_upload_kb(lang))
            return
        await send_broker_application_to_admin(uid, username, c["form_data"], c["form_data"].get("title", "Проверка документов перед подачей"))
        track(uid, username, lang, role or "", "broker_application", c["form_data"].get("service", ""))
        c["pending_form"] = None
        c["form_data"] = {}
        await message.answer(t(lang, "broker_application_received_3h"), reply_markup=broker_menu(lang))
        return

    if role == "physical":
        await message.answer(t(lang, "saved"), reply_markup=physical_menu(lang))
    elif role == "legal":
        await message.answer(t(lang, "legal_intro"), reply_markup=legal_menu(lang))
    elif role == "broker":
        await message.answer(t(lang, "broker_intro"), reply_markup=broker_menu(lang))
    elif role == "logistics":
        await message.answer(t(lang, "log_intro"), reply_markup=logistics_menu(lang))
    else:
        await message.answer(t(lang, "saved"), reply_markup=role_kb(lang, uid))

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

@dp.message_handler(commands=["admin"])
async def admin_cmd(message: types.Message):
    uid = message.from_user.id
    c = ctx(uid)
    if not is_admin(uid):
        await message.answer(t(c["lang"], "admin_access_denied"))
        return
    c["mode"] = "admin_panel"
    await message.answer(admin_overview_text(c["lang"]), reply_markup=admin_menu_kb(c["lang"]))

@dp.message_handler(commands=["analytics","stats"])
async def analytics_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(analytics_text(ctx(message.from_user.id)["lang"]), reply_markup=admin_menu_kb(ctx(message.from_user.id)["lang"]))

@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def router(message: types.Message):
    uid = message.from_user.id
    username = message.from_user.username or ""
    c = ctx(uid); lang = c["lang"]; role = c["role"]; text = message.text.strip()
    track(uid, username, lang, role or "", "message", text)

    if text in ["Русский", "O'zbekcha"]:
        c["lang"] = "ru" if text == "Русский" else "uz"
        c["mode"] = "choose_role"
        await message.answer(t(c["lang"], "lang_saved") + "\n" + t(c["lang"], "choose_role"), reply_markup=role_kb(c["lang"], message.from_user.id))
        return

    lang = c["lang"]

    if is_admin(uid) and text == t(lang, "admin_open"):
        c["mode"] = "admin_panel"
        await message.answer(admin_overview_text(lang), reply_markup=admin_menu_kb(lang))
        return

    if c.get("mode") == "admin_panel":
        if text == t(lang, "admin_overview"):
            await message.answer(admin_overview_text(lang), reply_markup=admin_menu_kb(lang))
            return
        if text == t(lang, "admin_today"):
            await message.answer(admin_period_text(lang, 0), reply_markup=admin_menu_kb(lang))
            return
        if text == t(lang, "admin_week"):
            await message.answer(admin_period_text(lang, 7), reply_markup=admin_menu_kb(lang))
            return
        if text == t(lang, "admin_popular"):
            await send_safe_message(message, admin_popular_text(lang), reply_markup=admin_menu_kb(lang))
            return
        if text == t(lang, "admin_users"):
            await send_safe_message(message, admin_users_text(lang), reply_markup=admin_menu_kb(lang))
            return
        if text == t(lang, "admin_apps"):
            c["mode"] = "admin_apps"
            await message.answer(admin_apps_text(lang), reply_markup=admin_apps_menu_kb(lang))
            return
        if text == t(lang, "admin_close"):
            c["mode"] = None
            await message.answer(t(lang, "admin_closed"), reply_markup=role_kb(lang) if not c.get("role") else (physical_menu(lang) if c.get("role")=="physical" else legal_menu(lang) if c.get("role")=="legal" else broker_menu(lang) if c.get("role")=="broker" else logistics_menu(lang)))
            return

    if c.get("mode") == "admin_apps":
        if text == t(lang, "admin_apps_back"):
            c["mode"] = "admin_panel"
            await message.answer(admin_overview_text(lang), reply_markup=admin_menu_kb(lang))
            return
        if text == t(lang, "admin_apps_new"):
            await send_safe_message(message, admin_apps_text(lang, status="new"), reply_markup=admin_apps_menu_kb(lang))
            return
        if text == t(lang, "admin_apps_specialist"):
            await send_safe_message(message, admin_apps_text(lang, app_type="specialist"), reply_markup=admin_apps_menu_kb(lang))
            return
        if text == t(lang, "admin_apps_broker"):
            await send_safe_message(message, admin_apps_text(lang, app_type="broker"), reply_markup=admin_apps_menu_kb(lang))
            return
        if text == t(lang, "admin_apps_logistics"):
            await send_safe_message(message, admin_apps_text(lang, app_type="logistics"), reply_markup=admin_apps_menu_kb(lang))
            return
        if text == t(lang, "admin_apps_all"):
            await send_safe_message(message, admin_apps_text(lang), reply_markup=admin_apps_menu_kb(lang))
            return
        if text == t(lang, "admin_close"):
            c["mode"] = None
            await message.answer(t(lang, "admin_closed"), reply_markup=role_kb(lang) if not c.get("role") else (physical_menu(lang) if c.get("role")=="physical" else legal_menu(lang) if c.get("role")=="legal" else broker_menu(lang) if c.get("role")=="broker" else logistics_menu(lang)))
            return

    if text in [t(lang, "role_physical"), t(lang, "role_legal"), t(lang, "role_broker"), t(lang, "role_logistics")]:
        c["role"] = "physical" if text == t(lang, "role_physical") else "legal" if text == t(lang, "role_legal") else "broker" if text == t(lang, "role_broker") else "logistics"
        c["mode"] = None
        track(uid, username, lang, c["role"], "role_selected", c["role"])
        await send_role_menu(message, uid)
        return

    if text == t(lang, "change"):
        reset_mode(uid); c["role"] = None; c["mode"] = "choose_lang"
        await message.answer(t(lang, "choose_lang"), reply_markup=build_lang_kb())
        return

    if text == t(lang, "back_menu"):
        c["role"] = None
        c["mode"] = None
        c["category"] = None
        c["group"] = None
        c["pending_form"] = None
        c["form_data"] = {}
        await send_main_menu(message, uid)
        return

    if text == t(lang, "back"):
        if c["mode"] == "legal_group":
            c["mode"] = "legal_category"
            await message.answer(t(lang, "pick_category"), reply_markup=category_kb(lang))
            return
        if c["mode"] == "legal_item":
            c["mode"] = "legal_group"
            await message.answer(t(lang, "pick_group"), reply_markup=group_kb(lang, c["category"]))
            return
        await send_role_menu(message, uid)
        return

    if text == t(lang, "specialist"):
        reset_mode(uid); c["pending_form"] = "specialist_name"
        await message.answer(t(lang, "specialist_intro") + "\n\n" + t(lang, "enter_name"))
        return

    if c.get("pending_form") == "broker_docs_files" and text == t(lang, "broker_finish_upload"):
        docs = (c.get("form_data") or {}).get("documents", [])
        if not docs:
            await message.answer(t(lang, "broker_need_doc"), reply_markup=broker_docs_upload_kb(lang))
            return
        await send_broker_application_to_admin(uid, username, c["form_data"], c["form_data"].get("title", "Проверка документов перед подачей"))
        track(uid, username, lang, role or "", "broker_application", c["form_data"].get("service", ""))
        c["pending_form"] = None
        c["form_data"] = {}
        await message.answer(t(lang, "broker_application_received_3h"), reply_markup=broker_menu(lang))
        return

    if role == "physical":
        if text == t(lang, "physical_ai"):
            reset_mode(uid); c["mode"] = "physical_ai_menu"
            await message.answer(t(lang, "physical_ai_intro"), reply_markup=physical_ai_kb(lang)); return
        if text == t(lang, "physical_posts"):
            reset_mode(uid); c["mode"] = "physical_posts_menu"
            await message.answer(t(lang, "physical_posts_intro"), reply_markup=physical_posts_menu_kb(lang)); return

    if role == "legal":
        if text == t(lang, "chat"):
            reset_mode(uid); c["mode"] = "legal_chat"
            await message.answer(t(lang, "ai_intro"), reply_markup=legal_ai_kb(lang)); return
        if text == t(lang, "tnved"):
            reset_mode(uid); c["mode"] = "legal_category"
            await message.answer(t(lang, "pick_category"), reply_markup=category_kb(lang)); return
        if text == t(lang, "exact"):
            reset_mode(uid); c["mode"] = "exact_code"
            await message.answer(t(lang, "enter_code"), reply_markup=legal_menu(lang)); return

    if role == "broker":
        if text == t(lang, "broker_cost"):
            reset_mode(uid)
            c["mode"] = "broker_cost_menu"
            await message.answer(t(lang, "broker_cost_text"), reply_markup=broker_cost_submenu(lang))
            return

        if text == t(lang, "broker_docs"):
            reset_mode(uid)
            c["mode"] = "broker_docs_info"
            await message.answer(t(lang, "broker_docs_text"), reply_markup=broker_docs_apply_kb(lang))
            return

        if text == t(lang, "broker_cert"):
            reset_mode(uid)
            c["mode"] = "broker_cert_menu"
            await message.answer(t(lang, "broker_cert_text"), reply_markup=broker_cert_submenu(lang))
            return

        if text == t(lang, "broker_tnved_analytics"):
            reset_mode(uid)
            c["mode"] = "broker_analytics_info"
            await message.answer(t(lang, "broker_analytics_text"), reply_markup=broker_analytics_apply_kb(lang))
            return

    if text == t(lang, "log_apply") and role == "logistics":
        reset_mode(uid); c["pending_form"] = "log_name"; c["form_data"] = {"lang": lang, "role": role}
        await message.answer(t(lang, "enter_name"), reply_markup=logistics_menu(lang))
        return
    if text == t(lang, "log_how") and role == "logistics":
        await message.answer(t(lang, "log_how_text"), reply_markup=logistics_menu(lang))
        return

    if c.get("mode") == "broker_cost_menu":
        if text == t(lang, "broker_cost_low"):
            c["pending_form"] = "broker_name"
            c["form_data"] = {"lang": lang, "role": role, "service": t(lang, "broker_cost_low"), "price": "300 000 сум" if lang == "ru" else "300 000 so‘m", "title": "Анализ таможенной стоимости"}
            await message.answer(t(lang, "enter_name"), reply_markup=broker_menu(lang))
            return
        if text == t(lang, "broker_cost_3m"):
            c["pending_form"] = "broker_name"
            c["form_data"] = {"lang": lang, "role": role, "service": t(lang, "broker_cost_3m"), "price": "600 000 сум" if lang == "ru" else "600 000 so‘m", "title": "Анализ таможенной стоимости"}
            await message.answer(t(lang, "enter_name"), reply_markup=broker_menu(lang))
            return

    if c.get("mode") == "broker_docs_info" and text == t(lang, "broker_docs_apply"):
        c["pending_form"] = "broker_name"
        c["form_data"] = {"lang": lang, "role": role, "service": t(lang, "broker_docs"), "price": "200 000 сум" if lang == "ru" else "200 000 so‘m", "title": "Проверка документов перед подачей"}
        await message.answer(t(lang, "enter_name"), reply_markup=broker_menu(lang))
        return

    if c.get("mode") == "broker_cert_menu":
        if text == t(lang, "broker_cert_check"):
            c["mode"] = "broker_cert_check_info"
            await message.answer(t(lang, "broker_cert_check_text"), reply_markup=broker_cert_apply_kb(lang))
            return
        if text == t(lang, "broker_cert_apply"):
            c["mode"] = "broker_cert_apply_agency"
            await message.answer(t(lang, "broker_cert_apply_text"), reply_markup=broker_agency_kb(lang))
            return

    if c.get("mode") == "broker_cert_check_info" and text == t(lang, "broker_cert_apply_btn"):
        c["pending_form"] = "broker_name"
        c["form_data"] = {"lang": lang, "role": role, "service": t(lang, "broker_cert_check"), "price": "200 000 сум" if lang == "ru" else "200 000 so‘m", "title": "Сертификация"}
        await message.answer(t(lang, "enter_name"), reply_markup=broker_menu(lang))
        return

    if c.get("mode") == "broker_cert_apply_agency":
        agencies = [t(lang, "broker_agency_plant"), t(lang, "broker_agency_vet"), t(lang, "broker_agency_cert")]
        if text in agencies:
            c["form_data"] = {"lang": lang, "role": role, "service": t(lang, "broker_cert_apply"), "title": "Подача заявки от имени импортёра", "agency": text}
            c["mode"] = "broker_cert_apply_service"
            if text == t(lang, "broker_agency_plant"):
                await message.answer(t(lang, "choose_service"), reply_markup=broker_plant_services_kb(lang))
            elif text == t(lang, "broker_agency_vet"):
                await message.answer(t(lang, "choose_service"), reply_markup=broker_vet_services_kb(lang))
            else:
                await message.answer(t(lang, "choose_service"), reply_markup=broker_cert_services_kb(lang))
            return

    if c.get("mode") == "broker_cert_apply_service":
        services = [t(lang, "broker_service_quarantine"), t(lang, "broker_service_akd"), t(lang, "broker_service_vet"), t(lang, "broker_service_conformity")]
        if text in services:
            c["form_data"]["subservice"] = text
            c["pending_form"] = "broker_name"
            await message.answer(t(lang, "enter_name"), reply_markup=broker_menu(lang))
            return

    if c.get("mode") == "broker_analytics_info" and text == t(lang, "broker_analytics_apply"):
        c["pending_form"] = "broker_name"
        c["form_data"] = {"lang": lang, "role": role, "service": t(lang, "broker_tnved_analytics"), "price": "1 000 000 сум" if lang == "ru" else "1 000 000 so‘m", "title": "Аналитика по ТН ВЭД коду"}
        await message.answer(t(lang, "enter_name"), reply_markup=broker_menu(lang))
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
        items = code_search(text)
        track(uid, username, lang, role or "", "code_search", query_code)

        if not items:
            await message.answer(t(lang, "nothing_found"), reply_markup=legal_menu(lang))
            return

        # If user entered 4 digits, prefer showing all matching variants for this prefix.
        if len(query_code) == 4:
            variants = [
                r for r in RECORDS
                if normalize_code(r.get("code", "")).startswith(query_code)
                and r.get("record_kind") == "exact"
            ]
            variants = dedupe(variants)

            if variants:
                out = f"<b>{t(lang, 'possible')}</b>\n\n"
                for i, item in enumerate(variants[:MAX_RESULTS_SHOW], 1):
                    out += format_item(item, lang, i) + "\n"

                if len(variants) > MAX_RESULTS_SHOW:
                    if lang == "ru":
                        out += f"\n⚠️ Показаны первые {MAX_RESULTS_SHOW} вариантов по префиксу <code>{query_code}</code>. Уточните запрос 6/8/10 цифрами.\n"
                    else:
                        out += f"\n⚠️ <code>{query_code}</code> prefiksi bo‘yicha dastlabki {MAX_RESULTS_SHOW} variant ko‘rsatildi. So‘rovni 6/8/10 raqam bilan aniqlang.\n"

                hint = ai_hint(text, variants[:6], lang)
                if hint:
                    out += "\n<b>AI:</b>\n" + hint + "\n"

                out += t(lang, "branch_hint")
                await send_safe_message(message, out, reply_markup=legal_menu(lang))
                return

            # fallback: if no exact variants inside 4-digit prefix, show first matching family result
            first_variant = items[:1]
            out = f"<b>{t(lang, 'code_result')}</b>\n\n"
            for i, item in enumerate(first_variant, 1):
                out += format_item(item, lang, i) + "\n"
            out += "\nПоказан первый вариант для 4-значного кода. Для точности лучше введите 6/8/10 цифр."
            await send_safe_message(message, out, reply_markup=legal_menu(lang))
            return

        out = f"<b>{t(lang, 'code_result')}</b>\n\n"
        for i, item in enumerate(items, 1):
            out += format_item(item, lang, i) + "\n"
        hint = ai_hint(text, items, lang)
        if hint:
            out += "\n<b>AI:</b>\n" + hint
        await send_safe_message(message, out, reply_markup=legal_menu(lang))
        return

    if c["mode"] == "legal_chat":
        faq_text = faq_answer(text, lang)
        if faq_text:
            await message.answer(faq_text + "\n\n" + t(lang, "free_specialist"), reply_markup=legal_ai_kb(lang))
            return

        if text in [t(lang, "faq_6"), t(lang, "ask_own")]:
            await message.answer("Напишите свой вопрос." if lang == "ru" else "Savolingizni yozing.", reply_markup=legal_ai_kb(lang))
            return

        if not looks_like_customs_question(text):
            await message.answer(t(lang, "only_customs"), reply_markup=legal_ai_kb(lang))
            return

        found_code = extract_code_from_text(text)
        items = code_search(found_code) if found_code else text_search(text)

        if items:
            out = ("<b>Найдено в базе:</b>\n\n" if lang == "ru" else "<b>Bazada topildi:</b>\n\n")
            for i, item in enumerate(items[:MAX_RESULTS_SHOW], 1):
                out += format_item(item, lang, i) + "\n"
            hint = ai_hint(text, items[:MAX_RESULTS_SHOW], lang)
            if hint:
                out += "\n<b>AI-комментарий:</b>\n" + hint + "\n"
            out += "\n" + t(lang, "free_specialist")
            await send_safe_message(message, out, reply_markup=legal_ai_kb(lang))
            return

        if client:
            try:
                resp = client.responses.create(model=OPENAI_MODEL, input=f"Ответь кратко на {'русском' if lang=='ru' else 'узбекском'} языке как помощник по таможенным вопросам Узбекистана. Отвечай только по теме таможни, импорта, экспорта, ТН ВЭД, документов, сертификации и ставок. После ответа задай 1 уточняющий вопрос. Запрос: {text}")
                await message.answer(((resp.output_text or '').strip() or t(lang, 'nothing_found')) + "\n\n" + t(lang, "free_specialist"), reply_markup=legal_ai_kb(lang))
            except Exception:
                await message.answer(t(lang, "nothing_found"), reply_markup=legal_ai_kb(lang))
            return

        await message.answer(t(lang, "nothing_found"), reply_markup=legal_ai_kb(lang))
        return

    if c["mode"] == "physical_ai_menu":
        if text == t(lang, "physical_ready"):
            c["mode"] = "physical_ready"
            await message.answer(t(lang, "physical_ready_intro"), reply_markup=physical_ready_kb(lang))
            return
        if text == t(lang, "physical_own"):
            c["mode"] = "physical_chat"
            await message.answer(t(lang, "physical_ask_own_intro"), reply_markup=physical_ai_kb(lang))
            return
        await message.answer(t(lang, "physical_ai_intro"), reply_markup=physical_ai_kb(lang))
        return

    if c["mode"] == "physical_ready":
        ready_answer = PHYSICAL_FAQ.get(lang, {}).get(text)
        if ready_answer:
            await message.answer(ready_answer + "\n\n" + t(lang, "physical_free_specialist"), reply_markup=physical_ready_kb(lang))
            return
        await message.answer(t(lang, "physical_ready_intro"), reply_markup=physical_ready_kb(lang))
        return

    if c["mode"] == "physical_posts_menu":
        if text == t(lang, "physical_posts_border"):
            c["mode"] = "physical_posts_border"
            await send_safe_message(message, posts_list_text(lang, "border"), reply_markup=physical_posts_menu_kb(lang))
            return
        if text == t(lang, "physical_posts_ved"):
            c["mode"] = "physical_posts_ved"
            await send_safe_message(message, posts_list_text(lang, "ved"), reply_markup=physical_posts_menu_kb(lang))
            return
        await message.answer(t(lang, "physical_posts_intro"), reply_markup=physical_posts_menu_kb(lang))
        return

    if c["mode"] in ["physical_posts_border", "physical_posts_ved"]:
        kind = "border" if c["mode"] == "physical_posts_border" else "ved"
        post = find_post_by_num(kind, text)
        if not post:
            await message.answer(t(lang, "physical_post_not_found"), reply_markup=physical_posts_menu_kb(lang))
            return
        c["mode"] = "physical_post_card"
        c["form_data"]["selected_post_kind"] = kind
        c["form_data"]["selected_post_num"] = post.get("num")
        has_loc = post.get("lat") is not None and post.get("lon") is not None
        await message.answer(post_card_text(lang, post), reply_markup=physical_post_card_kb(lang, has_loc))
        return

    if c["mode"] == "physical_post_card":
        if text == t(lang, "physical_location"):
            kind = c["form_data"].get("selected_post_kind")
            num = c["form_data"].get("selected_post_num")
            post = find_post_by_num(kind, str(num))
            if not post or post.get("lat") is None or post.get("lon") is None:
                await message.answer(t(lang, "physical_location_missing"), reply_markup=physical_post_card_kb(lang, False))
                return
            await bot.send_location(message.chat.id, latitude=float(post["lat"]), longitude=float(post["lon"]))
            await message.answer(post_card_text(lang, post), reply_markup=physical_post_card_kb(lang, True))
            return
        await message.answer(t(lang, "physical_free_specialist"), reply_markup=physical_post_card_kb(lang, True))
        return

    if c["mode"] == "physical_chat":
        faq_map = PHYSICAL_FAQ.get(lang, {})
        ready_answer = faq_map.get(text)

        if ready_answer:
            await send_safe_message(
                message,
                ready_answer + "\n\n" + t(lang, "physical_free_specialist"),
                reply_markup=physical_ai_kb(lang)
            )
            return

        user_q = normalize_text(text)

        commercial_markers = [
            "контейнер", "оптом", "партия", "для продажи", "коммерческ",
            "юрлиц", "гтд", "брокер", "контракт", "инвойс", "сертификат соответствия",
            "ulgurji", "sotish uchun", "partiya", "broker", "gtd", "kontrakt", "invoice"
        ]
        if any(x in user_q for x in commercial_markers):
            answer = (
                "Я помогаю физическим лицам только по вопросам личного пользования. Если вопрос связан с коммерческим импортом, лучше перейти в раздел для юр лиц или обратиться к специалисту."
                if lang == "ru"
                else
                "Men jismoniy shaxslar uchun faqat shaxsiy foydalanish bo‘yicha yordam beraman. Agar savol tijorat importiga oid bo‘lsa, yuridik shaxslar bo‘limiga o‘ting yoki mutaxassisga murojaat qiling."
            )
            await message.answer(answer, reply_markup=physical_ai_kb(lang))
            return

        customs_markers = [
            "bojxona", "olib kir", "olib chiq", "telefon", "iphone", "dori", "valyuta",
            "limit", "aeroport", "imei", "posilka", "post", "tamoj", "тамож",
            "ввоз", "вывоз", "телефон", "айфон", "лекар", "валют", "лимит", "аэропорт",
            "име", "посылк", "post", "почта", "bagaj", "багаж", "дубай", "dubay"
        ]

        if not any(x in user_q for x in customs_markers):
            answer = (
                "Я помогаю только по таможенным вопросам для физических лиц в Узбекистане. Например: телефоны, лекарства, лимиты, валюта, аэропорт, IMEI, личный ввоз."
                if lang == "ru"
                else
                "Men O‘zbekistonda jismoniy shaxslar uchun faqat bojxona savollariga yordam beraman. Masalan: telefon, dori, limit, valyuta, aeroport, IMEI, shaxsiy olib kirish."
            )
            await message.answer(answer, reply_markup=physical_ai_kb(lang))
            return

        local_hint = physical_answer(text, lang)

        if client:
            try:
                system_prompt = (
                    "Ты AI bojxonachi — помощник по таможенным вопросам Узбекистана для физических лиц. "
                    "Отвечай только по теме личного пользования. "
                    "Не отвечай как помощник для юрлиц, брокеров, ГТД, контрактов, коммерческого импорта и оптовых партий. "
                    "Если вопрос касается личного ввоза телефонов, iPhone, лекарств, валюты, багажа, лимитов, аэропорта, IMEI, посылок или таможенных постов — отвечай нормально и по-человечески. "
                    "Не отказывай слишком рано. "
                    "Если данных не хватает, задай 1 уточняющий вопрос. "
                    "Если точного правила не знаешь, скажи аккуратно, что нужна дополнительная проверка, но всё равно дай полезное объяснение. "
                    "В конце мягко предложи помощь специалиста."
                    if lang == "ru"
                    else
                    "Sen AI bojxonachi — O‘zbekistonda jismoniy shaxslar uchun bojxona bo‘yicha yordamchisan. "
                    "Faqat shaxsiy foydalanish masalalariga javob ber. "
                    "Yuridik shaxslar, brokerlar, GTD, kontrakt, tijorat importi yoki ulgurji partiyalar bo‘yicha javob bermagin. "
                    "Agar savol telefon, iPhone, dori, valyuta, bagaj, limit, aeroport, IMEI, posilka yoki bojxona postlari haqida bo‘lsa, odatiy aqlli yordamchi kabi tushunarli javob ber. "
                    "Juda tez rad javobini bermagin. "
                    "Agar ma’lumot yetmasa, 1 ta qisqa aniqlashtiruvchi savol ber. "
                    "Agar aniq qoidani bilmasang, tekshirish kerakligini ayt, lekin baribir foydali tushuntirish ber. "
                    "Oxirida mutaxassis yordamni muloyim taklif qil."
                )

                user_prompt = (
                    f"Javob tili: {'русский' if lang == 'ru' else 'o‘zbekcha'}.\n"
                    f"Lokal yordamchi izoh: {local_hint}\n"
                    f"Foydalanuvchi savoli: {text}"
                )

                resp = client.responses.create(
                    model=OPENAI_MODEL,
                    input=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ]
                )
                ans = (resp.output_text or "").strip()
                final_answer = ans or (local_hint + "\n\n" + t(lang, "physical_free_specialist"))
                await send_safe_message(message, final_answer, reply_markup=physical_ai_kb(lang))
                return
            except Exception:
                pass

        await send_safe_message(
            message,
            local_hint + "\n\n" + t(lang, "physical_free_specialist"),
            reply_markup=physical_ai_kb(lang)
        )
        return


    if c.get("pending_form") == "specialist_name":
        c["form_data"] = {"lang": lang, "role": role, "name": text}; c["pending_form"] = "specialist_tg"
        await message.answer(t(lang, "enter_tg")); return
    if c.get("pending_form") == "specialist_tg":
        c["form_data"]["tg"] = text; c["pending_form"] = "specialist_phone"
        await message.answer(t(lang, "enter_phone")); return
    if c.get("pending_form") == "specialist_phone":
        c["form_data"]["phone"] = text; c["pending_form"] = "specialist_question"
        await message.answer(t(lang, "enter_question")); return
    if c.get("pending_form") == "specialist_question":
        c["form_data"]["question"] = text; c["pending_form"] = None
        await send_specialist_application_to_admin(uid, username, c["form_data"])
        track(uid, username, lang, role or "", "application", text)
        await message.answer(t(lang, "specialist_done"), reply_markup=physical_menu(lang) if role == "physical" else legal_menu(lang) if role == "legal" else broker_menu(lang) if role == "broker" else logistics_menu(lang))
        c["form_data"] = {}
        return

    if c.get("pending_form") == "broker_name":
        c.setdefault("form_data", {})["name"] = text
        service = (c.get("form_data") or {}).get("service", "")
        if service == t(lang, "broker_docs"):
            c["pending_form"] = "broker_phone"
            await message.answer(t(lang, "enter_phone_broker"), reply_markup=broker_menu(lang)); return
        c["pending_form"] = "broker_tnved"
        await message.answer(t(lang, "enter_tnved"), reply_markup=broker_menu(lang)); return
    if c.get("pending_form") == "broker_tnved":
        c["form_data"]["tnved"] = text; c["pending_form"] = "broker_product"
        await message.answer(t(lang, "enter_description"), reply_markup=broker_menu(lang)); return
    if c.get("pending_form") == "broker_product":
        c["form_data"]["product"] = text; c["pending_form"] = "broker_dispatch_country"
        await message.answer(t(lang, "enter_dispatch_country"), reply_markup=broker_menu(lang)); return
    if c.get("pending_form") == "broker_dispatch_country":
        c["form_data"]["dispatch_country"] = text
        service = (c.get("form_data") or {}).get("service", "")
        if service in [t(lang, "broker_cost_low"), t(lang, "broker_cost_3m"), t(lang, "broker_docs")]:
            c["pending_form"] = "broker_phone"
            await message.answer(t(lang, "enter_phone_broker"), reply_markup=broker_menu(lang)); return
        c["pending_form"] = "broker_origin_country"
        await message.answer(t(lang, "enter_origin_country"), reply_markup=broker_menu(lang)); return
    if c.get("pending_form") == "broker_origin_country":
        c["form_data"]["origin_country"] = text; c["pending_form"] = "broker_phone"
        await message.answer(t(lang, "enter_phone_broker"), reply_markup=broker_menu(lang)); return
    if c.get("pending_form") == "broker_phone":
        c["form_data"]["phone"] = text; c["pending_form"] = "broker_comment"
        await message.answer(t(lang, "enter_comment_optional"), reply_markup=broker_menu(lang)); return
    if c.get("pending_form") == "broker_comment":
        c["form_data"]["comment"] = text
        service = (c.get("form_data") or {}).get("service", "")
        if service == t(lang, "broker_docs"):
            c["pending_form"] = "broker_docs_files"
            c["form_data"].setdefault("documents", [])
            await message.answer(t(lang, "broker_send_more_docs"), reply_markup=broker_docs_upload_kb(lang)); return
        await send_broker_application_to_admin(uid, username, c["form_data"], c["form_data"].get("title", "Broker PRO заявка"))
        track(uid, username, lang, role or "", "broker_application", c["form_data"].get("service", ""))
        c["pending_form"] = None
        c["form_data"] = {}
        await message.answer(t(lang, "broker_application_received"), reply_markup=broker_menu(lang)); return
    if c.get("pending_form") == "log_name":
        c["form_data"]["name"] = text; c["pending_form"] = "log_tg"
        await message.answer(t(lang, "enter_tg"), reply_markup=logistics_menu(lang)); return
    if c.get("pending_form") == "log_tg":
        c["form_data"]["tg"] = text; c["pending_form"] = "log_phone"
        await message.answer(t(lang, "enter_phone"), reply_markup=logistics_menu(lang)); return
    if c.get("pending_form") == "log_phone":
        c["form_data"]["phone"] = text; c["pending_form"] = "log_from"
        await message.answer(t(lang, "enter_from"), reply_markup=logistics_menu(lang)); return
    if c.get("pending_form") == "log_from":
        c["form_data"]["from"] = text; c["pending_form"] = "log_to"
        await message.answer(t(lang, "enter_to"), reply_markup=logistics_menu(lang)); return
    if c.get("pending_form") == "log_to":
        c["form_data"]["to"] = text; c["pending_form"] = "log_product"
        await message.answer("Какой товар:" if lang == "ru" else "Qanday tovar:", reply_markup=logistics_menu(lang)); return
    if c.get("pending_form") == "log_product":
        c["form_data"]["product"] = text; c["pending_form"] = "log_weight"
        await message.answer(t(lang, "enter_weight"), reply_markup=logistics_menu(lang)); return
    if c.get("pending_form") == "log_weight":
        c["form_data"]["weight"] = text; c["pending_form"] = "log_comment"
        await message.answer("Дополнительная информация:" if lang == "ru" else "Qo‘shimcha ma’lumot:", reply_markup=logistics_menu(lang)); return
    if c.get("pending_form") == "log_comment":
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

    if c.get("pending_form") == "broker_docs_files" and text == t(lang, "broker_finish_upload"):
        docs = (c.get("form_data") or {}).get("documents", [])
        if not docs:
            await message.answer(t(lang, "broker_need_doc"), reply_markup=broker_docs_upload_kb(lang))
            return
        await send_broker_application_to_admin(uid, username, c["form_data"], c["form_data"].get("title", "Проверка документов перед подачей"))
        track(uid, username, lang, role or "", "broker_application", c["form_data"].get("service", ""))
        c["pending_form"] = None
        c["form_data"] = {}
        await message.answer(t(lang, "broker_application_received_3h"), reply_markup=broker_menu(lang))
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


@dp.message_handler(content_types=types.ContentType.DOCUMENT)
async def broker_document_handler(message: types.Message):
    uid = message.from_user.id
    c = ctx(uid)
    lang = c["lang"]

    if c.get("pending_form") not in ["broker_docs_files", "broker_cert_apply_files"]:
        return

    if "documents" not in c["form_data"]:
        c["form_data"]["documents"] = []

    doc = message.document
    c["form_data"]["documents"].append({
        "file_id": doc.file_id,
        "file_name": doc.file_name or "document"
    })

    await message.answer(t(lang, "broker_doc_saved"), reply_markup=broker_docs_upload_kb(lang))


@dp.callback_query_handler(lambda call: call.data and call.data.startswith("appst:"))
async def application_status_callback(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    try:
        _, app_id_str, status = call.data.split(":", 2)
        app_id = int(app_id_str)
    except Exception:
        await call.answer("Ошибка")
        return

    app = get_application(app_id)
    if not app:
        await call.answer("Заявка не найдена", show_alert=True)
        return

    update_application_status(app_id, status)
    app = get_application(app_id)

    try:
        await call.message.edit_reply_markup(reply_markup=admin_app_status_kb(app_id, status))
    except Exception:
        pass

    user_lang = app.get("lang", "ru")
    notify_text = {
        "accepted": t(user_lang, "client_status_accepted"),
        "in_work": t(user_lang, "client_status_in_work"),
        "closed": t(user_lang, "client_status_closed"),
    }.get(status)
    if notify_text:
        try:
            await bot.send_message(app["user_id"], notify_text)
        except Exception:
            logging.exception("Telegram send failed")

    try:
        await call.answer(f"Заявка #{app_id}: {status_text('ru', status)}")
    except Exception:
        pass

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
