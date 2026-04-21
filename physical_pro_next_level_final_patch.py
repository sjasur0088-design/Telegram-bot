import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
except Exception:
    ReplyKeyboardMarkup = None
    KeyboardButton = None

BASE_DIR = Path(__file__).resolve().parent
FAQ_PATH = BASE_DIR / "physical_faq_pro_max.json"


class PhysicalProEngine:
    def __init__(self, faq_path: Optional[str] = None):
        self.faq_path = Path(faq_path) if faq_path else FAQ_PATH
        self.data = self._load_faq(self.faq_path)
        self.user_ctx: Dict[int, Dict[str, Any]] = {}
        self.synonyms = {
            "телфон": "телефон",
            "телефн": "телефон",
            "телик": "телевизор",
            "тв": "телевизор",
            "айфон": "iphone",
            "айфона": "iphone",
            "самсунг": "samsung",
            "сколка": "сколько",
            "скока": "сколько",
            "ввозит": "ввозить",
            "вывозит": "вывозить",
            "лекарство": "лекарства",
            "валюта": "валюты",
            "самалет": "аэропорт",
            "самолет": "аэропорт",
            "аверо": "аэропорт",
            "машина": "авто",
            "автомобиль": "авто",
            "тачка": "авто",
            "сигара": "сигары",
            "сигар": "сигары",
            "парфюмерия": "парфюм",
            "таблетка": "таблетки",
            "таблетки": "лекарства",
            # uz
            "bojsiz": "без пошлины",
            "qancha": "сколько",
            "olib kirish": "ввозить",
            "olib chiqish": "вывозить",
            "valyuta": "валюты",
            "dori": "лекарства",
            "telefon": "телефон",
            "tayyor savollar": "готовые вопросы",
            "tayyor savol": "готовые вопросы",
            "tovarlar": "товары",
            "taqiqlangan": "запрещенные",
            "ro'yxat": "регистрация",
            "royxat": "регистрация",
            "registratsiya": "регистрация",
            "qozog'iston": "казахстан",
            "qozogiston": "казахстан",
            "qozoq": "казахстан",
            "alkogol": "алкоголь",
            "tamaki": "табак",
            "sigaret": "сигареты",
            "sigara": "сигары",
        }
        self.tech_items = {
            "телевизор": "Телевизор — 1 штука, 1 раз в 6 календарных месяцев через авто/ж.д./речные пункты.",
            "холодильник": "Холодильник — 1 штука, 1 раз в 6 календарных месяцев через авто/ж.д./речные пункты.",
            "морозильник": "Морозильник — 1 штука, 1 раз в 6 календарных месяцев через авто/ж.д./речные пункты.",
            "кондиционер": "Кондиционер — 1 штука, 1 раз в 6 календарных месяцев через авто/ж.д./речные пункты.",
            "стиральн": "Стиральная машина — 1 штука, 1 раз в 6 календарных месяцев через авто/ж.д./речные пункты.",
            "пылесос": "Пылесос — 1 штука, 1 раз в 6 календарных месяцев через авто/ж.д./речные пункты.",
            "газовая плита": "Газовая плита — 1 штука, 1 раз в 6 календарных месяцев через авто/ж.д./речные пункты.",
            "электрическая плита": "Электрическая плита — 1 штука, 1 раз в 6 календарных месяцев через авто/ж.д./речные пункты.",
            "микроволнов": "Микроволновая печь — 1 штука, 1 раз в 6 календарных месяцев через авто/ж.д./речные пункты.",
            "мясоруб": "Электромясорубка — 1 штука, 1 раз в 6 календарных месяцев через авто/ж.д./речные пункты.",
            "утюг": "Утюг — 1 штука, 1 раз в 6 календарных месяцев через авто/ж.д./речные пункты.",
            "фен": "Фен — 1 штука, 1 раз в 6 календарных месяцев через авто/ж.д./речные пункты.",
            "кухонный комбайн": "Кухонный комбайн — 1 штука, 1 раз в 6 календарных месяцев через авто/ж.д./речные пункты.",
            "принтер": "Принтер или МФУ — 1 штука, 1 раз в 6 календарных месяцев через авто/ж.д./речные пункты.",
            "планшет": "Планшет — 1 штука, 1 раз в 6 календарных месяцев через авто/ж.д./речные пункты.",
            "ноутбук": "Ноутбук — 1 штука, 1 раз в 6 календарных месяцев через авто/ж.д./речные пункты.",
            "компьютер": "Компьютерная техника — 1 штука, 1 раз в 6 календарных месяцев через авто/ж.д./речные пункты.",
        }

    def _load_faq(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {"items": []}
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"items": []}

    def normalize_text(self, text: str) -> str:
        t = (text or "").lower().strip().replace("ё", "е")
        t = re.sub(r"[^\w\s$€₽.,:/\-]", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        for src, dst in self.synonyms.items():
            t = re.sub(rf"\b{re.escape(src)}\b", dst, t)
        return t

    def set_ctx(self, user_id: int, topic: str, text: str) -> None:
        self.user_ctx[user_id] = {"topic": topic, "last_text": text}

    def get_ctx_topic(self, user_id: int) -> Optional[str]:
        return self.user_ctx.get(user_id, {}).get("topic")

    def format_answer(self, answer: str, source: Optional[str] = None, extra: Optional[str] = None) -> str:
        parts = [f"📌 {answer.strip()}"]
        if source:
            parts.append(f"\n📖 Основание: {source.strip()}")
        if extra:
            parts.append(f"\nℹ️ {extra.strip()}")
        return "\n".join(parts)

    def _parse_money_weight(self, text: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        money = None
        weight = None
        mode = None
        m = re.search(r"(\d+[\d\s.,]*)\s*(\$|usd|доллар)", text)
        if m:
            money = float(m.group(1).replace(" ", "").replace(",", "."))
        m2 = re.search(r"(\d+[\d\s.,]*)\s*(кг|килограмм)", text)
        if m2:
            weight = float(m2.group(1).replace(" ", "").replace(",", "."))
        if "аэропорт" in text:
            mode = "airport"
        elif "границ" in text or "пеш" in text or re.search(r"\bавто\b", text):
            mode = "border"
        elif "поезд" in text or "жд" in text or "желез" in text or "речн" in text:
            mode = "rail_river"
        elif "курьер" in text:
            mode = "courier"
        elif "почта" in text or "посылка" in text:
            mode = "post"
        return money, weight, mode

    def _duty_limit(self, mode: Optional[str]) -> Optional[float]:
        return {
            "airport": 1000.0,
            "rail_river": 500.0,
            "border": 300.0,
            "courier": 200.0,
            "post": 100.0,
        }.get(mode)

    def detect_topic(self, text: str) -> Optional[str]:
        t = self.normalize_text(text)

        # system / ready
        if "таможенные правила для физлиц" in t or "написать свой вопрос" in t:
            return "system_intro"

        # registration / migration
        if "регистрац" in t or "казахстан" in t or "гостиниц" in t or "на лечении" in t:
            return "migration"

        # prohibited first
        if any(k in t for k in ["какие товары запрещены", "запрещен", "оруж", "дрон", "квадрокоптер", "пиротех", "фейерверк", "петарда"]):
            return "prohibited"

        # strict medicine
        if any(k in t for k in ["психотроп", "наркот", "прекурсор"]):
            return "medicine_strict"

        # named medicine
        if any(k in t for k in ["соннат", "анальгин", "цитрамон", "ибупрофен", "парацетамол"]):
            return "medicine_named"

        # alcohol/tobacco specific before generic memory
        if any(k in t for k in ["сигареты", "сигары", "табак", "алкоголь", "водка", "вино", "пиво", "парфюм"]):
            return "alcohol_tobacco"

        # tech specific item questions
        if any(k in t for k in self.tech_items.keys()) or any(k in t for k in ["телефон", "iphone", "samsung", "смартфон"]):
            return "tech_specific"

        # food
        if any(k in t for k in ["рис", "мясо", "сахар", "масло", "хлеб", "фрукты", "овощи", "продукты"]):
            return "food"

        # currency before generic limits
        if "валют" in t or "доллар" in t or "наличн" in t or "100000000" in t:
            return "currency"

        if "без пошлины" in t or "лимит" in t or "превышени" in t:
            return "limits"

        if any(k in t for k in ["штраф", "ответственность", "конфискац", "контрабанд", "уголов"]):
            return "liability"

        if any(k in t for k in ["авто", "машина", "автомобиль", "временный ввоз", "временный вывоз"]):
            return "vehicle"

        if any(k in t for k in ["ювелир", "золото", "кольцо", "серьги", "браслет", "цепочка"]):
            return "jewelry"

        if "лекарств" in t or "препарат" in t or "таблет" in t:
            return "medicine"

        return None

    def _find_faq_match(self, text: str, topic: Optional[str] = None) -> Optional[Dict[str, Any]]:
        items: List[Dict[str, Any]] = self.data.get("items", [])
        best = None
        best_score = 0
        for item in items:
            score = 0
            if topic and item.get("topic") == topic:
                score += 2
            for p in item.get("patterns", []) + item.get("keywords", []):
                p_norm = self.normalize_text(p)
                if not p_norm:
                    continue
                if p_norm == text:
                    score += 10
                elif p_norm in text:
                    score += 4
            if score > best_score:
                best_score = score
                best = item
        return best if best_score >= 4 else None

    def _topic_fallback(self, topic: str, text: str) -> Optional[str]:
        t = self.normalize_text(text)
        if topic == "system_intro":
            return self.format_answer(
                "Я отвечаю по правилам для физлиц: валюта, лекарства, техника, продукты, алкоголь, запреты, авто и ответственность.",
                "Локальная база physical_faq_pro_max.json",
                "Выберите готовый вопрос или напишите свой вопрос простыми словами.",
            )
        if topic == "migration":
            if "казахстан" in t:
                return self.format_answer(
                    "Гражданин Казахстана может находиться в Узбекистане без регистрации до 10 дней.",
                    "По твоей базе по миграции",
                    "Дольше — при проживании в гостинице или нахождении на лечении.",
                )
            return self.format_answer(
                "По регистрации срок зависит от категории и основания пребывания. Для гражданина Казахстана без регистрации — до 10 дней.",
                "По твоей базе по миграции",
                "Если проживание в гостинице или лечение — действует отдельный порядок.",
            )
        if topic == "medicine":
            return self.format_answer(
                "Для личного пользования обычно допускается до 10 разных лекарств и не более 5 упаковок каждого.",
                "Постановление КМ РУз №191 от 08.06.2016",
                "Для наркотических, психотропных препаратов и прекурсоров действует отдельный порядок.",
            )
        if topic == "medicine_strict":
            return self.format_answer(
                "Если препарат содержит наркотические вещества — ввоз и вывоз допускается только при наличии медицинских документов, и не более чем на 7 суток потребности. Если препарат содержит психотропные вещества — без меддокумента допускается до 5 видов и не более 2 упаковок каждого. Такие препараты нужно указывать в декларации.",
                "Постановление КМ РУз №191 от 08.06.2016 и твоя база по лекарствам",
                "Напишите точное название препарата — специалист проверит состав по перечню и ответит точно.",
            )
        if topic == "medicine_named":
            return self.format_answer(
                "Напишите точное международное или торговое название препарата — специалист проверит, относится ли он к психотропным, наркотическим или обычным лекарствам, и ответит точно.",
                "Постановление КМ РУз №191 от 08.06.2016",
            )
        if topic == "alcohol_tobacco":
            if "сигар" in t and "сигарет" not in t:
                return self.format_answer("Сигары — до 5 штук.", "Постановление КМ РУз №244 от 19.04.2025")
            if "сигарет" in t:
                return self.format_answer("Сигареты — до 200 штук.", "Постановление КМ РУз №244 от 19.04.2025")
            if "табак" in t:
                return self.format_answer("Табак — до 100 грамм.", "Постановление КМ РУз №244 от 19.04.2025")
            if "алког" in t or "водк" in t or "вин" in t or "пиво" in t:
                return self.format_answer("Алкогольные напитки, включая пиво — до 2 литров.", "Постановление КМ РУз №244 от 19.04.2025")
            if "парф" in t:
                return self.format_answer("Парфюмерия — до 3 флаконов, объёмом не более 300 мл каждый.", "Постановление КМ РУз №244 от 19.04.2025")
        if topic == "tech_specific":
            if "телефон" in t or "iphone" in t or "samsung" in t or "смартфон" in t:
                return self.format_answer(
                    "Через аэропорт можно ввезти до 2 телефонов за один въезд. Через авто/ж.д./речные пункты — 1 телефон, 1 раз в 6 календарных месяцев. По стоимости лимит: аэропорт — 1000$, ж/д и речные пункты — 500$, авто/пешком — 300$. При превышении — 30% от превышения, но не менее 3$ за кг.",
                    "Постановление КМ РУз №463 от 22.06.2018, Постановление КМ РУз №244 от 19.04.2025, ПҚ-4508 от 07.11.2019",
                )
            for key, ans in self.tech_items.items():
                if key in t:
                    return self.format_answer(
                        ans + " По стоимости лимит зависит от способа въезда: аэропорт — 1000$, ж/д и речные пункты — 500$, авто/пешком — 300$. При превышении — 30% от превышения, но не менее 3$ за кг.",
                        "Постановление КМ РУз №463 от 22.06.2018, Постановление КМ РУз №244 от 19.04.2025, ПҚ-4508 от 07.11.2019",
                    )
            return self.format_answer(
                "По технике для авто/ж.д./речных пунктов многие позиции идут по 1 штуке, 1 раз в 6 календарных месяцев. По стоимости лимит зависит от способа въезда: аэропорт — 1000$, ж/д и речные пункты — 500$, авто/пешком — 300$.",
                "Постановление КМ РУз №463 от 22.06.2018 и Постановление КМ РУз №244 от 19.04.2025",
            )
        if topic == "food":
            if "рис" in t:
                return self.format_answer("Рис можно вывозить до 3 кг.", "Постановление КМ РУз №244 от 19.04.2025")
            if "сахар" in t:
                return self.format_answer("Сахар можно вывозить до 2 кг.", "Постановление КМ РУз №244 от 19.04.2025")
            if "мяс" in t:
                return self.format_answer("Мясо и мясные продукты можно вывозить до 2 кг.", "Постановление КМ РУз №244 от 19.04.2025")
            return self.format_answer("По продуктам нормы зависят от вида товара. Рис — 3 кг, сахар — 2 кг, мясо — 2 кг, хлебобулочные — 5 кг, масло — 2 кг, фрукты и овощи — 40 кг.", "Постановление КМ РУз №244 от 19.04.2025")
        if topic == "currency":
            if "вывоз" in t or "вывозить" in t or "олиб чиқ" in t or "chiq" in t:
                return self.format_answer("Вывоз наличной валюты разрешён в сумме не более эквивалента 100 000 000 сумов.", "Положение №66 от 30.01.2018")
            return self.format_answer("Ввоз наличной валюты не ограничен. При необходимости можно заполнить декларацию.", "Положение №66 от 30.01.2018")
        if topic == "limits":
            if "превыш" in t:
                return self.format_answer("При превышении лимита применяется единый таможенный платёж: 30% от стоимости, но не менее 3$ за кг.", "ПҚ-4508 от 07.11.2019")
            return self.format_answer("Лимит беспошлинного ввоза: аэропорт — 1000$, ж/д и речные пункты — 500$, авто и пешком — 300$, курьер — 200$, почта — 100$.", "Постановление КМ РУз №244 от 19.04.2025")
        if topic == "prohibited":
            return self.format_answer("К запрещённым или ограниченным товарам относятся, в частности, оружие, боеприпасы, дроны, пиротехника, наркотические и психотропные вещества, отдельные материалы экстремистского и порнографического содержания.", "Закон РУз «Об оружии» №ЎРҚ-550 от 29.07.2019, ПКМ №658 от 15.11.2022, ПФ-5286 от 15.12.2017")
        if topic == "vehicle":
            return self.format_answer("Иностранное транспортное средство для некоммерческих целей обычно может временно находиться на таможенной территории до 90 календарных дней в течение года. По временно ввозимому или вывозимому авто нужен отдельный порядок.", "Таможенный кодекс РУз, статьи 62 и 159")
        if topic == "jewelry":
            return self.format_answer("Готовые ювелирные изделия для личного пользования рассматриваются отдельно, а полуготовые ювелирные изделия без заключения Инспекции вывозить нельзя.", "Постановление КМ РУз №281 от 29.04.2025")
        if topic == "liability":
            return self.format_answer("За нарушение таможенных правил может быть административная или уголовная ответственность: штраф, конфискация, а по тяжёлым случаям — лишение свободы.", "КоАО и УК РУз, твоя база по ответственности")
        return None

    def calculate_duty(self, text: str, topic: Optional[str]) -> Optional[str]:
        if topic == "currency":
            return None
        money, weight, mode = self._parse_money_weight(text)
        if money is None or mode is None:
            return None
        limit = self._duty_limit(mode)
        if limit is None:
            return None
        over = max(0.0, money - limit)
        if over <= 0:
            labels = {"airport": "аэропорт", "rail_river": "ж/д или речной транспорт", "border": "граница", "courier": "курьер", "post": "почта"}
            return self.format_answer(f"Стоимость {money:.0f}$ укладывается в лимит для режима «{labels[mode]}». Пошлина не начисляется.", "Постановление КМ РУз №244 от 19.04.2025")
        duty30 = over * 0.30
        duty_min = (weight * 3.0) if weight is not None else None
        final = max(duty30, duty_min) if duty_min is not None else duty30
        extra = f"Сверх лимита: {over:.0f}$. 30% = {duty30:.2f}$."
        if duty_min is not None:
            extra += f" Минимум по весу: {duty_min:.2f}$."
        else:
            extra += " Для минимума по весу нужен вес в кг."
        return self.format_answer(f"Ориентировочная пошлина: {final:.2f}$.", "ПҚ-4508 от 07.11.2019 и Постановление КМ РУз №244 от 19.04.2025", extra)

    def find_answer(self, user_id: int, text: str) -> Optional[str]:
        normalized = self.normalize_text(text)

        new_topic = self.detect_topic(normalized)

        # explicit FAQ by fresh topic first
        if new_topic:
            duty_answer = self.calculate_duty(normalized, new_topic)
            if duty_answer:
                self.set_ctx(user_id, new_topic, normalized)
                return duty_answer

            matched = self._find_faq_match(normalized, new_topic)
            self.set_ctx(user_id, new_topic, normalized)
            if matched:
                answer = matched.get("answer") or matched.get("title")
                source = matched.get("law") or matched.get("source") or matched.get("basis")
                follow = matched.get("follow_up")
                return self.format_answer(answer, source, follow)

            fb = self._topic_fallback(new_topic, normalized)
            if fb:
                return fb

        # exact FAQ without memory bias
        matched_any = self._find_faq_match(normalized, None)
        if matched_any:
            topic = matched_any.get("topic")
            if topic:
                self.set_ctx(user_id, topic, normalized)
            return self.format_answer(matched_any.get("answer") or matched_any.get("title"), matched_any.get("law") or matched_any.get("source") or matched_any.get("basis"), matched_any.get("follow_up"))

        # controlled follow-up only for short clarifications
        remembered = self.get_ctx_topic(user_id)
        short_follow = len(normalized.split()) <= 4
        if remembered and short_follow:
            # try to extend current topic only for compact follow-ups like "а сахар" / "соннат"
            if remembered in {"food", "medicine", "tech_specific", "alcohol_tobacco", "currency", "migration"}:
                fb = self._topic_fallback(remembered, normalized)
                if fb:
                    return fb

        return None


def get_physical_keyboard():
    if not ReplyKeyboardMarkup or not KeyboardButton:
        return None
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("💰 Валюта"),
        KeyboardButton("💊 Лекарства"),
        KeyboardButton("📱 Техника"),
        KeyboardButton("🚗 Авто"),
        KeyboardButton("🍎 Продукты"),
        KeyboardButton("🚫 Запрещено"),
        KeyboardButton("💎 Ювелирка"),
        KeyboardButton("⚖️ Ответственность"),
    )
    return kb


_engine_singleton: Optional[PhysicalProEngine] = None


def get_engine() -> PhysicalProEngine:
    global _engine_singleton
    if _engine_singleton is None:
        _engine_singleton = PhysicalProEngine()
    return _engine_singleton


def find_physical_answer_v2(user_id: int, user_text: str) -> Optional[str]:
    return get_engine().find_answer(user_id, user_text)
