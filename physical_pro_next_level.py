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
            "айфон": "iphone",
            "айфона": "iphone",
            "самсунг": "samsung",
            "сколка": "сколько",
            "скока": "сколько",
            "ввозит": "ввозить",
            "вывозит": "вывозить",
            "лекарство": "лекарства",
            "лекарства": "лекарства",
            "валюта": "валюты",
            "аверо": "аэропорт",
            "самалет": "аэропорт",
            "самолет": "аэропорт",
            "духи": "парфюм",
            "парфюмерия": "парфюм",
            "таблетка": "лекарства",
            "таблетки": "лекарства",
            "машина": "авто",
            "автомобиль": "авто",
            "тачка": "авто",
            "bojsiz": "без пошлины",
            "qancha": "сколько",
            "olib kirish": "ввозить",
            "olib chiqish": "вывозить",
            "valyuta": "валюты",
            "dori": "лекарства",
            "telefon": "телефон",
            "tayyor savollar": "готовые вопросы",
        }
        # Priority matters: more specific topics must be checked first.
        self.topic_keywords = [
            ("medicine", ["лекарства", "препарат", "таблет", "анальгин", "ибупрофен", "цитрамон", "психотроп", "наркот"]),
            ("electronics", ["телефон", "iphone", "samsung", "смартфон", "телевизор", "ноутбук", "планшет", "техника"]),
            ("vehicle", ["авто", "машина", "автомобиль", "иномарка", "номера", "временный ввоз", "временный вывоз"]),
            ("jewelry", ["ювелир", "золото", "кольцо", "цепочка", "серьги", "браслет"]),
            ("food", ["рис", "мясо", "сахар", "масло", "хлеб", "фрукты", "овощи", "продукты"]),
            ("alcohol_tobacco", ["алкоголь", "вино", "водка", "пиво", "сигареты", "табак", "сигары", "парфюм"]),
            ("prohibited", ["запрещ", "оруж", "дрон", "квадрокоптер", "пиротех", "петарда", "фейерверк"]),
            ("liability", ["штраф", "ответственность", "накажут", "конфискация", "уголов", "административ"]),
            ("currency", ["валюты", "доллар", "usd", "наличные", "евро", "сум"]),
            ("limits", ["без пошлины", "лимит", "норма", "превышении нормы", "превышение"]),
        ]

    def _load_faq(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {"items": []}
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def normalize_text(self, text: str) -> str:
        t = (text or "").lower().strip()
        t = t.replace("ё", "е")
        # preserve dollars and slash for formulas
        t = re.sub(r"[^\w\s$€₽.,:/-]", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        for src, dst in self.synonyms.items():
            t = re.sub(rf"\b{re.escape(src)}\b", dst, t)
        return t

    def detect_topic(self, text: str) -> Optional[str]:
        t = self.normalize_text(text)
        # explicit ready questions first
        if "сколько можно вывозить валюты" in t or ("валюты" in t and "вывоз" in t):
            return "currency"
        if "сколько можно ввозить без пошлины" in t or "без пошлины" in t:
            return "limits"
        if "что будет при превышении нормы" in t or "превыш" in t:
            return "limits"
        for topic, keywords in self.topic_keywords:
            if any(k in t for k in keywords):
                return topic
        return None

    def set_topic(self, user_id: int, topic: str, text: str) -> None:
        ctx = self.user_ctx.setdefault(user_id, {})
        ctx["topic"] = topic
        ctx["last_text"] = text

    def get_topic(self, user_id: int) -> Optional[str]:
        return self.user_ctx.get(user_id, {}).get("topic")

    def format_answer(self, answer: str, source: Optional[str] = None, extra: Optional[str] = None) -> str:
        parts = [f"📌 {answer.strip()}"]
        if source:
            parts.append(f"\n📖 Основание: {source.strip()}")
        if extra:
            parts.append(f"\nℹ️ {extra.strip()}")
        return "\n".join(parts)

    def _find_faq_match(self, text: str, topic: Optional[str] = None) -> Optional[Dict[str, Any]]:
        items: List[Dict[str, Any]] = self.data.get("items", [])
        best = None
        best_score = 0
        for item in items:
            score = 0
            patterns = item.get("patterns", []) + item.get("keywords", [])
            item_topic = item.get("topic")
            # only mild preference for topic; never let stale topic dominate
            if topic and item_topic == topic:
                score += 2
            for p in patterns:
                p_norm = self.normalize_text(p)
                if not p_norm:
                    continue
                if p_norm == text:
                    score += 12
                elif p_norm in text:
                    score += max(4, len(p_norm.split()))
                elif all(word in text for word in p_norm.split() if len(word) > 2):
                    score += 2
            if score > best_score:
                best_score = score
                best = item
        return best if best_score >= 4 else None

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
        elif "границ" in text or "пеш" in text or "авто" in text:
            mode = "border"
        elif "поезд" in text or "жд" in text or "желез" in text or "река" in text:
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

    def calculate_duty(self, text: str, topic: Optional[str]) -> Optional[str]:
        # Only calculate when question is clearly about goods/tech, not currency.
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
            mode_label = {
                "airport": "аэропорт",
                "rail_river": "ж/д или речной транспорт",
                "border": "граница",
                "courier": "курьер",
                "post": "почта",
            }[mode]
            return self.format_answer(
                f"Стоимость {money:.0f}$ укладывается в лимит для режима «{mode_label}». Пошлина не начисляется.",
                "Постановление КМ РУз №244 от 19.04.2025",
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

    def _topic_fallback_answer(self, topic: str) -> Optional[str]:
        fallback = {
            "electronics": self.format_answer(
                "Через аэропорт можно ввезти до 2 телефонов за один въезд. Общий лимит беспошлинного ввоза — 1000 долларов. Через сухопутную границу лимит — 300 долларов. При превышении применяется единый таможенный платеж: 30% от превышения, но не менее 3 долларов за кг.",
                "Постановление КМ РУз №463 от 22.06.2018, Постановление КМ РУз №244 от 19.04.2025, ПҚ-4508 от 07.11.2019",
            ),
            "medicine": self.format_answer(
                "Для личного пользования обычно допускается до 10 разных лекарств и не более 5 упаковок каждого. Для наркотических, психотропных препаратов и прекурсоров действует отдельный порядок и могут требоваться специальные документы.",
                "Постановление КМ РУз №191 от 08.06.2016",
                "Напишите точное название препарата — специалист проверит состав и ответит точно.",
            ),
            "currency": self.format_answer(
                "Вывоз наличной валюты разрешён в сумме не более эквивалента 100 000 000 сумов. Ввоз наличной валюты не ограничен.",
                "Положение №66 от 30.01.2018",
            ),
            "limits": self.format_answer(
                "Лимит беспошлинного ввоза зависит от способа ввоза: аэропорт — 1000$, ж/д и речные пункты — 500$, авто и пешком — 300$, курьер — 200$, почта — 100$. При превышении применяется 30% от стоимости, но не менее 3$ за кг.",
                "Постановление КМ РУз №244 от 19.04.2025, ПҚ-4508 от 07.11.2019",
            ),
        }
        return fallback.get(topic)

    def find_answer(self, user_id: int, text: str) -> Optional[str]:
        normalized = self.normalize_text(text)

        # 1) Always try to understand the NEW question first.
        new_topic = self.detect_topic(normalized)

        # 2) Direct calculator only after fresh topic detection.
        duty_answer = self.calculate_duty(normalized, new_topic)
        if duty_answer:
            self.set_topic(user_id, new_topic or "electronics", normalized)
            return duty_answer

        # 3) FAQ search using the NEW topic, not stale memory.
        if new_topic:
            matched = self._find_faq_match(normalized, new_topic)
            self.set_topic(user_id, new_topic, normalized)
            if matched:
                answer = matched.get("answer") or matched.get("title")
                source = matched.get("law") or matched.get("source") or matched.get("basis")
                follow = matched.get("follow_up")
                return self.format_answer(answer, source, follow)
            fallback = self._topic_fallback_answer(new_topic)
            if fallback:
                return fallback

        # 4) If NEW topic was not found, try exact FAQ by text without memory bias.
        matched_any = self._find_faq_match(normalized, None)
        if matched_any:
            answer = matched_any.get("answer") or matched_any.get("title")
            source = matched_any.get("law") or matched_any.get("source") or matched_any.get("basis")
            follow = matched_any.get("follow_up")
            item_topic = matched_any.get("topic")
            if item_topic:
                self.set_topic(user_id, item_topic, normalized)
            return self.format_answer(answer, source, follow)

        # 5) Only now use remembered topic as follow-up.
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
