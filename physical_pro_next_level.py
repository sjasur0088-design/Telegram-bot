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
            "айфон": "iphone",
            "айфона": "iphone",
            "iphone": "iphone",
            "самсунг": "samsung",
            "сколка": "сколько",
            "скока": "сколько",
            "ввозит": "ввозить",
            "вывозит": "вывозить",
            "лекарство": "лекарства",
            "таблетка": "лекарства",
            "таблетки": "лекарства",
            "цитрамон": "цитрамон",
            "анальгин": "анальгин",
            "ибупрофен": "ибупрофен",
            "парацетамол": "парацетамол",
            "аверо": "аэропорт",
            "самалет": "аэропорт",
            "самолет": "аэропорт",
            "машина": "авто",
            "автомобиль": "авто",
            "тачка": "авто",
            "доларов": "доллар",
            "долар": "доллар",
        }
        self.topic_keywords = [
            ("electronics", ["телефон", "iphone", "samsung", "смартфон", "телевизор", "ноутбук", "планшет", "техника"]),
            ("medicine", ["лекарства", "препарат", "таблет", "цитрамон", "анальгин", "ибупрофен", "парацетамол", "психотроп", "наркот"]),
            ("vehicle", ["авто", "иномарка", "номера", "машин", "транспортн"]),
            ("jewelry", ["ювелир", "золото", "кольцо", "цепочка", "серьги", "браслет"]),
            ("food", ["рис", "мясо", "сахар", "масло", "хлеб", "фрукты", "овощи", "продукты"]),
            ("alcohol_tobacco", ["алкоголь", "вино", "водка", "пиво", "сигареты", "табак", "сигары", "парфюм", "духи"]),
            ("prohibited", ["запрещ", "оруж", "дрон", "квадрокоптер", "пиротех", "петарда", "фейерверк"]),
            ("liability", ["штраф", "ответственность", "накажут", "конфискация", "уголов", "административ"]),
            ("currency", ["валюта", "доллар", "usd", "наличные", "евро", "сум"]),
        ]

    def _load_faq(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {"items": []}
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def normalize_text(self, text: str) -> str:
        t = (text or "").lower().strip()
        t = t.replace("ё", "е")
        t = re.sub(r"[^\w\s$€₽.,/-]", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        for src, dst in self.synonyms.items():
            t = re.sub(rf"\b{re.escape(src)}\b", dst, t)
        return t

    def _ctx(self, user_id: int) -> Dict[str, Any]:
        return self.user_ctx.setdefault(user_id, {})

    def set_topic(self, user_id: int, topic: str, text: str) -> None:
        ctx = self._ctx(user_id)
        ctx["topic"] = topic
        ctx["last_text"] = text

    def get_topic(self, user_id: int) -> Optional[str]:
        return self._ctx(user_id).get("topic")

    def format_answer(self, answer: str, source: Optional[str] = None, extra: Optional[str] = None) -> str:
        parts = [f"📌 {answer.strip()}"]
        if source:
            parts.append(f"\n📖 Основание: {source.strip()}")
        if extra:
            parts.append(f"\nℹ️ {extra.strip()}")
        return "\n".join(parts)

    def _looks_like_followup(self, text: str) -> bool:
        short = len(text.split()) <= 5
        has_number = bool(re.search(r"\d", text))
        return short or has_number or any(x in text for x in ["аэропорт", "граница", "поезд", "кг", "$", "доллар", "упаков", "шт"])

    def detect_topic(self, user_id: int, text: str) -> Optional[str]:
        remembered = self.get_topic(user_id)
        if remembered in {"electronics", "medicine", "vehicle", "currency", "jewelry"} and self._looks_like_followup(text):
            if remembered == "electronics" and any(k in text for k in ["iphone", "samsung", "телефон", "смартфон", "телевизор", "ноутбук", "аэропорт", "граница", "доллар", "$", "кг"]):
                return "electronics"
            if remembered == "medicine" and any(k in text for k in ["цитрамон", "анальгин", "ибупрофен", "парацетамол", "упаков", "препарат", "лекар"]):
                return "medicine"
            if remembered == "vehicle" and any(k in text for k in ["срок", "90", "дней", "временн", "авто"]):
                return "vehicle"
            if remembered == "currency" and any(k in text for k in ["доллар", "сум", "евро", "ввоз", "вывоз"]):
                return "currency"
            if remembered == "jewelry" and any(k in text for k in ["золото", "кольцо", "цепочка", "серьги"]):
                return "jewelry"
        for topic, keywords in self.topic_keywords:
            if any(k in text for k in keywords):
                return topic
        return remembered if self._looks_like_followup(text) else None

    def _find_faq_match(self, text: str, topic: Optional[str]) -> Optional[Dict[str, Any]]:
        items: List[Dict[str, Any]] = self.data.get("items", [])
        best = None
        best_score = 0
        for item in items:
            score = 0
            patterns = item.get("patterns", []) + item.get("keywords", [])
            item_topic = item.get("topic")
            if topic and item_topic == topic:
                score += 3
            for p in patterns:
                p_norm = self.normalize_text(p)
                if not p_norm:
                    continue
                if p_norm == text:
                    score += 10
                elif p_norm in text:
                    score += max(4, len(p_norm.split()))
            if score > best_score:
                best_score = score
                best = item
        return best if best_score > 0 else None

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
        elif "граница" in text or "пеш" in text or "авто" in text:
            mode = "border"
        elif "поезд" in text or "жд" in text or "желез" in text or "река" in text:
            mode = "rail_river"
        elif "курьер" in text:
            mode = "courier"
        elif "почта" in text or "посылка" in text:
            mode = "post"
        return money, weight, mode

    def _duty_limit(self, mode: Optional[str]) -> Optional[float]:
        return {"airport": 1000.0, "rail_river": 500.0, "border": 300.0, "courier": 200.0, "post": 100.0}.get(mode)

    def calculate_duty(self, text: str) -> Optional[str]:
        money, weight, mode = self._parse_money_weight(text)
        if money is None or mode is None:
            return None
        limit = self._duty_limit(mode)
        if limit is None:
            return None
        over = max(0.0, money - limit)
        mode_label = {"airport": "аэропорт", "rail_river": "ж/д или речной транспорт", "border": "граница", "courier": "курьер", "post": "почта"}[mode]
        if over <= 0:
            return self.format_answer(
                f"Стоимость {money:.0f}$ укладывается в лимит для режима «{mode_label}». Пошлина не начисляется.",
                "Постановление КМ РУз №244 от 19.04.2025"
            )
        duty_30 = over * 0.30
        duty_min = (weight * 3.0) if weight is not None else None
        if duty_min is not None:
            final_duty = max(duty_30, duty_min)
            calc = f"Сверх лимита: {over:.0f}$. 30% = {duty_30:.2f}$. Минимум по весу: {duty_min:.2f}$."
        else:
            final_duty = duty_30
            calc = f"Сверх лимита: {over:.0f}$. 30% = {duty_30:.2f}$. Для расчёта минимума по весу нужен вес в кг."
        return self.format_answer(
            f"Ориентировочная пошлина: {final_duty:.2f}$.",
            "ПҚ-4508 от 07.11.2019 и Постановление КМ РУз №244 от 19.04.2025",
            calc,
        )

    def _direct_electronics_answer(self, text: str) -> Optional[str]:
        is_phone = any(k in text for k in ["телефон", "iphone", "samsung", "смартфон"])
        money, weight, mode = self._parse_money_weight(text)
        if is_phone and ("сколько" in text or "можно" in text) and money is None:
            return self.format_answer(
                "Через аэропорт можно ввезти до 2 телефонов за один въезд. Общий лимит беспошлинного ввоза — 1000 долларов. Через сухопутную границу лимит — 300 долларов. При превышении применяется единый таможенный платеж: 30% от превышения, но не менее 3 долларов за кг.",
                "Постановление КМ РУз №463 от 22.06.2018, Постановление КМ РУз №244 от 19.04.2025, ПҚ-4508 от 07.11.2019"
            )
        if is_phone and money is not None:
            airport_over = max(0.0, money - 1000.0)
            border_over = max(0.0, money - 300.0)
            extra = "Если напишете вес в кг и как именно везёте, я посчитаю точную пошлину."
            if mode:
                duty = self.calculate_duty(text)
                if duty:
                    return self.format_answer(
                        f"Для телефона стоимостью {money:.0f}$ лимит зависит от способа въезда. Через аэропорт лимит — 1000$, через границу — 300$.",
                        "Постановление КМ РУз №244 от 19.04.2025, ПҚ-4508 от 07.11.2019",
                        f"Через аэропорт превышение: {airport_over:.0f}$. Через границу превышение: {border_over:.0f}$."
                    ) + "\n\n" + duty
            return self.format_answer(
                f"Для телефона стоимостью {money:.0f}$ через аэропорт лимит — 1000$, превышение — {airport_over:.0f}$. Через сухопутную границу лимит — 300$, превышение — {border_over:.0f}$.",
                "Постановление КМ РУз №244 от 19.04.2025, ПҚ-4508 от 07.11.2019",
                extra
            )
        if any(k in text for k in ["телевизор", "ноутбук", "планшет", "техника"]):
            return self.format_answer(
                "По технике для личного пользования лимит зависит от способа въезда: аэропорт — 1000$, ж/д и речной транспорт — 500$, граница — 300$. При превышении применяется 30% от превышения, но не менее 3$ за кг.",
                "Постановление КМ РУз №244 от 19.04.2025, ПҚ-4508 от 07.11.2019"
            )
        return None

    def _direct_medicine_answer(self, text: str) -> Optional[str]:
        if any(k in text for k in ["цитрамон", "анальгин", "ибупрофен", "парацетамол"]):
            packs_match = re.search(r"(\d+)\s*(упаков|пачк|шт)", text)
            packs = int(packs_match.group(1)) if packs_match else None
            if packs is not None and packs <= 5:
                return self.format_answer(
                    f"Для личного пользования {packs} упаковок укладываются в общую норму: до 10 видов лекарств и до 5 упаковок каждого. Если препарат содержит наркотические или психотропные вещества, действует отдельный порядок.",
                    "Постановление КМ РУз №191 от 08.06.2016",
                    "Если хотите точную проверку по составу, напишите полное название препарата — специалист проверит и ответит точно."
                )
            return self.format_answer(
                "Для личного пользования обычно допускается до 10 видов лекарств и до 5 упаковок каждого. Для наркотических, психотропных препаратов и прекурсоров действует отдельный порядок: могут требоваться специальные документы и декларация.",
                "Постановление КМ РУз №191 от 08.06.2016",
                "Напишите полное название препарата и количество упаковок — я скажу точнее."
            )
        if "лекарства" in text and ("можно" in text or "сколько" in text):
            return self.format_answer(
                "Для личного пользования обычно допускается до 10 разных лекарств и не более 5 упаковок каждого. Для наркотических, психотропных препаратов и прекурсоров действует отдельный порядок: могут требоваться специальные документы и декларация.",
                "Постановление КМ РУз №191 от 08.06.2016"
            )
        return None

    def _direct_currency_answer(self, text: str) -> Optional[str]:
        if "сколько" in text and "валюта" in text and "вывоз" in text:
            return self.format_answer("Вывоз наличной валюты разрешён до эквивалента 100 000 000 сум. Свыше действует отдельный порядок.", "Положение №66 от 30.01.2018")
        if ("сколько" in text and "валюта" in text and "ввоз" in text) or text in {"валюта", "доллар"}:
            return self.format_answer("Ввоз наличной валюты не ограничен. При необходимости можно заполнить декларацию, таможня подтвердит с печатью.", "Положение №66 от 30.01.2018")
        return None

    def _direct_by_topic(self, topic: Optional[str], text: str) -> Optional[str]:
        if topic == "electronics":
            return self._direct_electronics_answer(text)
        if topic == "medicine":
            return self._direct_medicine_answer(text)
        if topic == "currency":
            return self._direct_currency_answer(text)
        return None

    def find_answer(self, user_id: int, text: str) -> Optional[str]:
        normalized = self.normalize_text(text)
        topic = self.detect_topic(user_id, normalized)
        if topic:
            self.set_topic(user_id, topic, normalized)

        direct = self._direct_by_topic(topic, normalized)
        if direct:
            return direct

        if topic == "electronics":
            duty_answer = self.calculate_duty(normalized)
            if duty_answer:
                return duty_answer

        matched = self._find_faq_match(normalized, topic)
        if matched:
            answer = matched.get("answer") or matched.get("title")
            source = matched.get("law") or matched.get("source") or matched.get("basis")
            follow = matched.get("follow_up")
            return self.format_answer(answer, source, follow)

        remembered = self.get_topic(user_id)
        if remembered:
            extra_map = {
                "electronics": ("Похоже, это уточнение по технике. Напишите стоимость в долларах, вес в кг и как везёте: аэропорт / граница / поезд.", "Постановление КМ РУз №244 от 19.04.2025, ПҚ-4508 от 07.11.2019"),
                "medicine": ("Похоже, это уточнение по лекарствам. Напишите точное название препарата — специалист проверит состав и скажет точно.", "Постановление КМ РУз №191 от 08.06.2016"),
                "currency": ("Похоже, это уточнение по валюте. Напишите сумму и направление: ввоз или вывоз.", "Положение №66 от 30.01.2018"),
                "vehicle": ("Похоже, это уточнение по авто. Напишите: временный ввоз или вывоз, чьё авто и на какой срок.", "Таможенный кодекс РУз, статьи 62 и 159"),
            }
            if remembered in extra_map:
                answer, source = extra_map[remembered]
                return self.format_answer(answer, source)
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
