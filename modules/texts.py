from typing import Dict

def apply_text_patches(TXT: Dict[str, Dict[str, str]]) -> None:
    extra = {
        "ru": {
            "admin_apps": "📥 Заявки",
            "admin_apps_back": "⬅️ Назад в админку",
            "admin_apps_new": "🆕 Только новые",
            "admin_apps_specialist": "👨‍💼 Специалист",
            "admin_apps_broker": "💼 Broker PRO",
            "admin_apps_logistics": "🚚 Логистика",
            "admin_apps_all": "📋 Все заявки",
            "admin_apps_empty": "Заявки пока отсутствуют.",
            "client_status_accepted": "✅ Ваша заявка принята. Специалист уже увидел её.",
            "client_status_in_work": "🛠 Ваша заявка в работе.",
            "client_status_closed": "✅ Ваша заявка закрыта. Если нужно, можете отправить новый запрос.",
            "status_new": "Новая",
            "status_accepted": "Принята",
            "status_in_work": "В работе",
            "status_closed": "Закрыта",
        },
        "uz": {
            "admin_apps": "📥 Arizalar",
            "admin_apps_back": "⬅️ Admin panelga qaytish",
            "admin_apps_new": "🆕 Faqat yangi",
            "admin_apps_specialist": "👨‍💼 Mutaxassis",
            "admin_apps_broker": "💼 Broker PRO",
            "admin_apps_logistics": "🚚 Logistika",
            "admin_apps_all": "📋 Barcha arizalar",
            "admin_apps_empty": "Hozircha arizalar yo‘q.",
            "client_status_accepted": "✅ Arizangiz qabul qilindi. Mutaxassis uni ko‘rdi.",
            "client_status_in_work": "🛠 Arizangiz ish jarayonida.",
            "client_status_closed": "✅ Arizangiz yopildi. Kerak bo‘lsa, yangi so‘rov yuborishingiz mumkin.",
            "status_new": "Yangi",
            "status_accepted": "Qabul qilindi",
            "status_in_work": "Jarayonda",
            "status_closed": "Yopildi",
        },
    }
    for lang, values in extra.items():
        TXT.setdefault(lang, {}).update(values)

def t(TXT: Dict[str, Dict[str, str]], lang: str, key: str) -> str:
    return TXT.get(lang, TXT["ru"]).get(key, key)

def get_lang(ctx: dict) -> str:
    return ctx.get("lang", "ru")
