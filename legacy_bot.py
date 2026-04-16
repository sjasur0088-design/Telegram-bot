
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

from modules.texts import apply_text_patches
from modules.keyboards import (
    admin_apps_menu_kb as _admin_apps_menu_kb,
    admin_app_status_kb as _admin_app_status_kb,
)
from modules.analytics import is_admin as _helper_is_admin
from modules.applications import (
    admin_apps_text as _admin_apps_text,
    get_application as _get_application,
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

USER_CTX = {}
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
        "broker_intro":"Brokerlar va importyorlar uchun professional yordam\n\nMutaxassislarimiz O‘zbekiston bojxona sohasida 10–15 yillik amaliy tajribaga ega.\n\nBiz quyidagilarda yordam beramiz:\n• bojxona qiymati bo‘yicha ortiqcha to‘lovlarning oldini olish\n• hujjatlarni topshirishdan oldin tekshirish\n• sertifikatlash talablarini oldindan tushunish\n• mutaxassis uchun tayyor кейс/so‘rov tayyorlash\n\nKerakli xizmatni tanlang:",
        "broker_pick":"Xizmatni tanlang:",
        "broker_paid":"Bu pullik xizmat. Ariza yuborilgach, mutaxassis siz bilan bog‘lanadi.",
        "enter_name":"Ismingizni kiriting:",
        "enter_product":"Tovar / so‘rovni yozing:",
        "enter_country":"Kelib chiqish yoki jo‘natish davlatini kiriting:",
        "enter_comment":"Kerak bo‘lsa izoh qoldiring:",
        "service_min_avg":"Min. va o‘rtacha qiymat",
        "service_3m":"Oxirgi 3 oy bazasi",
        "application_sent":"✅ Ariza mutaxassisga yuborildi.",
        "broker_cost_text":"Bojxona qiymati tahlili\n\nNoto‘g‘ri bojxona qiymati ortiqcha to‘lovlarga, корректировка va rasmiylashtirishdagi kechikishlarga olib kelishi mumkin.\n\nBiz 2 ta pullik xizmatni taklif qilamiz:\n\n1) Eng past bojxona qiymatini aniqlash — 300 000 so‘m\n2) Oxirgi 3 oy bo‘yicha aniq bazani ko‘rish — 600 000 so‘m\n\nKerakli xizmatni tanlang:",
        "broker_cost_low":"1️⃣ Eng past bojxona qiymati",
        "broker_cost_3m":"2️⃣ Oxirgi 3 oy bazasi",
        "broker_docs_text":"GTD topshirishdan oldin hujjatlarni tekshirish\n\nKo‘plab tadbirkorlar bojxona rasmiylashtiruvida hujjatlardagi xatolar sabab vaqt va mablag‘ yo‘qotadi.\n\nHatto kichik xato ham quyidagi hujjatlarda:\n• invoice\n• kontrakt\n• packing list\n• transport hujjatlari\n\nquyidagilarga olib kelishi mumkin:\n• yukning kechikishi\n• qo‘shimcha tekshiruvlar\n• jarimalar\n• bojxona qiymatining oshishi\n\n👨‍💼 10–15 yillik tajribaga ega mutaxassislarimiz:\n• hujjatlaringizni topshirishdan oldin tekshiradi\n• xato va risklarni aniqlaydi\n• tuzatish bo‘yicha tavsiyalar beradi\n\n⏱ Tekshiruv muddati: 3 soatgacha\n💰 Narx: 200 000 so‘m\n\nQuyidagi tugma orqali tekshiruv uchun ariza qoldiring.",
        "broker_docs_apply":"📝 Ariza qoldirish",
        "broker_finish_upload":"✅ Hujjat yuklashni tugatish",
        "broker_send_more_docs":"Hujjatlarni birma-bir yuboring, so‘ng «✅ Hujjat yuklashni tugatish» tugmasini bosing.",
        "broker_need_doc":"Avval kamida bitta hujjat yuklang.",
        "broker_doc_saved":"Hujjat saqlandi. Yana yuborishingiz yoki tugatishingiz mumkin.",
        "broker_cert_text":"Sertifikatlash bo‘yicha nuanslar\n\nSertifikatlash importdan oldingi eng muhim bosqichlardan biridir. Bu yerda xato bo‘lsa, yuk kechikishi, ortiqcha xarajat va vaqt yo‘qotish bo‘lishi mumkin.\n\nBiz 2 ta xizmatni taklif qilamiz:\n\n1) TN VED bo‘yicha tovar qaysi sertifikatlarga tushishini aniqlash — 200 000 so‘m\n2) Importyor nomidan aniq xizmat bo‘yicha ariza topshirish\n\nKerakli xizmatni tanlang:",
        "broker_cert_check":"1️⃣ TN VED bo‘yicha sertifikatlarni bilish",
        "broker_cert_apply":"2️⃣ Importyor nomidan ariza topshirish",
        "broker_cert_check_text":"TN VED kodi bo‘yicha tovaringizga qaysi sertifikatlar, ruxsatnomalar yoki kelishuvlar kerak bo‘lishini aniqlab beramiz.\n\n💰 Narx: 200 000 so‘m\n\nAriza qoldirish uchun quyidagi tugmani bosing.",
        "broker_cert_apply_text":"Importyor nomidan ariza topshirish\n\nMutaxassislarimiz bu yo‘nalishda yaxshi tajribaga ega va so‘rovingizni to‘g‘ri rasmiylashtirishga yordam beradi.\n\nIsh tartibi va topshirishdagi nuanslarni yaxshi bilganimiz uchun so‘rovingiz keyingi ish jarayoniga ustuvor tarzda tayyorlanadi.\n\n⏱ Javob muddati tovar turiga qarab farq qiladi.\n\nMuassasani tanlang:",
        "broker_cert_apply_btn":"📝 Ariza qoldirish",
        "broker_agency_plant":"1️⃣ O‘simliklar karantini va himoyasi agentligi",
        "broker_agency_vet":"2️⃣ Veterinariya qo‘mitasi",
        "broker_agency_cert":"3️⃣ Sertifikatlash organlari",
        "broker_service_quarantine":"1. Karantin ruxsatnomasi (import uchun)",
        "broker_service_akd":"2. AKD",
        "broker_service_vet":"1. Veterinariya ruxsatnomasi",
        "broker_service_conformity":"1. Muvofiqlik sertifikati",
        "broker_analytics_text":"TN VED kod bo‘yicha analitika\n\nBozorni tushunish va tahlil qilish biznesning eng muhim qismlaridan biridir.\n\nTN VED kodi orqali quyidagilarni bilish mumkin:\n• bir yil davomida qancha va qaysi tovarlar o‘tganini\n• aniq nisha bo‘yicha faollikni\n• tovar harakatining umumiy hajmini\n\nBu importdan oldin aniqroq qaror qabul qilishga yordam beradi.\n\n💰 Xizmat narxi: 1 000 000 so‘m / 1 kod\n\nAriza qoldirish uchun quyidagi tugmani bosing.",
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

apply_text_patches(TXT)

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
        "Лекарства": (
            "Для личного пользования обычно можно:\n"
            "— до 10 видов лекарств\n"
            "— до 5 упаковок каждого\n\n"
            "Наркотические и психотропные препараты — только по специальному порядку."
        ),
        "Сигареты и алкоголь": (
            "Можно ввозить:\n"
            "— сигареты до 200 штук\n"
            "— сигары до 5 штук\n"
            "— табак до 100 грамм\n"
            "— алкоголь до 2 литров\n\n"
            "Эти нормы учитываются вместе с общим лимитом по стоимости."
        ),
        "Техника": (
            "Техника для личного пользования:\n"
            "— обычно 1 штука каждого вида\n"
            "— 1 раз в 6 месяцев\n\n"
            "Лимиты по стоимости:\n"
            "— аэропорт до 1000$\n"
            "— авто/пешком до 300$\n"
            "— ж/д и речной до 500$"
        ),
        "Валюта": (
            "Ввоз валюты — без ограничений.\n\n"
            "Вывоз:\n"
            "— до 100 млн сум эквивалента\n\n"
            "При больших суммах может требоваться декларация."
        ),
        "Что запрещено": (
            "Запрещено или требует разрешения:\n"
            "— наркотики и психотропные вещества\n"
            "— оружие и боеприпасы\n"
            "— дроны\n"
            "— пиротехника\n"
            "— культурные ценности"
        ),
        "Сколько можно без пошлины": (
            "Без пошлины можно:\n"
            "— аэропорт до 1000$\n"
            "— ж/д и речной до 500$\n"
            "— авто/пешком до 300$\n"
            "— курьер до 200$\n"
            "— почта до 100$"
        )
    },
    "uz": {
        "Dorilar": (
            "Shaxsiy foydalanish uchun:\n"
            "— 10 xil dorigacha\n"
            "— har biridan 5 qadoqqacha\n\n"
            "Narkotik va psixotrop dorilar alohida tartibda."
        ),
        "Sigaret va alkogol": (
            "Olib kirish mumkin:\n"
            "— sigaret 200 dona\n"
            "— sigara 5 dona\n"
            "— tamaki 100 gramm\n"
            "— alkogol 2 litr\n\n"
            "Bu me'yorlar umumiy qiymat limiti bilan hisoblanadi."
        ),
        "Texnika": (
            "Texnika:\n"
            "— odatda 1 dona\n"
            "— 6 oyda 1 marta\n\n"
            "Qiymat limiti:\n"
            "— aeroport 1000$\n"
            "— avto/piyoda 300$\n"
            "— temir yo'l 500$"
        ),
        "Valyuta": (
            "Valyuta olib kirish — cheklanmagan.\n\n"
            "Olib chiqish:\n"
            "— 100 mln so‘mgacha\n\n"
            "Katta summa bo‘lsa deklaratsiya talab qilinadi."
        ),
        "Nima taqiqlangan": (
            "Taqiqlangan yoki ruxsat talab qiladi:\n"
            "— narkotik va psixotrop moddalar\n"
            "— qurol va o‘q-dori\n"
            "— dron\n"
            "— pirotexnika\n"
            "— madaniy boyliklar"
        ),
        "Bojsiz qancha mumkin": (
            "Bojsiz:\n"
            "— aeroport 1000$\n"
            "— temir yo‘l 500$\n"
            "— avto/piyoda 300$\n"
            "— kuryer 200$\n"
            "— pochta 100$"
        )
    }
}


def load_physical_faq_pro():
    path = os.path.join(BASE_DIR, "physical_faq.json")
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                obj = json.load(f)
                if isinstance(obj, dict):
                    return obj
    except Exception as e:
        logging.exception("Error loading physical_faq.json: %s", e)
    return {"ru": {"faq_items": [], "global_rules": {}}, "uz": {"faq_items": [], "global_rules": {}}}

PHYSICAL_FAQ_PRO = load_physical_faq_pro()


def physical_pro_state(c: Dict[str, Any]) -> Dict[str, Any]:
    return c.setdefault("physical_pro_state", {})


def physical_set_pro_topic(c: Dict[str, Any], topic: str, source_text: str = "") -> None:
    c["physical_pro_state"] = {"topic": topic or "", "source_text": (source_text or "")[:500]}


def physical_get_pro_topic(c: Dict[str, Any]) -> str:
    return physical_pro_state(c).get("topic", "")


def physical_clear_pro_state(c: Dict[str, Any]) -> None:
    c["physical_pro_state"] = {}


def physical_pro_guess_topic(text: str) -> str:
    q = normalize_text(text)
    if any(x in q for x in ["лекар", "dori", "tablet", "таблет", "цитрамон", "sitramon", "парацетамол", "анальгин", "ibuprofen", "ибупрофен"]):
        return "medicine"
    if any(x in q for x in ["телевизор", "tv", "smart tv", "смарт тв"]):
        return "tv"
    if any(x in q for x in ["телефон", "айфон", "смартфон", "iphone", "telefon", "phone"]):
        return "phones"
    if any(x in q for x in ["ноутбук", "noutbuk", "laptop"]):
        return "notebook"
    if any(x in q for x in ["валют", "valyuta", "доллар", "usd", "евро", "eur", "sum", "сум"]):
        return "currency"
    if any(x in q for x in ["пиротех", "салют", "petard", "pirotex"]):
        return "pyro"
    if any(x in q for x in ["авто", "машин", "mashina", "avto", "автомобиль"]):
        return "auto"
    if any(x in q for x in ["ввоз", "вывоз", "olib kir", "olib chiq", "аэропорт", "границ", "chegara"]):
        return "import"
    return ""


def physical_pro_pattern_answer(text: str, lang: str) -> str:
    q = normalize_text(text)
    best_answer = ""
    best_score = 0
    for item in PHYSICAL_FAQ_PRO.get(lang, {}).get("faq_items", []):
        score = 0
        for p in item.get("patterns", []):
            p_norm = normalize_text(str(p))
            if not p_norm:
                continue
            if p_norm in q:
                score += 3
            else:
                for w in [w for w in p_norm.split() if len(w) >= 3]:
                    if w in q:
                        score += 1
        if score > best_score and item.get("answer"):
            best_score = score
            best_answer = item.get("answer", "").strip()

    if best_score >= 3 and best_answer:
        return best_answer

    topic = physical_pro_guess_topic(text)
    if topic == "tv":
        return (
            "Для личного пользования можно привезти 1 телевизор. Через автодорожные, пешеходные, железнодорожные и речные пункты для телевизора действует норма 1 единица на 6 календарных месяцев. По стоимости лимит зависит от способа въезда: через аэропорт — до 1000 долларов США, через автодорожную или пешеходную границу — до 300 долларов США. Если стоимость выше лимита, на превышение могут начисляться таможенные платежи."
            if lang == "ru" else
            "Shaxsiy foydalanish uchun 1 dona televizor olib kirish mumkin. Quruqlik, temir yo‘l va daryo punktlari orqali televizor uchun 6 kalendar oyda 1 dona me’yor qo‘llanadi. Qiymat limiti kirish usuliga bog‘liq: aeroport orqali — 1000 AQSH dollari, avtoyo‘l yoki piyoda chegara orqali — 300 AQSH dollari. Limitdan oshsa, ortiqcha qismiga bojxona to‘lovlari qo‘llanishi mumkin."
        )
    if topic == "notebook":
        return (
            "Через автодорожные, пешеходные, железнодорожные и речные пункты ноутбук для личного пользования обычно можно ввозить в количестве 1 единица на 6 календарных месяцев. Если ноутбуков 2 и более, это уже может считаться превышением нормы и таможня может дополнительно оценивать цель ввоза."
            if lang == "ru" else
            "Avtoyo‘l, piyoda, temir yo‘l va daryo punktlari orqali noutbukni shaxsiy foydalanish uchun odatda 6 kalendar oyda 1 dona olib kirish mumkin. Agar noutbuk 2 dona yoki undan ko‘p bo‘lsa, bu me’yor oshishi hisoblanishi va bojxona olib kirish maqsadini qo‘shimcha baholashi mumkin."
        )
    if topic == "phones":
        return (
            "Через аэропорт для телефонов действует норма до 2 единиц при каждом въезде. Если устройств больше или они выглядят как партия, таможня может оценить это как не для личного пользования."
            if lang == "ru" else
            "Aeroport orqali telefonlar uchun har kirishda 2 donagacha me’yor qo‘llanadi. Qurilmalar ko‘p bo‘lsa yoki partiyaga o‘xshasa, bojxona buni shaxsiy foydalanish emas deb baholashi mumkin."
        )
    if topic == "currency":
        return (
            "Ввоз наличной валюты физлицами в Узбекистан не ограничен. Вывоз разрешён до эквивалента 100 000 000 сумов. Сверх этой суммы действует отдельный порядок."
            if lang == "ru" else
            "Jismoniy shaxslar tomonidan naqd valyutani O‘zbekistonga olib kirish cheklanmagan. Olib chiqish 100 000 000 so‘m ekvivalentigacha ruxsat etiladi. Undan yuqori summa uchun alohida tartib mavjud."
        )
    if topic == "medicine" and any(x in q for x in ["можно", "qanday", "какие", "какой", "dori", "лекар", "таблет"]):
        return (
            "Для личного пользования лекарства ввозить и вывозить можно. Без меддокумента обычно допускается до 10 разных препаратов и не более 5 упаковок каждого. Для наркотических и психотропных веществ правила строже."
            if lang == "ru" else
            "Shaxsiy foydalanish uchun dori vositalarini olib kirish va olib chiqish mumkin. Tibbiy hujjatsiz odatda 10 xil preparat va har biridan 5 qadoqgacha ruxsat etiladi. Narkotik va psixotrop moddalar uchun qoidalar qat’iyroq."
        )
    if topic == "auto":
        return (
            "По транспортным средствам для физлиц действует отдельный порядок. Временный ввоз автомобиля для некоммерческих целей обычно не должен превышать 90 календарных дней в течение года, если иное не оформлено в установленном порядке."
            if lang == "ru" else
            "Transport vositalari bo‘yicha jismoniy shaxslar uchun alohida tartib mavjud. Nokommersiya maqsadida avtomobilni vaqtincha olib kirish odatda bir yil davomida 90 kalendar kundan oshmasligi kerak, agar boshqacha tartibda rasmiylashtirilmagan bo‘lsa."
        )
    return ""


def physical_pro_global_hint(text: str, lang: str) -> str:
    topic = physical_pro_guess_topic(text)
    rules = PHYSICAL_FAQ_PRO.get(lang, {}).get("global_rules", {})
    if topic == "currency":
        return rules.get("currency", "")
    if topic == "medicine":
        return rules.get("med", "")
    if topic == "auto":
        return rules.get("auto", "")
    if topic in {"import", "tv", "phones", "notebook"}:
        return rules.get("import", "")
    return ""




def _physical_answer_legacy_fallback(text: str, lang: str) -> str:
    return (
        "Для точного ответа по физлицу нужны данные. Напишите товар, количество и как именно вы пересекаете границу."
        if lang == "ru" else
        "Jismoniy shaxs bo‘yicha aniq javob uchun ma'lumot kerak. Tovarni, miqdorini va chegarani qanday kesib o‘tayotganingizni yozing."
    )

physical_answer_legacy = _physical_answer_legacy_fallback

def physical_answer(text: str, lang: str) -> str:
    ans = physical_pro_pattern_answer(text, lang)
    if ans:
        return ans
    hint = physical_pro_global_hint(text, lang)
    if hint:
        return hint
    return physical_answer_legacy(text, lang)


def physical_needs_ai_followup(text: str, c: Dict[str, Any], lang: str) -> bool:
    q = normalize_text(text)
    topic = physical_get_pro_topic(c)
    if not topic:
        return False
    if text in PHYSICAL_FAQ.get(lang, {}):
        return False
    if looks_like_new_question(text):
        return False
    if is_legal_commercial_question(text):
        return False

    generic_ru = ["можно", "нельзя", "сколько", "какие", "какой", "товар", "лекарство", "лекарства", "телефон", "телевизор", "ноутбук", "валюта"]
    generic_uz = ["mumkin", "qancha", "qanday", "qaysi", "dori", "telefon", "televizor", "noutbuk", "valyuta"]
    generic = generic_uz if lang == "uz" else generic_ru

    if topic == "medicine":
        if 1 <= len(q.split()) <= 4 and not any(w in q for w in generic):
            return True
        if any(ch.isdigit() for ch in text):
            return True
    if topic in {"tv", "phones", "notebook", "currency", "auto", "import"}:
        if 1 <= len(q.split()) <= 8:
            return True
    return False


def build_physical_ai_prompt(user_text: str, c: Dict[str, Any], lang: str) -> str:
    topic = physical_get_pro_topic(c) or physical_pro_guess_topic(user_text)
    if lang == "uz":
        base = (
            "Sen O‘zbekiston bojxona masalalari bo‘yicha jismoniy shaxslar uchun yordamchisan. "
            "Avval shaxsiy foydalanish qoidalariga tayangan holda javob ber. "
            "Yuridik shaxslar, brokerlik yoki TN VED mavzusiga o‘tib ketma. "
            "Agar foydalanuvchi aniq dori nomini yozsa, bu dori odatda oddiy shaxsiy foydalanish dorisiga o‘xshaydimi, shuni tushuntir. "
            "Narkotik va psixotrop moddalar uchun qoidalar qat’iyroq ekanini ayt. "
            "Keraksiz savollar bermagin. Javobni qisqa, aniq va qonunga yaqin uslubda yoz."
        )
    else:
        base = (
            "Ты помощник по таможенным вопросам Узбекистана для физических лиц. "
            "Сначала отвечай по правилам личного пользования. "
            "Не уводи ответ в юрлица, брокера или ТН ВЭД. "
            "Если пользователь пишет конкретное название лекарства, объясни, похоже ли это на обычный препарат для личного пользования. "
            "Отдельно укажи, что для наркотических и психотропных веществ правила строже. "
            "Не задавай лишних вопросов. Пиши кратко, уверенно и по делу."
        )
    local = []
    hint = physical_pro_global_hint(user_text, lang)
    patt = physical_pro_pattern_answer(user_text, lang)
    if hint:
        local.append(hint)
    if patt:
        local.append(patt)
    if not local and topic == "medicine":
        local.append("Без меддокумента обычно допускается до 10 разных препаратов и до 5 упаковок каждого." if lang == "ru" else "Tibbiy hujjatsiz odatda 10 xil preparat va har biridan 5 qadoqgacha ruxsat etiladi.")
    if local:
        return base + ("\n\nЛокальный контекст:\n- " if lang == "ru" else "\n\nMahalliy kontekst:\n- ") + "\n- ".join(local)
    return base


def physical_ai_answer(user_text: str, c: Dict[str, Any], lang: str) -> str:
    if not client:
        return ""
    try:
        prompt = build_physical_ai_prompt(user_text, c, lang)
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_text},
            ],
            temperature=0.2,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        logging.exception("physical_ai_answer error: %s", e)
        return ""


def looks_like_physical_customs_question(text: str) -> bool:
    q = normalize_text(text)
    markers = [
        "телефон", "iphone", "айфон", "смартфон", "phone", "telefon",
        "dori", "лекар", "tablet", "таблет", "sitramon", "цитрамон",
        "валют", "valyuta", "доллар", "usd",
        "норм", "me'yor", "oshsa", "превыш",
        "для себя", "личного пользования", "shaxsiy foydalanish",
        "аэропорт", "airport", "aeroport", "post", "пост", "границ", "chegara",
        "вывезти", "ввезти", "olib kir", "olib chiq",
        "из дубая", "dubay", "из казахстана", "qozog'iston", "rossiya", "кыргызстан"
    ]
    return any(m in q for m in markers)


def classify_goods_type(text: str) -> str:
    q = normalize_text(text)
    food_words = [
        "помидор", "томат", "tomat", "огур", "bodring", "яблок", "olma", "banana", "banan",
        "meva", "fruit", "овощ", "sabzavot", "go'sht", "мясо", "kuritsa", "курица"
    ]
    medicine_words = ["лекар", "dori", "tablet", "таблет", "цитрамон", "sitramon", "paratsetamol", "парацетамол"]
    phone_words = ["iphone", "айфон", "телефон", "смартфон", "phone", "telefon"]
    auto_words = ["авто", "машин", "mashina", "avto", "tesla", "byd", "гибрид", "gibrid", "электро", "elektro"]

    if any(w in q for w in food_words):
        return "food"
    if any(w in q for w in medicine_words):
        return "medicine"
    if any(w in q for w in phone_words):
        return "phone"
    if any(w in q for w in auto_words):
        return "auto"
    return "general"

def is_personal_use_question(text: str) -> bool:
    q = normalize_text(text)
    markers = [
        "для себя", "для личного", "личного пользования", "1 dona", "один", "одна штука",
        "o'zim uchun", "shaxsiy foydalanish", "oila uchun", "семья", "для семьи"
    ]
    return any(m in q for m in markers)

def is_legal_commercial_question(text: str) -> bool:
    q = normalize_text(text)
    markers = [
        "для продажи", "коммер", "оптом", "партия", "контейнер", "broker", "брокер",
        "юрлиц", "yuridik", "gtd", "гтд", "контракт", "invoice", "invoys", "tn ved", "тн вэд",
        "сертификат соответствия", "ставка", "stavka", "код", "код тн вэд", "пошлина", "boj", "qqs"
    ]
    return any(m in q for m in markers)


def physical_set_state(c: Dict[str, Any], topic: str, lang: str) -> None:
    c["physical_ai_state"] = {
        "topic": topic,
        "lang": lang,
        "product": "",
        "quantity": "",
        "country": "",
        "awaiting": "product",
    }

def physical_get_state(c: Dict[str, Any]) -> Dict[str, Any]:
    return c.setdefault("physical_ai_state", {})

def physical_clear_state(c: Dict[str, Any]) -> None:
    c["physical_ai_state"] = {}

def physical_has_quantity(text: str) -> bool:
    q = normalize_text(text)
    qty_words = ["шт", "штук", "упаков", "qadoq", "dona", "ta ", " пач", "pack", "box", "kg", "кг", "litr", "литр"]
    has_digit = any(ch.isdigit() for ch in text)
    return has_digit or any(w in q for w in qty_words)

def physical_has_country(text: str) -> bool:
    q = normalize_text(text)
    countries = [
        "дубай", "dubay", "оаэ", "uae", "казахстан", "qozog'iston", "qozoqiston",
        "россия", "russia", "кыргызстан", "qirg'iziston", "киргизия",
        "китай", "xitoy", "турция", "turkiya", "корея", "koreya",
        "германия", "germaniya", "европа", "yevropa"
    ]
    return any(cn in q for cn in countries) or q.startswith("из ") or q.startswith("dan ")

def physical_followup_topic(text: str, lang: str) -> str:
    q = normalize_text(text)
    faq_map = PHYSICAL_FAQ.get(lang, {})
    if text in faq_map:
        if "норм" in q or "norma" in q:
            return "norm_exceeded"
        if "док" in q or "dori" in q or "лекар" in q:
            return "medicine"
        if "телефон" in q or "phone" in q or "telefon" in q:
            return "phones"
        if "валют" in q or "valyuta" in q:
            return "currency"
    if any(x in q for x in ["норм", "oshsa", "превыш", "me'yor"]):
        return "norm_exceeded"
    if any(x in q for x in ["док", "лекар", "dori"]):
        return "medicine"
    if any(x in q for x in ["телефон", "iphone", "phone", "telefon"]):
        return "phones"
    if any(x in q for x in ["валют", "valyuta"]):
        return "currency"
    return ""

def physical_followup_answer(topic: str, detail: str, lang: str, state: Dict[str, Any] = None) -> str:
    item = detail.strip()
    q = normalize_text(item)
    state = state or {}
    product = state.get("product", "").strip()
    quantity = state.get("quantity", "").strip()
    country = state.get("country", "").strip()

    current_name = product or item

    if topic == "medicine":
        if not product:
            return (
                f"По лекарству «{item}» ключевое — состав и количество. Теперь напишите, сколько упаковок вы везёте."
                if lang == "ru" else
                f"«{item}» dori bo‘yicha asosiy masala — tarkibi va miqdori. Endi nechta qadoq olib kirayotganingizni yozing."
            )
        if product and not quantity:
            return (
                f"По лекарству «{product}» теперь нужен объём. Напишите, сколько упаковок вы везёте."
                if lang == "ru" else
                f"«{product}» bo‘yicha endi miqdor kerak. Nechta qadoq olib kirayotganingizni yozing."
            )
        if product and quantity and not country:
            return (
                f"По лекарству «{product}» в количестве {quantity} для личного пользования обычно смотрят состав, разумный объём и возможные ограничения по препарату. "
                "По отдельным лекарствам могут потребоваться дополнительные документы. Теперь напишите, из какой страны ввозите."
                if lang == "ru" else
                f"«{product}» dorisini {quantity} miqdorda shaxsiy foydalanish uchun olib kirishda odatda tarkib, me’yoriy miqdor va preparat bo‘yicha cheklovlar ko‘riladi. "
                "Ayrim dorilar uchun qo‘shimcha hujjatlar talab qilinishi mumkin. Endi qaysi davlatdan olib kirayotganingizni yozing."
            )
        return (
            f"По лекарству «{product}» в количестве {quantity} из {country} для личного пользования обычно смотрят состав, объём и возможные ограничения по препарату. "
            "Если препарат обычный и количество разумное, ситуация обычно проще. Если хотите, следующим сообщением я подскажу, на что обратить внимание на границе."
            if lang == "ru" else
            f"«{product}» dorisini {quantity} miqdorda {country}dan shaxsiy foydalanish uchun olib kirishda odatda tarkib, miqdor va preparat bo‘yicha cheklovlar ko‘riladi. "
            "Agar dori oddiy bo‘lsa va miqdor me’yorida bo‘lsa, vaziyat odatda yengilroq bo‘ladi. Xohlasangiz, keyingi xabarda chegarada nimalarga e’tibor berish kerakligini yozaman."
        )

    if topic == "phones":
        if not product:
            return (
                f"По телефону «{item}» для физлица ключевое — количество. Теперь напишите, сколько именно телефонов вы везёте."
                if lang == "ru" else
                f"«{item}» telefoni bo‘yicha jismoniy shaxs uchun asosiy masala — soni. Endi nechta telefon olib kirayotganingizni yozing."
            )
        if product and not quantity:
            return (
                f"По телефону «{product}» теперь нужен точный объём. Напишите, сколько именно устройств вы везёте."
                if lang == "ru" else
                f"«{product}» telefoni bo‘yicha endi aniq son kerak. Nechta qurilma olib kirayotganingizni yozing."
            )
        if product and quantity and not country:
            return (
                f"По телефону «{product}» в количестве {quantity} для физлица смотрят личное пользование, стоимость и признаки коммерческой партии. "
                "Один для себя обычно проще, чем несколько одинаковых устройств. Теперь напишите, откуда ввозите."
                if lang == "ru" else
                f"«{product}» telefonini {quantity} miqdorda olib kirishda jismoniy shaxs uchun shaxsiy foydalanish, qiymat va tijorat partiyasi alomatlari ko‘riladi. "
                "O‘zingiz uchun 1 dona odatda bir nechta bir xil qurilmaga qaraganda osonroq. Endi qayerdan olib kirayotganingizni yozing."
            )
        return (
            f"По телефону «{product}» в количестве {quantity} из {country} для физлица смотрят личное пользование, стоимость, IMEI-регистрацию и признаки коммерческой партии. "
            "Если это один телефон для себя, ситуация обычно проще. Если хотите, следующим сообщением я скажу, что важно на границе."
            if lang == "ru" else
            f"«{product}» telefonini {quantity} miqdorda {country}dan olib kirishda jismoniy shaxs uchun shaxsiy foydalanish, qiymat, IMEI ro‘yxatdan o‘tkazish va tijorat alomatlari ko‘riladi. "
            "Agar bu o‘zingiz uchun 1 dona bo‘lsa, vaziyat odatda osonroq. Xohlasangiz, keyingi xabarda chegarada nimalar muhimligini aytaman."
        )

    if topic == "norm_exceeded":
        if not product:
            return (
                f"Если речь о товаре «{item}», сначала нужен сам товар. Теперь напишите количество или примерную стоимость."
                if lang == "ru" else
                f"Agar gap «{item}» haqida bo‘lsa, keyingi qadam — miqdor yoki taxminiy qiymat. Endi shuni yozing."
            )
        if product and not quantity:
            return (
                f"По товару «{product}» теперь нужен объём или примерная стоимость. Напишите количество."
                if lang == "ru" else
                f"«{product}» bo‘yicha endi miqdor yoki taxminiy qiymat kerak. Miqdorini yozing."
            )
        return (
            f"Если норма превышена по товару «{product}» в объёме {quantity}, могут применяться таможенные платежи. "
            "Точный ответ зависит от способа въезда и стоимости. Напишите, откуда и как вы въезжаете."
            if lang == "ru" else
            f"Agar me’yor «{product}» bo‘yicha {quantity} miqdorda oshsa, bojxona to‘lovlari qo‘llanishi mumkin. "
            "Aniq javob kirish usuli va qiymatga bog‘liq. Qayerdan va qanday kirayotganingizni yozing."
        )

    if topic == "currency":
        return (
            f"По валюте для точного ответа нужна сумма и вид валюты. Напишите точную сумму."
            if lang == "ru" else
            f"Valyuta bo‘yicha aniq javob uchun summa va valyuta turi kerak. Aniq summani yozing."
        )

    return (
        f"Уточните товар, количество и страну: сейчас данных мало."
        if lang == "ru" else
        f"Tovar, miqdor va davlatni aniqlashtiring: hozir ma’lumot yetarli emas."
    )


def ai_state(c: Dict[str, Any]) -> Dict[str, Any]:
    return c.setdefault("ai_state", {})

def ai_clear_state(c: Dict[str, Any]) -> None:
    c["ai_state"] = {}

def ai_set_state(c: Dict[str, Any], topic: str, lang: str) -> None:
    c["ai_state"] = {
        "topic": topic,
        "lang": lang,
        "product": "",
        "country": "",
        "purpose": "",
        "awaiting": "product",
    }

def looks_like_new_question(text: str) -> bool:
    q = normalize_text(text)
    question_words = [
        "какие", "какой", "как", "сколько", "можно", "нужно", "надо", "что",
        "qanday", "qancha", "mumkin", "kerak", "kerakmi", "nima", "qaysi"
    ]
    return "?" in text or any(q.startswith(w) for w in question_words)

def detect_country_value(text: str) -> str:
    raw = text.strip()
    q = normalize_text(text)
    countries = [
        "uzbekistan", "uzbekiston", "россия", "russia", "казахстан", "qozog'iston", "qozoqiston",
        "киргизия", "qirg'iziston", "кыргызстан", "китай", "xitoy", "турция", "turkiya",
        "корея", "koreya", "дубай", "uae", "oae", "germaniya", "германия", "европа", "yevropa"
    ]
    if q.startswith("из ") or q.startswith("from ") or q.startswith("из страны ") or q.startswith("страна "):
        return raw
    if q.startswith("dan ") or q.startswith("dan olib") or q.startswith("qayerdan "):
        return raw
    if any(c in q for c in countries):
        return raw
    return ""

def detect_purpose_value(text: str) -> str:
    raw = text.strip()
    q = normalize_text(text)
    purpose_keys = [
        "для продажи", "на продажу", "коммер", "для себя", "личного пользования",
        "sotish uchun", "savdo uchun", "kommersiya", "o'zim uchun", "shaxsiy foydalanish"
    ]
    if any(k in q for k in purpose_keys):
        return raw
    return ""

def ai_topic_from_text(text: str, lang: str) -> str:
    q = normalize_text(text)
    if any(x in q for x in ["документ", "hujjat"]) and any(x in q for x in ["импорт", "import"]):
        return "import_docs"
    if any(x in q for x in ["документ", "hujjat"]) and any(x in q for x in ["экспорт", "eksport"]):
        return "export_docs"
    if any(x in q for x in ["сертифик", "sertifikat", "разреш", "ruxsat"]):
        return "certs"
    if any(x in q for x in ["тн вэд", "tn ved", "код", "kodi"]):
        return "tnved"
    if any(x in q for x in ["платеж", "пошлин", "ставк", "boj", "qqs", "ндс", "to'lov"]):
        return "payments"
    return ""

def ai_base_topic_answer(topic: str, lang: str) -> str:
    if topic == "import_docs":
        return (
            "Это зависит от товара. Обычно для импорта нужны:\n"
            "• контракт\n• инвойс\n• упаковочный лист\n• транспортные документы\n• при необходимости сертификаты и разрешения\n\n"
            "Напишите, о каком товаре идёт речь."
            if lang == "ru" else
            "Bu tovarga bog‘liq. Import uchun odatda kerak bo‘ladi:\n"
            "• kontrakt\n• invoys\n• qadoqlash varaqasi\n• transport hujjatlari\n• zarur bo‘lsa sertifikat va ruxsatnomalar\n\n"
            "Qaysi tovar haqida gap ketayotganini yozing."
        )
    if topic == "export_docs":
        return (
            "Это зависит от товара и страны отправки. Обычно для экспорта нужны:\n"
            "• контракт\n• инвойс\n• упаковочный лист\n• транспортные документы\n• при необходимости разрешительные документы\n\n"
            "Напишите, о каком товаре идёт речь."
            if lang == "ru" else
            "Bu tovar va jo‘natish davlatiga bog‘liq. Eksport uchun odatda kerak bo‘ladi:\n"
            "• kontrakt\n• invoys\n• qadoqlash varaqasi\n• transport hujjatlari\n• zarur bo‘lsa ruxsatnomalar\n\n"
            "Qaysi tovar haqida gap ketayotganini yozing."
        )
    if topic == "certs":
        return (
            "Сертификаты зависят от товара, состава и назначения. Могут понадобиться:\n"
            "• сертификат соответствия\n• санитарно-эпидемиологическое заключение\n• фитосанитарные документы\n• иные разрешения\n\n"
            "Напишите, о каком товаре идёт речь."
            if lang == "ru" else
            "Sertifikatlar tovar, tarkib va maqsadga bog‘liq. Kerak bo‘lishi mumkin:\n"
            "• muvofiqlik sertifikati\n• sanitariya-epidemiologik xulosa\n• fitosanitariya hujjatlari\n• boshqa ruxsatnomalar\n\n"
            "Qaysi tovar haqida gap ketayotganini yozing."
        )
    if topic == "tnved":
        return (
            "TN VED kodi tovarning vazifasi, tarkibi, materiali va texnik xususiyatlariga qarab aniqlanadi.\n\nQaysi tovar uchun kod aniqlash kerak?"
            if lang != "ru" else
            "Код ТН ВЭД определяется по назначению, составу, материалу и характеристикам товара.\n\nНапишите, какой именно товар нужно определить."
        )
    if topic == "payments":
        return (
            "Таможенные платежи зависят от кода ТН ВЭД, стоимости, страны происхождения и цели ввоза. Обычно рассматриваются пошлина, НДС, а по некоторым товарам акциз и утильсбор.\n\nНапишите, о каком товаре идёт речь."
            if lang == "ru" else
            "Bojxona to‘lovlari TN VED kodi, qiymat, kelib chiqish davlati va olib kirish maqsadiga bog‘liq. Odatda boj, QQS, ayrim tovarlarda aksiz va util yig‘imi ko‘riladi.\n\nQaysi tovar haqida gap ketayotganini yozing."
        )
    return ""

def ai_followup_answer(state: Dict[str, Any], lang: str) -> str:
    topic = state.get("topic", "")
    product = state.get("product", "").strip()
    country = state.get("country", "").strip()
    purpose = state.get("purpose", "").strip()

    goods_type = classify_goods_type(product)
    is_food = goods_type == "food"
    is_medicine = goods_type == "medicine"
    is_phone = goods_type == "phone"
    is_auto = goods_type == "auto"

    if not product:
        return ai_base_topic_answer(topic, lang)

    if topic == "import_docs":
        base = (
            f"По товару «{product}» для импорта обычно смотрят:\n"
            "• контракт\n• инвойс\n• упаковочный лист\n• транспортные документы\n"
            if lang == "ru" else
            f"«{product}» bo‘yicha importda odatda quyidagilar ko‘riladi:\n"
            "• kontrakt\n• invoys\n• qadoqlash varaqasi\n• transport hujjatlari\n"
        )
        if is_food:
            base += (
                "• фитосанитарные документы\n• санитарные/карантинные разрешения\n• возможный карантинный контроль\n"
                if lang == "ru" else
                "• fitosanitariya hujjatlari\n• sanitariya/karantin ruxsatlari\n• ehtimoliy karantin nazorati\n"
            )
        elif is_medicine:
            base += (
                "• регистрационные/разрешительные документы по составу\n• при необходимости заключения по медтоварам\n"
                if lang == "ru" else
                "• tarkib bo‘yicha ro‘yxatga olish/ruxsat hujjatlari\n• zarur bo‘lsa medtovar bo‘yicha xulosalar\n"
            )
        elif is_phone:
            base += (
                "• техническое описание товара\n• документы для корректного подбора кода и проверки требований\n"
                if lang == "ru" else
                "• texnik tavsif\n• kodni to‘g‘ri tanlash va talablarni tekshirish uchun hujjatlar\n"
            )
        elif is_auto:
            base += (
                "• техпаспорт/характеристики\n• документы по году, объёму двигателя и происхождению\n"
                if lang == "ru" else
                "• texpasport/xususiyatlar\n• yil, dvigatel hajmi va kelib chiqish bo‘yicha hujjatlar\n"
            )
        else:
            base += (
                "• при необходимости сертификаты и разрешительные документы\n"
                if lang == "ru" else
                "• zarur bo‘lsa sertifikat va ruxsatnomalar\n"
            )
    elif topic == "export_docs":
        base = (
            f"По товару «{product}» для экспорта обычно смотрят:\n"
            "• контракт\n• инвойс\n• упаковочный лист\n• транспортные документы\n• при необходимости разрешительные документы\n"
            if lang == "ru" else
            f"«{product}» bo‘yicha eksportda odatda quyidagilar ko‘riladi:\n"
            "• kontrakt\n• invoys\n• qadoqlash varaqasi\n• transport hujjatlari\n• zarur bo‘lsa ruxsatnomalar\n"
        )
    elif topic == "certs":
        base = (
            f"По товару «{product}» могут понадобиться:\n"
            if lang == "ru" else
            f"«{product}» bo‘yicha quyidagilar kerak bo‘lishi mumkin:\n"
        )
        if is_food:
            base += (
                "• фитосанитарный сертификат\n• санитарно-эпидемиологические документы\n• карантинные разрешения\n"
                if lang == "ru" else
                "• fitosanitariya sertifikati\n• sanitariya-epidemiologik hujjatlar\n• karantin ruxsatnomalari\n"
            )
        elif is_medicine:
            base += (
                "• документы по составу и регистрации\n• разрешительные документы по мед/фарм требованиям\n"
                if lang == "ru" else
                "• tarkib va ro‘yxatdan o‘tish hujjatlari\n• med/farm talablar bo‘yicha ruxsatnomalar\n"
            )
        elif is_phone:
            base += (
                "• документы по соответствию и теххарактеристикам\n• возможные разрешительные требования по категории товара\n"
                if lang == "ru" else
                "• muvofiqlik va texnik xususiyatlar bo‘yicha hujjatlar\n• tovar toifasi bo‘yicha ehtimoliy ruxsat talablari\n"
            )
        else:
            base += (
                "• сертификат соответствия\n• декларация соответствия\n• иные разрешительные документы\n"
                if lang == "ru" else
                "• muvofiqlik sertifikati\n• muvofiqlik deklaratsiyasi\n• boshqa ruxsatnomalar\n"
            )
    elif topic == "tnved":
        base = (
            f"Для товара «{product}» код TN VED нужно подбирать по составу, назначению, форме поставки и характеристикам. Для точного подбора лучше знать описание товара, материал и назначение.\n"
            if lang == "ru" else
            f"«{product}» uchun TN VED kodini tarkib, vazifa, yetkazib berish shakli va xususiyatlarga qarab tanlash kerak. Aniq kod uchun tovar tavsifi, materiali va maqsadini bilish kerak.\n"
        )
    elif topic == "payments":
        base = (
            f"По товару «{product}» таможенные платежи будут зависеть от TN VED кода, таможенной стоимости и страны происхождения. Обычно смотрят пошлину и НДС, а по отдельным товарам — акциз и другие сборы.\n"
            if lang == "ru" else
            f"«{product}» bo‘yicha bojxona to‘lovlari TN VED kodi, bojxona qiymati va kelib chiqish davlatiga bog‘liq bo‘ladi. Odatda boj va QQS, ayrim tovarlarda aksiz va boshqa yig‘imlar ko‘riladi.\n"
        )
    else:
        base = ai_base_topic_answer(topic, lang)

    if country:
        base += (
            f"\nСтрана/направление: {country}. Это важно, потому что требования и льготы могут зависеть от страны отправления или происхождения.\n"
            if lang == "ru" else
            f"\nDavlat/yo‘nalish: {country}. Bu muhim, chunki talablar va imtiyozlar jo‘natish yoki kelib chiqish davlatiga bog‘liq bo‘lishi mumkin.\n"
        )

    if purpose:
        base += (
            f"\nЦель: {purpose}. Для коммерческого ввоза требования обычно строже, чем для личного пользования.\n"
            if lang == "ru" else
            f"\nMaqsad: {purpose}. Tijorat importida talablar odatda shaxsiy foydalanishga qaraganda qat’iyroq bo‘ladi.\n"
        )

    if not country:
        base += (
            "\nНапишите страну отправления или происхождения, и я уточню дальше."
            if lang == "ru" else
            "\nJo‘natish yoki kelib chiqish davlatini yozing, men javobni yanada aniqlashtiraman."
        )
    elif not purpose:
        base += (
            "\nТеперь напишите цель: для продажи или для собственного использования."
            if lang == "ru" else
            "\nEndi maqsadni yozing: sotish uchunmi yoki shaxsiy foydalanish uchunmi."
        )
    else:
        base += (
            "\nЕсли хотите, следующим сообщением я могу подсказать, какие именно разрешения или документы стоит проверить в первую очередь."
            if lang == "ru" else
            "\nXohlasangiz, keyingi xabarda aynan qaysi ruxsatnoma yoki hujjatlarni birinchi bo‘lib tekshirish kerakligini yozib beraman."
        )

    return base


# ===== PHYSICAL PRO MAX OVERRIDES =====
PHYSICAL_TYPO_MAP = {
    "ru": {
        "аеропорт": "аэропорт",
        "самалет": "самолет",
        "самалёт": "самолет",
        "улитаю": "улетаю",
        "ссобой": "с собой",
        "лекраство": "лекарство",
        "лекраства": "лекарства",
        "золато": "золото",
        "дубаи": "дубай",
        "ципочка": "цепочка",
        "кулан": "кулон",
    },
    "uz": {
        "aerport": "aeroport",
        "samalet": "samolyot",
    }
}


def normalize_physical_human_text(text: str, lang: str) -> str:
    q = normalize_text(text)
    words = q.split()
    mapping = PHYSICAL_TYPO_MAP.get(lang, {})
    words = [mapping.get(w, w) for w in words]
    q = " ".join(words)
    q = q.replace(" ё", " е")
    return q.strip()


def physical_detect_direction(text: str, lang: str) -> str:
    q = normalize_physical_human_text(text, lang)
    export_markers = [
        "улетаю", "лечу", "вылетаю", "беру с собой", "с собой", "вывезти", "вывоз", "увезти",
        "olib chiq", "olib ket", "uchyapman", "uchaman"
    ]
    import_markers = [
        "ввезти", "ввоз", "привезти", "завезти", "везу в узбекистан", "возвращаюсь в узбекистан",
        "olib kir", "olib kel", "kirit"
    ]
    if any(x in q for x in export_markers):
        return "export"
    if any(x in q for x in import_markers):
        return "import"
    return ""


def physical_detect_transport(text: str, lang: str) -> str:
    q = normalize_physical_human_text(text, lang)
    if any(x in q for x in ["аэропорт", "самолет", "самолёт", "рейс", "улетаю", "лечу", "вылетаю", "aeroport", "samolyot", "uchyapman", "uchaman"]):
        return "air"
    if any(x in q for x in ["машина", "авто", "автомобиль", "на машине", "mashina", "avto"]):
        return "car"
    if any(x in q for x in ["пешком", "пешеход", "piyoda"]):
        return "foot"
    if any(x in q for x in ["поезд", "жд", "железнодорож", "poyezd", "temir yo"]):
        return "rail"
    if any(x in q for x in ["река", "речной", "daryo"]):
        return "river"
    if any(x in q for x in ["курьер", "доставка", "kuryer"]):
        return "courier"
    if any(x in q for x in ["почта", "посылка", "pochta", "posilka"]):
        return "mail"
    return ""


def physical_import_limit_by_transport(transport: str) -> int:
    return {
        "air": 1000,
        "rail": 500,
        "river": 500,
        "car": 300,
        "foot": 300,
        "courier": 200,
        "mail": 100,
    }.get(transport, 0)


def physical_detect_topic_plus(text: str, lang: str) -> str:
    q = normalize_physical_human_text(text, lang)
    if any(x in q for x in ["лекар", "dori", "tablet", "таблет", "цитрамон", "sitramon", "парацетамол", "анальгин", "ибупрофен", "retsept", "рецепт"]):
        return "medicine"
    if any(x in q for x in ["телефон", "айфон", "iphone", "смартфон", "telefon", "phone"]):
        return "phones"
    if any(x in q for x in ["ноутбук", "noutbuk", "laptop"]):
        return "notebook"
    if any(x in q for x in ["телевизор", "tv", "smart tv", "смарт тв", "televizor"]):
        return "tv"
    if any(x in q for x in ["валют", "valyuta", "доллар", "usd", "евро", "eur", "наличн", "деньги", "sum", "сум"]):
        return "currency"
    if any(x in q for x in ["пиротех", "салют", "petard", "pirotex", "фейерверк"]):
        return "pyro"
    if any(x in q for x in ["дрон", "квадрокоптер", "беспилот", "dron"]):
        return "drone"
    if any(x in q for x in ["золото", "цепочка", "кулон", "кольцо", "серьги", "браслет", "ювелир", "украш", "tilla", "uzuk", "zirak", "zanjir"]):
        return "jewelry"
    if any(x in q for x in ["сигарет", "сигар", "табак", "алкогол", "пиво", "вино", "водка", "коньяк", "sigaret", "alkogol", "tamaki"]):
        return "tobacco_alcohol"
    if any(x in q for x in ["машин", "авто", "автомобил", "mashina", "avto"]):
        return "auto"
    if any(x in q for x in ["что нельзя", "запрещ", "можно дрон", "можно оруж", "mumkin emas", "taqiq"]):
        return "forbidden"
    direction = physical_detect_direction(text, lang)
    if direction:
        return direction
    return ""


def physical_looks_commercial(text: str, lang: str) -> bool:
    q = normalize_physical_human_text(text, lang)
    markers = [
        "для продажи", "на продажу", "коммер", "оптом", "партия", "контейнер", "для магазина", "для бизнеса",
        "broker", "брокер", "юрлиц", "юридичес", "контракт", "invoice", "invoys", "tn ved", "тн вэд",
        "sertifikat", "сертификат соответствия", "gtd", "гтд", "код тн вэд", "stavka",
        "sotish uchun", "tijorat", "ulgurji", "biznes uchun", "yuridik shaxs"
    ]
    return any(m in q for m in markers)


def physical_best_faq_item(text: str, lang: str) -> Dict[str, Any]:
    q = normalize_physical_human_text(text, lang)
    topic = physical_detect_topic_plus(text, lang)
    direction = physical_detect_direction(text, lang)
    transport = physical_detect_transport(text, lang)
    best = {}
    best_score = 0
    for item in PHYSICAL_FAQ_PRO.get(lang, {}).get("faq_items", []):
        score = 0
        item_topic = str(item.get("topic", ""))
        for p in item.get("patterns", []):
            pn = normalize_physical_human_text(str(p), lang)
            if not pn:
                continue
            if pn in q:
                score += 10
            else:
                # token match for noisy human text
                for token in [w for w in pn.split() if len(w) >= 4]:
                    if token in q:
                        score += 2
        if topic and item_topic == topic:
            score += 7
        if topic == "jewelry" and item_topic == "jewelry" and direction == "export":
            score += 5
        if direction == "export" and any(x in q for x in ["улетаю", "лечу", "с собой", "вывезти"]):
            if item_topic in {"jewelry", "currency", "export", "forbidden", "drone", "pyro"}:
                score += 3
        if direction == "import" and any(x in q for x in ["ввезти", "привезти", "завезти"]):
            if item_topic in {"phones", "medicine", "tobacco_alcohol", "perfume", "jewelry", "import"}:
                score += 3
        if transport == "air" and any(x in q for x in ["улетаю", "лечу", "аэропорт", "самолет"]):
            score += 1
        if score > best_score and item.get("answer"):
            best = item
            best_score = score
    if best:
        best = dict(best)
        best["_score"] = best_score
    return best


def physical_pro_guess_topic(text: str) -> str:
    # override old simple topic guess
    return physical_detect_topic_plus(text, "ru") or physical_detect_topic_plus(text, "uz")


def physical_pro_pattern_answer(text: str, lang: str) -> str:
    q = normalize_physical_human_text(text, lang)
    direction = physical_detect_direction(text, lang)
    transport = physical_detect_transport(text, lang)
    topic = physical_detect_topic_plus(text, lang)

    if physical_looks_commercial(text, lang):
        return physical_redirect_text(lang)

    # broad human intent: "I'm flying to Dubai" => airport export
    if direction == "export" and transport == "air" and not topic:
        return (
            "Если вы улетаете, значит речь идет о выезде через аэропорт. Напишите, пожалуйста, что именно хотите взять с собой: валюту, золото, лекарства, телефон или другой товар."
            if lang == "ru" else
            "Agar uchayotgan bo‘lsangiz, demak gap aeroport orqali olib chiqish haqida ketmoqda. O‘zingiz bilan nima olib ketmoqchi ekaningizni yozing: valyuta, tilla, dori, telefon yoki boshqa tovar."
        )

    best = physical_best_faq_item(text, lang)
    if best and best.get("_score", 0) >= 10:
        answer = best.get("answer", "").strip()
        follow = best.get("follow_up", "").strip()
        if direction == "import" and transport:
            limit = physical_import_limit_by_transport(transport)
            if limit:
                if lang == "ru":
                    answer += f"\n\nПо вашему сообщению это похоже на въезд через {('аэропорт' if transport=='air' else 'автодорожный пункт' if transport=='car' else 'пешеходный пункт' if transport=='foot' else 'ж/д пункт' if transport=='rail' else 'речной пункт' if transport=='river' else 'курьер' if transport=='courier' else 'международную почту')}. Базовый лимит для физлица здесь — до {limit} долларов США."
                else:
                    answer += f"\n\nXabaringizga ko‘ra bu kirish usuli uchun asosiy limit — {limit} AQSh dollarigacha."
        if follow:
            answer += "\n\n" + follow
        return answer

    # contextual direct answers
    if topic == "phones":
        amount = 0.0
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*(\$|доллар|доллара|долларов|usd)", q)
        if m:
            try:
                amount = float(m.group(1).replace(',', '.'))
            except Exception:
                amount = 0.0
        if direction == "import" and transport:
            limit = physical_import_limit_by_transport(transport)
            if amount and limit and amount > limit:
                excess = round(amount - limit, 2)
                return (
                    f"По вашему вопросу это похоже на ввоз телефона для личного пользования через {('аэропорт' if transport=='air' else 'границу')}. Стоимость: {amount:.2f}$. Лимит: {limit}$. Превышение: {excess:.2f}$. На превышение применяется единый таможенный платеж: 30% от таможенной стоимости части превышения, но не менее 3 долларов США за каждый килограмм этой части."
                    if lang == "ru" else
                    f"Bu shaxsiy foydalanish uchun telefon olib kirishga o‘xshaydi. Qiymati: {amount:.2f}$. Limit: {limit}$. Oshgan qismi: {excess:.2f}$. Oshgan qismga 30% yagona bojxona to‘lovi qo‘llanadi, lekin har kilogramm uchun kamida 3$ bo‘lishi kerak."
                )
        return (
            "Телефон для физлица рассматривается как товар для личного пользования. Важны способ въезда, стоимость, вес и признаки некоммерческого характера. Напишите, как именно вы пересекаете границу, сколько стоит телефон и его примерный вес."
            if lang == "ru" else
            "Telefon jismoniy shaxs uchun shaxsiy foydalanish tovari sifatida ko‘riladi. Kirish usuli, qiymati, vazni va tijorat alomatlari yo‘qligi muhim. Qanday kirayotganingizni, telefon narxi va taxminiy vaznini yozing."
        )

    if topic == "jewelry":
        if direction == "export" and transport == "air":
            return (
                "Если вы улетаете через аэропорт и речь о золоте, цепочке, кулоне, кольце или другом украшении, то для физлица обычно важны не только граммы, а характер вещи: это личное украшение или партия товара. Если это одна личная вещь и не выглядит как коммерция, ситуация обычно проще. Напишите, пожалуйста: это одно личное украшение или несколько изделий?"
                if lang == "ru" else
                "Agar aeroport orqali uchayotgan bo‘lsangiz va gap tilla, zanjir, kulon, uzuk yoki boshqa taqinchoq haqida bo‘lsa, jismoniy shaxs uchun faqat gramm emas, balki buyumning xarakteri ham muhim: bu shaxsiy taqinchoqmi yoki tovar partiyasimi. Agar bu bitta shaxsiy buyum bo‘lsa va tijoratga o‘xshamasa, vaziyat odatda osonroq bo‘ladi."
            )
        return (
            "Готовые ювелирные изделия для личного пользования оцениваются как обычный товар: важны стоимость, количество и признаки некоммерческого характера. Если изделий немного и это выглядит как вещи для себя или семьи, вопрос обычно рассматривается как личное пользование."
            if lang == "ru" else
            "Tayyor zargarlik buyumlari shaxsiy foydalanish uchun odatiy tovar sifatida baholanadi. Bunda qiymat, soni va tijorat alomatlari yo‘qligi muhim."
        )

    if topic == "medicine":
        return (
            "Для личного пользования без медицинских документов обычно допускается до 10 разных лекарств и не более 5 упаковок каждого. Для наркотических и психотропных веществ правила строже. Напишите название лекарства и количество упаковок — я скажу точнее."
            if lang == "ru" else
            "Shaxsiy foydalanish uchun tibbiy hujjatlarsiz odatda 10 xil dori va har biridan 5 qadoqqacha olib kirish mumkin. Narkotik va psixotrop moddalar uchun qoidalar qat’iyroq. Dori nomi va qadoq sonini yozing."
        )

    if topic == "currency":
        return (
            "Ввоз наличной валюты в Узбекистан для физлиц не ограничен по сумме. Вывоз наличной валюты разрешён в сумме не более эквивалента 100 000 000 сумов. Напишите валюту и сумму — я скажу точнее."
            if lang == "ru" else
            "Naqd valyutani O‘zbekistonga olib kirish jismoniy shaxslar uchun cheklanmagan. Olib chiqish esa 100 000 000 so‘m ekvivalentigacha ruxsat etiladi. Valyuta turi va summani yozing."
        )

    if topic == "tobacco_alcohol":
        return (
            "Для личного пользования допускается ввоз: алкогольной продукции — до 2 литров, сигарет — до 200 штук, сигар — до 5 штук, табака — до 100 граммов. Эти количественные нормы проверяются вместе с общим лимитом по стоимости."
            if lang == "ru" else
            "Shaxsiy foydalanish uchun alkogol — 2 litrgacha, sigaret — 200 donagacha, sigara — 5 donagacha, tamaki — 100 grammgacha olib kirish mumkin. Bu me’yorlar umumiy qiymat limiti bilan birga tekshiriladi."
        )

    if topic == "pyro":
        return (
            "Пиротехнические изделия нельзя просто так ввозить для личного пользования. Такие товары находятся под строгим контролем и обычно требуют отдельного разрешительного порядка."
            if lang == "ru" else
            "Pirotexnika mahsulotlarini oddiy tartibda olib kirish mumkin emas. Bunday tovarlar qat’iy nazorat ostida bo‘ladi va alohida ruxsat talab qilinadi."
        )

    if topic == "drone":
        return (
            "Ввоз и использование дронов в Узбекистане строго регулируется. Без специального разрешения их ввоз, хранение и использование запрещены, кроме отдельных прямо предусмотренных случаев."
            if lang == "ru" else
            "Dronlarni olib kirish va ulardan foydalanish O‘zbekistonda qat’iy tartibga solinadi. Maxsus ruxsatsiz olib kirish va ishlatish mumkin emas."
        )

    return ""


def physical_pro_global_hint(text: str, lang: str) -> str:
    topic = physical_detect_topic_plus(text, lang)
    rules = PHYSICAL_FAQ_PRO.get(lang, {}).get("global_rules", {})
    if topic == "currency":
        return rules.get("currency_rules", {}).get("answer", "") if isinstance(rules.get("currency_rules"), dict) else rules.get("currency", "")
    if topic == "medicine":
        return rules.get("medicine", "") if isinstance(rules.get("medicine"), str) else ""
    if topic in {"import", "phones", "notebook", "tv", "tobacco_alcohol", "perfume", "jewelry"}:
        rule = rules.get("import_limits", {})
        if isinstance(rule, dict):
            return rule.get("answer", "")
    return ""


def build_physical_ai_prompt(user_text: str, c: Dict[str, Any], lang: str) -> str:
    topic = physical_get_pro_topic(c) or physical_detect_topic_plus(user_text, lang)
    direction = physical_detect_direction(user_text, lang)
    transport = physical_detect_transport(user_text, lang)
    local = []
    patt = physical_pro_pattern_answer(user_text, lang)
    if patt:
        local.append(patt)
    hint = physical_pro_global_hint(user_text, lang)
    if hint and hint not in local:
        local.append(hint)
    if lang == "uz":
        base = (
            "Sen O‘zbekiston bojxona masalalari bo‘yicha faqat jismoniy shaxslar uchun AI yordamchisan. "
            "Faqat shaxsiy foydalanish haqida javob ber. "
            "Agar savol tijorat, TN VED, kontrakt, broker yoki biznes haqida bo‘lsa, yuridik shaxslar bo‘limiga yo‘naltir. "
            "Odamlar oddiy va xato bilan yozishi mumkin, ma’noni to‘g‘ri tushun. "
            "Agar foydalanuvchi 'uchyapman' desa, buni aeroport orqali olib chiqish deb tushun. "
            "Agar 'o‘zim bilan olib ketaman' desa, buni olib chiqish deb tushun. "
            "Javobni qisqa, aniq va foydali yoz."
        )
    else:
        base = (
            "Ты AI-помощник по таможенным вопросам Узбекистана только для физических лиц. "
            "Работаешь только по личному пользованию. "
            "Если вопрос про коммерцию, ТН ВЭД, контракт, брокера или бизнес — мягко отправляй в раздел для юрлиц. "
            "Понимай живую речь и ошибки. "
            "Если пользователь пишет 'улетаю' — считай это выездом через аэропорт. "
            "Если пишет 'беру с собой' — считай это вывозом. "
            "Если пишет 'хочу привезти' — считай это ввозом. "
            "Отвечай коротко, по делу, человеческим языком."
        )
    ctx = f"\n\nTopic: {topic or '-'}\nDirection: {direction or '-'}\nTransport: {transport or '-'}"
    if local:
        ctx += "\n\nLocal context:\n- " + "\n- ".join(local)
    return base + ctx


def physical_answer(text: str, lang: str) -> str:
    ans = physical_pro_pattern_answer(text, lang)
    if ans:
        return ans
    hint = physical_pro_global_hint(text, lang)
    if hint:
        return hint
    return physical_answer_legacy(text, lang)

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

    if button_eq(text, t(lang, "change")):
        reset_mode(uid); c["role"] = None; c["mode"] = "choose_lang"
        await message.answer(t(lang, "choose_lang"), reply_markup=build_lang_kb())
        return

    if button_eq(text, t(lang, "back_menu")):
        c["mode"] = None
        c["category"] = None
        c["group"] = None
        c["pending_form"] = None
        c["form_data"] = {}
        if c.get("role") == "physical":
            await message.answer(t(lang, "physical_intro"), reply_markup=physical_menu(lang))
            return
        await send_main_menu(message, uid)
        return

    if button_eq(text, t(lang, "back")):
        if c["mode"] == "legal_group":
            c["mode"] = "legal_category"
            await message.answer(t(lang, "pick_category"), reply_markup=category_kb(lang))
            return
        if c["mode"] == "legal_item":
            c["mode"] = "legal_group"
            await message.answer(t(lang, "pick_group"), reply_markup=group_kb(lang, c["category"]))
            return
        if c["mode"] in ["physical_ready", "physical_chat", "physical_post_card", "physical_posts_border", "physical_posts_ved", "physical_posts_menu"]:
            c["mode"] = "physical_ai_menu"
            await message.answer(t(lang, "physical_ai_intro"), reply_markup=physical_ai_kb(lang))
            return
        if c["mode"] == "physical_ai_menu":
            c["mode"] = None
            await message.answer(t(lang, "physical_intro"), reply_markup=physical_menu(lang))
            return
        if role == "physical":
            await message.answer(t(lang, "physical_intro"), reply_markup=physical_menu(lang))
            return
        await send_role_menu(message, uid)
        return

    if button_eq(text, t(lang, "specialist")):
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
        # Robust physical menu handling regardless of current mode
        if button_eq(text, t(lang, "physical_ai")):
            reset_mode(uid); c["mode"] = "physical_ai_menu"
            await message.answer(t(lang, "physical_ai_intro"), reply_markup=physical_ai_kb(lang)); return
        if button_eq(text, t(lang, "physical_ready")):
            c["mode"] = "physical_ready"
            await message.answer(t(lang, "physical_ready_intro"), reply_markup=physical_ready_kb(lang)); return
        if button_eq(text, t(lang, "physical_own")):
            c["mode"] = "physical_chat"
            await message.answer(t(lang, "physical_ask_own_intro"), reply_markup=physical_ai_kb(lang)); return
        if button_eq(text, t(lang, "physical_posts")):
            reset_mode(uid); c["mode"] = "physical_posts_menu"
            await message.answer(t(lang, "physical_posts_intro"), reply_markup=physical_posts_menu_kb(lang)); return
        for _ready_key in ["physical_q1", "physical_q2", "physical_q3", "physical_q4", "physical_q5", "physical_q6"]:
            if button_eq(text, t(lang, _ready_key)):
                physical_clear_state(c)
                physical_set_pro_topic(c, physical_pro_guess_topic(text), text)
                c["mode"] = "physical_chat"
                await message.answer(
                    physical_answer(text, lang) + "\n\n" + t(lang, "physical_free_specialist"),
                    reply_markup=physical_ai_kb(lang)
                )
                return

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
        state = ai_state(c)

        faq_topic_map = {
            t(lang, "faq_1"): "import_docs",
            t(lang, "faq_2"): "export_docs",
            t(lang, "faq_3"): "certs",
            t(lang, "faq_4"): "tnved",
            t(lang, "faq_5"): "payments",
        }
        if text in faq_topic_map:
            topic = faq_topic_map[text]
            ai_set_state(c, topic, lang)
            await message.answer(ai_base_topic_answer(topic, lang) + "\n\n" + t(lang, "free_specialist"), reply_markup=legal_ai_kb(lang))
            return

        if text in [t(lang, "faq_6"), t(lang, "ask_own")]:
            ai_clear_state(c)
            await message.answer("Напишите свой вопрос." if lang == "ru" else "Savolingizni yozing.", reply_markup=legal_ai_kb(lang))
            return

        # follow-up mode: product -> country -> purpose
        if state.get("topic"):
            if not state.get("product") and text.strip():
                if looks_like_new_question(text) and looks_like_customs_question(text):
                    ai_clear_state(c)
                else:
                    state["product"] = text.strip()
                    state["awaiting"] = "country"
                    await message.answer(ai_followup_answer(state, lang) + "\n\n" + t(lang, "free_specialist"), reply_markup=legal_ai_kb(lang))
                    return

            elif state.get("product") and not state.get("country"):
                country_val = detect_country_value(text)
                if country_val:
                    state["country"] = country_val
                    state["awaiting"] = "purpose"
                    await message.answer(ai_followup_answer(state, lang) + "\n\n" + t(lang, "free_specialist"), reply_markup=legal_ai_kb(lang))
                    return
                if not looks_like_customs_question(text):
                    state["country"] = text.strip()
                    state["awaiting"] = "purpose"
                    await message.answer(ai_followup_answer(state, lang) + "\n\n" + t(lang, "free_specialist"), reply_markup=legal_ai_kb(lang))
                    return

            elif state.get("product") and state.get("country") and not state.get("purpose"):
                purpose_val = detect_purpose_value(text) or text.strip()
                if purpose_val:
                    state["purpose"] = purpose_val
                    await message.answer(ai_followup_answer(state, lang) + "\n\n" + t(lang, "free_specialist"), reply_markup=legal_ai_kb(lang))
                    return

        topic = ai_topic_from_text(text, lang)
        if topic:
            ai_set_state(c, topic, lang)
            await message.answer(ai_base_topic_answer(topic, lang) + "\n\n" + t(lang, "free_specialist"), reply_markup=legal_ai_kb(lang))
            return

        if is_personal_use_question(text) and looks_like_physical_customs_question(text) and not is_legal_commercial_question(text):
            await message.answer(
                "Это больше вопрос для раздела физлиц. Перейдите в раздел для физических лиц и напишите товар, количество и как именно пересекаете границу."
                if lang == "ru" else
                "Bu ko‘proq jismoniy shaxslar bo‘limi uchun savol. Jismoniy shaxslar bo‘limiga o‘ting va tovar, miqdor hamda chegarani qanday kesib o‘tayotganingizni yozing.",
                reply_markup=legal_ai_kb(lang)
            )
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
            ai_clear_state(c)
            await send_safe_message(message, out, reply_markup=legal_ai_kb(lang))
            return

        if client:
            try:
                system_prompt = (
                    "Ты — сильный таможенный AI-консультант по Узбекистану. "
                    "Отвечай жёстко, коротко и по делу. Без воды. Без расплывчатых формулировок. "
                    "Работай только по темам таможни, импорта, экспорта, документов, сертификации, TN VED, ставок и платежей. "
                    "Если данных мало, не рассуждай — сразу требуй конкретику: товар, страна, цель ввоза. "
                    "Если пользователь отвечает коротко одним словом, воспринимай это как уточнение предыдущего таможенного вопроса. "
                    "Если вопрос не по теме — отвечай: Я отвечаю только по таможенным вопросам."
                    if lang == "ru" else
                    "Sen O‘zbekiston bo‘yicha kuchli bojxona AI-konsultantsan. "
                    "Javobni qat’iy, qisqa va aniq ber. Ortiqcha gap yozma. "
                    "Faqat bojxona, import, eksport, hujjatlar, sertifikatlash, TN VED, stavkalar va to‘lovlar mavzusida javob ber. "
                    "Ma’lumot yetarli bo‘lmasa, taxmin qilma — darrov aniqlik talab qil: tovar, davlat, olib kirish maqsadi. "
                    "Agar foydalanuvchi bir-ikki so‘z bilan javob bersa, buni oldingi bojxona savoliga aniqlashtirish deb tushun. "
                    "Agar savol mavzudan tashqarida bo‘lsa, javob ber: Men faqat bojxona savollariga javob beraman."
                )
                user_prompt = text
                resp = client.responses.create(
                    model=OPENAI_MODEL,
                    input=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ]
                )
                ai_clear_state(c)
                await message.answer(((resp.output_text or '').strip() or t(lang, 'nothing_found')) + "\n\n" + t(lang, "free_specialist"), reply_markup=legal_ai_kb(lang))
            except Exception:
                await message.answer(t(lang, "nothing_found"), reply_markup=legal_ai_kb(lang))
            return

        await message.answer(t(lang, "nothing_found"), reply_markup=legal_ai_kb(lang))
        return

    if c["mode"] == "physical_ai_menu":
        if button_eq(text, t(lang, "physical_ready")):
            c["mode"] = "physical_ready"
            await message.answer(t(lang, "physical_ready_intro"), reply_markup=physical_ready_kb(lang))
            return
        if button_eq(text, t(lang, "physical_own")):
            c["mode"] = "physical_chat"
            await message.answer(t(lang, "physical_ask_own_intro"), reply_markup=physical_ai_kb(lang))
            return
        await message.answer(t(lang, "physical_ai_intro"), reply_markup=physical_ai_kb(lang))
        return

    if c["mode"] == "physical_ready":
        ready_answer = PHYSICAL_FAQ.get(lang, {}).get(text)
        if not ready_answer:
            for k, v in PHYSICAL_FAQ.get(lang, {}).items():
                if button_eq(text, k):
                    ready_answer = v
                    break
        if ready_answer:
            physical_clear_state(c)
            physical_set_pro_topic(c, physical_pro_guess_topic(text), text)
            c["mode"] = "physical_chat"
            await message.answer(
                ready_answer + "\n\n" + t(lang, "physical_free_specialist"),
                reply_markup=physical_ai_kb(lang)
            )
            return

        if physical_needs_ai_followup(text, c, lang):
            ai_text = physical_ai_answer(text, c, lang)
            if ai_text:
                c["mode"] = "physical_chat"
                await send_safe_message(
                    message,
                    ai_text + "\n\n" + t(lang, "physical_free_specialist"),
                    reply_markup=physical_ai_kb(lang)
                )
                return

        await message.answer(t(lang, "physical_ready_intro"), reply_markup=physical_ready_kb(lang))
        return

    if c["mode"] == "physical_posts_menu":
        if button_eq(text, t(lang, "physical_posts_border")):
            c["mode"] = "physical_posts_border"
            await send_safe_message(message, posts_list_text(lang, "border"), reply_markup=physical_posts_menu_kb(lang))
            return
        if button_eq(text, t(lang, "physical_posts_ved")):
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
        if button_eq(text, t(lang, "physical_location")):
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
        state = physical_get_state(c)
        faq_map = PHYSICAL_FAQ.get(lang, {})
        ready_answer = faq_map.get(text)
        if not ready_answer:
            for k, v in faq_map.items():
                if button_eq(text, k):
                    ready_answer = v
                    break

        if ready_answer:
            physical_clear_state(c)
            physical_set_pro_topic(c, physical_pro_guess_topic(text), text)
            await send_safe_message(
                message,
                ready_answer + "\n\n" + t(lang, "physical_free_specialist"),
                reply_markup=physical_ai_kb(lang)
            )
            return

        pattern_answer = physical_pro_pattern_answer(text, lang)
        if pattern_answer:
            physical_clear_state(c)
            physical_set_pro_topic(c, physical_pro_guess_topic(text), text)
            await send_safe_message(
                message,
                pattern_answer + "\n\n" + t(lang, "physical_free_specialist"),
                reply_markup=physical_ai_kb(lang)
            )
            return

        global_hint = physical_pro_global_hint(text, lang)
        if global_hint:
            physical_clear_state(c)
            physical_set_pro_topic(c, physical_pro_guess_topic(text), text)
            await send_safe_message(
                message,
                global_hint + "\n\n" + t(lang, "physical_free_specialist"),
                reply_markup=physical_ai_kb(lang)
            )
            return

        if physical_needs_ai_followup(text, c, lang):
            ai_text = physical_ai_answer(text, c, lang)
            if ai_text:
                physical_clear_state(c)
                await send_safe_message(
                    message,
                    ai_text + "\n\n" + t(lang, "physical_free_specialist"),
                    reply_markup=physical_ai_kb(lang)
                )
                return

        # legacy structured follow-up оставляем только как резерв
        if state.get("topic"):
            if is_physical_rate_question(text):
                physical_clear_state(c)
                await message.answer(
                    physical_redirect_text(lang),
                    reply_markup=physical_ai_kb(lang)
                )
                return

            if not looks_like_new_question(text):
                if not state.get("product"):
                    state["product"] = text.strip()
                    state["awaiting"] = "quantity"
                elif not state.get("quantity") and physical_has_quantity(text):
                    state["quantity"] = text.strip()
                    state["awaiting"] = "country"
                elif not state.get("country") and physical_has_country(text):
                    state["country"] = text.strip()
                    state["awaiting"] = "done"

                await message.answer(
                    physical_followup_answer(state.get("topic", ""), text.strip(), lang, state) + "\n\n" + t(lang, "physical_free_specialist"),
                    reply_markup=physical_ai_kb(lang)
                )
                return

            physical_clear_state(c)

        user_q = normalize_text(text)

        commercial_markers = [
            "контейнер", "оптом", "партия", "для продажи", "коммерческ",
            "юрлиц", "гтд", "брокер", "контракт", "инвойс", "сертификат соответствия",
            "ulgurji", "sotish uchun", "partiya", "broker", "gtd", "kontrakt", "invoice"
        ]
        if any(marker in user_q for marker in commercial_markers):
            physical_clear_state(c)
            physical_clear_pro_state(c)
            await message.answer(
                "Я помощник только для физических лиц. По коммерческому импорту перейдите в раздел для юридических лиц."
                if lang == "ru"
                else "Men faqat jismoniy shaxslar uchun yordamchiman. Tijorat importi bo‘yicha yuridik shaxslar bo‘limiga o‘ting.",
                reply_markup=physical_ai_kb(lang)
            )
            return

        if is_physical_rate_question(text) and not physical_get_pro_topic(c):
            physical_clear_state(c)
            physical_clear_pro_state(c)
            await message.answer(
                physical_redirect_text(lang),
                reply_markup=physical_ai_kb(lang)
            )
            return

        if not looks_like_customs_question(text):
            if looks_like_physical_customs_question(text) or physical_pro_guess_topic(text):
                physical_clear_state(c)
                physical_set_pro_topic(c, physical_pro_guess_topic(text), text)
                await message.answer(physical_answer(text, lang), reply_markup=physical_ai_kb(lang))
                return
            await message.answer(
                t(lang, "physical_only_customs") if "physical_only_customs" in TXT.get(lang, {}) else t(lang, "only_customs"),
                reply_markup=physical_ai_kb(lang)
            )
            return

        physical_clear_state(c)
        physical_set_pro_topic(c, physical_pro_guess_topic(text), text)
        await message.answer(physical_answer(text, lang), reply_markup=physical_ai_kb(lang))
        return

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


# ============================================================
# ADDITIVE PATCH: v5 document-routed physical answers
# Only physical-person logic is upgraded.
# ============================================================
def _load_physical_doc_router_v5() -> Dict[str, Any]:
    path = os.path.join(BASE_DIR, "physical_faq_document_router_v5_forbidden.json")
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                obj = json.load(f)
                if isinstance(obj, dict):
                    return obj
    except Exception:
        logging.exception("Failed to load physical_faq_document_router_v5_forbidden.json")
    return {}

PHYSICAL_DOC_ROUTER_V5 = _load_physical_doc_router_v5()

def _v5_norm(s: str) -> str:
    s = normalize_text(s or "")
    s = s.replace("ʻ", "'").replace("ʼ", "'").replace("`", "'").replace("’", "'").replace("‘", "'")
    return s

def _v5_detect_transport(text: str) -> str:
    q = _v5_norm(text)
    if any(x in q for x in ["аэропорт", "aeroport", "airport", "самолет", "samolyot", "улетаю", "uchyapman", "uchaman"]):
        return "air"
    if any(x in q for x in ["машина", "mashina", "avto", "авто", "на машине", "пешком", "piyoda", "пешеход", "chegara"]):
        return "car_foot"
    if any(x in q for x in ["поезд", "poyezd", "temir yo", "жд", "daryo", "речной"]):
        return "rail_river"
    if any(x in q for x in ["курьер", "kuryer"]):
        return "courier"
    if any(x in q for x in ["почта", "pochta", "посылка", "posilka"]):
        return "post"
    return ""

def _v5_parse_usd_amount(text: str) -> float:
    q = _v5_norm(text)
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(\$|usd|доллар|dollar)", q)
    if not m:
        return 0.0
    try:
        return float(m.group(1).replace(",", "."))
    except Exception:
        return 0.0

def _v5_match_named_item(text: str, block: Dict[str, Any]) -> str:
    q = _v5_norm(text)
    for item_key, item in block.get("items", {}).items():
        names = list(item.get("names_ru", [])) + list(item.get("names_uz", []))
        if any(_v5_norm(n) in q for n in names):
            return item_key
    return ""

def physical_base_from_documents_v5(text: str, lang: str) -> str:
    router = PHYSICAL_DOC_ROUTER_V5
    if not router:
        return ""
    q = _v5_norm(text)
    transport = _v5_detect_transport(text)
    amount = _v5_parse_usd_amount(text)

    electronics = router.get("knowledge", {}).get("electronics", {})
    item_key = _v5_match_named_item(text, electronics)
    if item_key:
        item = electronics.get("items", {}).get(item_key, {})
        item_answer = item.get("base_answer_ru" if lang == "ru" else "base_answer_uz", "")
        template = electronics.get("answer_template_ru" if lang == "ru" else "answer_template_uz", "{item_answer}")
        answer = template.replace("{item_answer}", item_answer).strip()
        limits = router.get("general_rules", {}).get("import_limits_usd", {})
        limit_value = limits.get(transport, 0) if transport else 0
        if amount and limit_value and amount > limit_value:
            excess = round(amount - limit_value, 2)
            duty_text = router.get("general_rules", {}).get("duty_rule", {}).get(lang, "")
            if lang == "ru":
                answer += f"\n\nВ вашем случае лимит по посту — {limit_value}$. Стоимость товара: {amount}$. Превышение: {excess}$.\n{duty_text}"
            else:
                answer += f"\n\nSizning holatingizda post bo'yicha limit — {limit_value}$. Tovar narxi: {amount}$. Oshgan qismi: {excess}$.\n{duty_text}"
        elif amount and limit_value and amount <= limit_value:
            if lang == "ru":
                answer += f"\n\nВ вашем случае лимит по посту — {limit_value}$. Стоимость товара: {amount}$. Это укладывается в лимит."
            else:
                answer += f"\n\nSizning holatingizda post bo'yicha limit — {limit_value}$. Tovar narxi: {amount}$. Bu limit ichida."
        return answer

    medicine = router.get("knowledge", {}).get("medicine", {})
    med_rules = medicine.get("base_rules", {})
    if any(x in q for x in ["лекар", "лекарства", "таблет", "dori", "dorilar", "tabletka"]):
        for drug in medicine.get("common_drugs", {}).values():
            names = list(drug.get("names_ru", [])) + list(drug.get("names_uz", []))
            if any(_v5_norm(n) in q for n in names):
                ans = drug.get("answer_ru" if lang == "ru" else "answer_uz", "")
                extra = med_rules.get("followup_ru" if lang == "ru" else "followup_uz", "")
                return f"{ans} {extra}".strip()
        if any(x in q for x in ["наркот", "психотроп", "narkotik", "psixotrop"]):
            ans = med_rules.get("forbidden_ru" if lang == "ru" else "forbidden_uz", "")
            extra = med_rules.get("followup_ru" if lang == "ru" else "followup_uz", "")
            return f"{ans} {extra}".strip()
        ans = med_rules.get("basic_limit_ru" if lang == "ru" else "basic_limit_uz", "")
        extra = med_rules.get("followup_ru" if lang == "ru" else "followup_uz", "")
        return f"{ans} {extra}".strip()

    currency = router.get("knowledge", {}).get("currency", {})
    cur_rules = currency.get("base_rules", {})
    if any(x in q for x in ["валют", "доллар", "евро", "налич", "деньги", "valyuta", "dollar", "yevro", "evro", "naqd", "pul"]):
        if any(x in q for x in ["вывоз", "вывез", "с собой", "улетаю", "olib chiq", "olib ket", "uchyapman", "uchaman"]):
            ans = cur_rules.get("export_ru" if lang == "ru" else "export_uz", "")
        else:
            ans = cur_rules.get("import_ru" if lang == "ru" else "import_uz", "")
        if any(ch.isdigit() for ch in q):
            extra = cur_rules.get("declaration_ru" if lang == "ru" else "declaration_uz", "")
            ans = f"{ans} {extra}".strip()
        return ans

    jewelry = router.get("knowledge", {}).get("jewelry", {})
    j_key = _v5_match_named_item(text, jewelry)
    if j_key:
        item = jewelry.get("items", {}).get(j_key, {})
        base = item.get("answer_ru" if lang == "ru" else "answer_uz", "")
        template = jewelry.get("answer_template_ru" if lang == "ru" else "answer_template_uz", "{base_answer}")
        return template.replace("{base_answer}", base).strip()
    if any(x in q for x in ["золото", "ювелир", "tilla", "zargarlik"]):
        if any(x in q for x in ["вывоз", "olib chiq", "olib ket", "улетаю", "uchyapman", "uchaman"]):
            return jewelry.get("base_rules", {}).get("export_limit_ru" if lang == "ru" else "export_limit_uz", "")
        if any(x in q for x in ["ввоз", "olib kir", "olib kel", "привез", "завез"]):
            return jewelry.get("base_rules", {}).get("import_limit_ru" if lang == "ru" else "import_limit_uz", "")
        return jewelry.get("base_rules", {}).get("general_ru" if lang == "ru" else "general_uz", "")

    forbidden = router.get("knowledge", {}).get("forbidden", {})
    f_key = _v5_match_named_item(text, forbidden)
    if f_key:
        item = forbidden.get("items", {}).get(f_key, {})
        base = item.get("answer_ru" if lang == "ru" else "answer_uz", "")
        template = forbidden.get("answer_template_ru" if lang == "ru" else "answer_template_uz", "{base_answer}")
        return template.replace("{base_answer}", base).strip()
    if any(x in q for x in ["что запрещено", "что нельзя", "zapret", "taqiql", "qaysi tovarlar taqiqlangan", "nima taqiqlangan"]):
        return forbidden.get("base_rules", {}).get("general_ru" if lang == "ru" else "general_uz", "")
    return ""

_physical_pro_pattern_answer_old_v5 = physical_pro_pattern_answer
def physical_pro_pattern_answer(text: str, lang: str) -> str:
    base = physical_base_from_documents_v5(text, lang)
    if base:
        return base
    return _physical_pro_pattern_answer_old_v5(text, lang)

_physical_answer_old_v5 = physical_answer
def physical_answer(text: str, lang: str) -> str:
    base = physical_base_from_documents_v5(text, lang)
    if base:
        return base
    return _physical_answer_old_v5(text, lang)


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
@dp.message_handler(content_types=["text"])
async def universal_handler(message: types.Message):
    text = message.text.lower()

    # 🟢 ВСЕГДА отвечаем на кнопки (даже если сломался mode)
    if "tayyor" in text:
        await message.answer("📋 Tayyor savollar ishlamoqda")
        return

    if "savolingiz" in text or "savol" in text:
        await message.answer("✍ Savolingizni yozing, men javob beraman")
        return

    if "orqaga" in text:
        await message.answer("⬅️ Orqaga qaytdingiz")
        return

    if "asosiy" in text:
        await message.answer("🏠 Asosiy menyu")
        return

    # 🔥 ФИЗЛИЦА — ОСНОВА
    answer = search_physical_faq(message.text, "ru")

    if answer:
        await message.answer(answer)
        return

    # 🤖 fallback AI (если есть)
    await message.answer("Savolingizni tushundim. Batafsil yozing: tovar, narx, yo‘l.")
