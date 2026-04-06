from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

STATUS_ORDER = ["new", "accepted", "in_work", "closed"]

def admin_apps_menu_kb(t_func, lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t_func(lang, "admin_apps_new"), t_func(lang, "admin_apps_all"))
    kb.add(t_func(lang, "admin_apps_specialist"), t_func(lang, "admin_apps_broker"))
    kb.add(t_func(lang, "admin_apps_logistics"))
    kb.add(t_func(lang, "admin_apps_back"), t_func(lang, "admin_close"))
    return kb

def admin_app_status_kb(app_id: int, current_status: str = "new"):
    kb = InlineKeyboardMarkup(row_width=2)
    labels = {
        "new": "🆕 New",
        "accepted": "✅ Accepted",
        "in_work": "🛠 In work",
        "closed": "📦 Closed",
    }
    buttons = []
    for status in STATUS_ORDER:
        label = labels[status]
        if status == current_status:
            label = f"• {label}"
        buttons.append(InlineKeyboardButton(label, callback_data=f"appst:{app_id}:{status}"))
    kb.add(*buttons)
    return kb
