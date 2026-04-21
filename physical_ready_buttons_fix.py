# -*- coding: utf-8 -*-
"""
Patch for physical ready-question buttons in legacy_bot.py

How to use in legacy_bot.py:

1) Add import:
from physical_ready_buttons_fix import (
    PHYSICAL_READY_RU,
    PHYSICAL_READY_UZ,
    is_physical_ready_button,
    handle_physical_ready_button,
)

2) Inside role == "physical" block, BEFORE old ready-question handling, add:

    handled = await handle_physical_ready_button(
        message=message,
        user_id=uid,
        text=text,
        lang=lang,
        answer_func=find_physical_answer_v2,
        reply_markup=physical_ready_kb(lang),
    )
    if handled:
        return

This patch does not touch other sections.
"""

from typing import Awaitable, Callable, Dict, Optional, Sequence, Union

try:
    from aiogram import types
except Exception:  # pragma: no cover
    types = None


PHYSICAL_READY_RU: Dict[str, str] = {
    "Таможенные правила для физлиц": "Таможенные правила для физлиц",
    "Сколько можно ввозить без пошлины": "Сколько можно ввозить без пошлины",
    "Сколько телефонов можно привезти": "Сколько телефонов можно привезти",
    "Можно ли ввозить лекарства": "Можно ли ввозить лекарства",
    "Сколько можно вывозить валюты": "Сколько можно вывозить валюты",
    "Что будет при превышении нормы": "Что будет при превышении нормы",
}

PHYSICAL_READY_UZ: Dict[str, str] = {
    "Jismoniy shaxslar uchun bojxona qoidalari": "Jismoniy shaxslar uchun bojxona qoidalari",
    "Bojsiz qancha olib kirish mumkin": "Bojsiz qancha olib kirish mumkin",
    "Nechta telefon olib kirish mumkin": "Nechta telefon olib kirish mumkin",
    "Dori olib kirish mumkinmi": "Dori olib kirish mumkinmi",
    "Qancha valyuta olib chiqish mumkin": "Qancha valyuta olib chiqish mumkin",
    "Norma oshsa nima bo‘ladi": "Norma oshsa nima bo‘ladi",
    "Norma oshsa nima bo'ladi": "Norma oshsa nima bo'ladi",
}

_PHYSICAL_READY_ALL = {**PHYSICAL_READY_RU, **PHYSICAL_READY_UZ}


def is_physical_ready_button(text: str) -> bool:
    return (text or "").strip() in _PHYSICAL_READY_ALL


async def handle_physical_ready_button(
    message: "types.Message",
    user_id: int,
    text: str,
    lang: str,
    answer_func: Callable[[int, str], Optional[str]],
    reply_markup=None,
) -> bool:
    """
    Converts ready-question button text into a real customs question and sends the answer.

    Returns True if the text was handled as a ready-question button.
    """
    text = (text or "").strip()
    if text not in _PHYSICAL_READY_ALL:
        return False

    normalized_question = _PHYSICAL_READY_ALL[text]
    answer = answer_func(user_id, normalized_question)

    if answer:
        await message.answer(answer, reply_markup=reply_markup)
    else:
        fallback = (
            "Не удалось найти готовый ответ. Напишите вопрос подробнее."
            if (lang or "ru") == "ru"
            else "Tayyor javob topilmadi. Savolni batafsilroq yozing."
        )
        await message.answer(fallback, reply_markup=reply_markup)

    return True
