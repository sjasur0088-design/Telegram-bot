
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
            "самалет": "аэропорт",
            "самолет": "аэропорт",
            "аверо": "аэропорт",
            "лекарство": "лекарства",
            "таблетка": "лекарства",
            "таблетки": "лекарства",
            "автомобиль": "авто",
            "машина": "авто",
            "тачка": "авто",
            "сколка": "сколько",
            "скока": "сколько",
            "сколька": "сколько",
            "вывозит": "вывозить",
            "ввозит": "ввозить",
            "духи": "парфюм",
            "парфюмерия": "парфюм",
        }

    def _load_faq(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {"items": []}
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def normalize_text(self, text: str) -> str:
        t = (text or "").lower().strip().replace("ё", "е")
        t = re.sub(r"[^\w\s$€₽.,/-]", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        for src, dst in self.synonyms.items():
            t = re.sub(rf"\b{re.escape(src)}\b", dst, t)
        return t

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

    def _topic_score(self, text: str) -> Dict[str, int]:
        scores = {
            "phone": 0,
            "electronics": 0,
            "medicine": 0,
            "currency": 0,
            "food": 0,
            "alcohol_tobacco": 0,
            "prohibited": 0,
            "vehicle": 0,
            "jewelry": 0,
            "liability": 0,
        }
        phone_kw = ["телефон", "iphone", "samsung", "смартфон", "мобильн"]
        electronics_kw = ["телевизор", "ноутбук", "планшет", "холодильник", "техника"]
        medicine_kw = ["лекарства", "препарат", "таблет", "цитрамон", "анальгин", "ибупрофен", "психотроп", "наркот"]
        currency_kw = ["валюта", "наличные", "доллары", "долларов", "евро", "usd", "100000000 сум"]
        food_kw = ["рис", "мясо", "сахар", "масло", "хлеб", "овощ", "фрукт", "продукт"]
        alcohol_kw = ["алкоголь", "вино", "водка", "пиво", "сигарет", "табак", "сигары", "парфюм"]
        prohibited_kw = ["запрещ", "оруж", "дрон", "квадрокоптер", "пиротех", "петарда", "фейерверк"]
        vehicle_kw = ["авто", "машина", "иномарка", "номера", "временный ввоз", "временный вывоз"]
        jewelry_kw = ["ювелир", "кольцо", "цепочка", "серьги", "браслет", "золото"]
        liability_kw = ["штраф", "ответствен", "конфискац", "уголов", "административ"]
        for k in phone_kw:
            if k in text: scores["phone"] += 3
        for k in electronics_kw:
            if k in text: scores["electronics"] += 3
        for k in medicine_kw:
            if k in text: scores["medicine"] += 3
        for k in currency_kw:
            if k in text: scores["currency"] += 2
        for k in food_kw:
            if k in text: scores["food"] += 3
        for k in alcohol_kw:
            if k in text: scores["alcohol_tobacco"] += 3
        for k in prohibited_kw:
            if k in text: scores["prohibited"] += 3
        for k in vehicle_kw:
            if k in text: scores["vehicle"] += 3
        for k in jewelry_kw:
            if k in text: scores["jewelry"] += 3
        for k in liability_kw:
            if k in text: scores["liability"] += 3

        # protect from false currency routing when price appears inside another topic
        if re.search(r"\d+[\d\s.,]*\s*(\$|usd|доллар)", text):
            if scores["phone"] or scores["electronics"] or scores["medicine"] or scores["food"] or scores["vehicle"] or scores["jewelry"]:
                scores["currency"] -= 10
        return scores

    def detect_topic(self, text: str, user_id: int) -> Optional[str]:
        scores = self._topic_score(text)
        priority = ["phone", "medicine", "vehicle", "jewelry", "food", "alcohol_tobacco", "prohibited", "liability", "electronics", "currency"]
        for topic in priority:
            if scores[topic] > 0 and scores[topic] == max(scores.values()):
                return topic
        remembered = self.get_topic(user_id)
        return remembered

    def _find_faq_match(self, text: str, topic: Optional[str]) -> Optional[Dict[str, Any]]:
        items: List[Dict[str, Any]] = self.data.get("items", [])
        best = None
        best_score = 0
        topic_map = {"phone": "electronics"}
        desired_topic = topic_map.get(topic, topic)
        for item in items:
            score = 0
            item_topic = item.get("topic")
            if desired_topic and item_topic == desired_topic:
                score += 2
            patterns = item.get("patterns", []) + item.get("keywords", [])
            for p in patterns:
                pn = self.normalize_text(p)
                if pn and pn in text:
                    score += max(3, len(pn.split()))
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
        w = re.search(r"(\d+[\d\s.,]*)\s*(кг|килограмм)", text)
        if w:
            weight = float(w.group(1).replace(" ", "").replace(",", "."))
        if "аэропорт" in text:
            mode = "airport"
        elif "граница" in text or "пеш" in text or "авто" in text:
            mode = "border"
        elif "поезд" in text or "жд" in text or "желез" in text or "реч" in text:
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

    def calculate_duty(self, text: str) -> Optional[str]:
        money, weight, mode = self._parse_money_weight(text)
        if money is None or mode is None:
            return None
        limit = self._duty_limit(mode)
        if limit is None:
            return None
        over = max(0.0, money - limit)
        if over <= 0:
            label = {"airport": "аэропорт", "rail_river": "ж/д или речной транспорт", "border": "граница", "courier": "курьер", "post": "почта"}[mode]
            return self.format_answer(
                f"Стоимость {money:.0f}$ укладывается в лимит для режима «{label}». Пошлина не начисляется.",
                "Постановление КМ РУз №244 от 19.04.2025"
            )
        duty_30 = over * 0.30
        if weight is not None:
            duty_min = weight * 3.0
            final = max(duty_30, duty_min)
            extra = f"Сверх лимита: {over:.0f}$. 30% = {duty_30:.2f}$. Минимум по весу: {duty_min:.2f}$."
        else:
            final = duty_30
            extra = f"Сверх лимита: {over:.0f}$. 30% = {duty_30:.2f}$. Для расчета минимума по весу нужен вес в кг."
        return self.format_answer(
            f"Ориентировочная пошлина: {final:.2f}$.",
            "ПҚ-4508 от 07.11.2019 и Постановление КМ РУз №244 от 19.04.2025",
            extra,
        )

    def _strict_rule_answer(self, text: str, topic: Optional[str]) -> Optional[str]:
        if topic == "currency":
            if "ввоз" in text:
                return self.format_answer(
                    "Ввоз наличной валюты не ограничен. При необходимости можно заполнить декларацию.",
                    "Положение №66 от 30.01.2018"
                )
            if "вывоз" in text or "вывезти" in text:
                return self.format_answer(
                    "Вывоз наличной валюты разрешен в сумме не более эквивалента 100 000 000 сумов.",
                    "Положение №66 от 30.01.2018"
                )
            if "валют" in text or "доллар" in text or "евро" in text:
                return self.format_answer(
                    "Ввоз наличной валюты не ограничен. Вывоз наличной валюты разрешен в сумме не более эквивалента 100 000 000 сумов.",
                    "Положение №66 от 30.01.2018"
                )

        if topic == "phone":
            duty = self.calculate_duty(text)
            if duty:
                return duty
            return self.format_answer(
                "Через аэропорт можно ввезти до 2 телефонов за один въезд. Общий лимит беспошлинного ввоза — 1000 долларов. Через сухопутную границу лимит — 300 долларов. При превышении применяется единый таможенный платеж: 30% от превышения, но не менее 3 долларов за кг.",
                "Постановление КМ РУз №463 от 22.06.2018, Постановление КМ РУз №244 от 19.04.2025, ПҚ-4508 от 07.11.2019"
            )

        if topic == "electronics":
            duty = self.calculate_duty(text)
            if duty:
                return duty
            return self.format_answer(
                "Для ряда видов техники действует количественная норма. По стоимости лимит зависит от способа ввоза: аэропорт — 1000 долларов, ж/д и речные пункты — 500 долларов, сухопутная граница — 300 долларов. При превышении применяется 30% от превышения, но не менее 3 долларов за кг.",
                "Постановление КМ РУз №463 от 22.06.2018, Постановление КМ РУз №244 от 19.04.2025, ПҚ-4508 от 07.11.2019"
            )

        if topic == "medicine":
            if any(x in text for x in ["наркот", "психотроп", "прекурсор"]):
                return self.format_answer(
                    "Если препарат содержит наркотические вещества — ввоз и вывоз допускается только при наличии медицинских документов, и не более чем на 7 суток потребности. Если препарат содержит психотропные вещества — без меддокумента допускается до 5 видов и не более 2 упаковок каждого в рамках курса лечения. Такие препараты обязательно нужно указать в декларации.",
                    "Постановление КМ РУз №191 от 08.06.2016 и решение по перечням ограниченных препаратов"
                )
            return self.format_answer(
                "Для личного пользования обычно допускается до 10 разных лекарств и не более 5 упаковок каждого. Для наркотических, психотропных препаратов и прекурсоров действует отдельный порядок и могут требоваться специальные документы.",
                "Постановление КМ РУз №191 от 08.06.2016",
                "Напишите точное название препарата — специалист проверит состав и ответит точно."
            )

        if topic == "food":
            food_map = {
                "рис": "Рис — до 3 кг.",
                "мяс": "Мясо и мясные продукты — до 2 кг.",
                "сахар": "Сахар — до 2 кг.",
                "масло": "Растительное масло — до 2 кг.",
                "хлеб": "Хлебобулочные изделия — до 5 кг.",
            }
            for k, v in food_map.items():
                if k in text:
                    return self.format_answer(v, "Постановление КМ РУз №244 от 19.04.2025")
            if any(x in text for x in ["овощ", "фрукт", "сухофрукт"]):
                return self.format_answer("Фрукты, овощи и сухофрукты — до 40 кг.", "Постановление КМ РУз №244 от 19.04.2025")

        if topic == "alcohol_tobacco":
            if "алког" in text or "пиво" in text or "вино" in text or "водка" in text:
                return self.format_answer("Алкогольные напитки, включая пиво, — до 2 литров.", "Постановление КМ РУз №244 от 19.04.2025")
            if "сигар" in text:
                return self.format_answer("Сигареты — до 200 штук. Сигары — до 5 штук. Табак — до 100 грамм.", "Постановление КМ РУз №244 от 19.04.2025")
            if "парфюм" in text:
                return self.format_answer("Парфюмерия — до 3 единиц, объемом не более 300 мл каждая.", "Постановление КМ РУз №244 от 19.04.2025")

        if topic == "vehicle":
            return self.format_answer(
                "Временный ввоз автотранспортных средств для физлиц в обычном порядке не разрешается, кроме отдельных случаев. Временный вывоз для личного пользования допускается на время нахождения за границей. Общая продолжительность пребывания временно ввезенного транспортного средства для некоммерческих целей не должна превышать 90 календарных дней в течение календарного года.",
                "Таможенный кодекс РУз, статьи 62 и 159"
            )

        if topic == "jewelry":
            if "полу" in text or "полуготов" in text:
                return self.format_answer(
                    "Полуготовые ювелирные изделия без специального заключения вывозить нельзя. Требуется заключение Инспекции пробирного контроля.",
                    "Постановление КМ РУз №281 от 29.04.2025"
                )
            if "ввоз" in text:
                return self.format_answer(
                    "При ввозе ювелирных изделий с 1 сентября 2025 года до 1 сентября 2028 года применяется таможенная пошлина 2 процента.",
                    "ПҚ-207 от 26.06.2025"
                )

        if topic == "prohibited":
            if "дрон" in text or "квадрокоптер" in text:
                return self.format_answer("Дроны запрещены к ввозу, хранению и использованию без специального разрешения.", "Постановление КМ РУз №658 от 15.11.2022")
            if "оруж" in text:
                return self.format_answer("Оружие и боеприпасы нельзя ввозить или вывозить без специальных разрешений.", "Закон РУз «Об оружии» №ЎРҚ-550 от 29.07.2019")
            if "пирот" in text or "петард" in text or "фейерверк" in text:
                return self.format_answer("Пиротехнические изделия запрещены или требуют отдельного разрешительного порядка.", "Указ Президента №ПФ-5286 от 15.12.2017 и профильные акты по пиротехнике")
            return self.format_answer("Существуют товары с жесткими ограничениями или запретами: наркотические средства, психотропные вещества, оружие и боеприпасы, пиротехника, отдельные дроны и другие товары с разрешительным порядком.", "Указ Президента №ПФ-5286 от 15.12.2017 и специальные законы")

        if topic == "liability":
            return self.format_answer("За нарушение таможенных правил возможны административная или уголовная ответственность, штраф, конфискация товара и в отдельных случаях лишение свободы.", "КоАО РУз и УК РУз")
        return None

    def find_answer(self, user_id: int, text: str) -> Optional[str]:
        normalized = self.normalize_text(text)
        topic = self.detect_topic(normalized, user_id)
        if topic:
            self.set_topic(user_id, topic, normalized)

        # strict rules first
        strict = self._strict_rule_answer(normalized, topic)
        if strict:
            return strict

        # calculator if price/weight and remembered topic fits goods
        if topic in {"phone", "electronics", "jewelry", "vehicle"} or self.get_topic(user_id) in {"phone", "electronics", "jewelry", "vehicle"}:
            duty = self.calculate_duty(normalized)
            if duty:
                return duty

        # FAQ next
        matched = self._find_faq_match(normalized, topic)
        if matched:
            answer = matched.get("answer") or matched.get("title")
            source = matched.get("law") or matched.get("source") or matched.get("basis")
            follow = matched.get("follow_up")
            return self.format_answer(answer, source, follow)

        remembered = self.get_topic(user_id)
        if remembered == "currency":
            return self.format_answer("Напишите сумму и направление: ввоз или вывоз.", "Положение №66 от 30.01.2018")
        if remembered == "medicine":
            return self.format_answer("Напишите точное название препарата — специалист проверит состав и ответит точно.", "Постановление КМ РУз №191 от 08.06.2016")
        if remembered in {"phone", "electronics"}:
            return self.format_answer("Напишите стоимость в долларах, вес в кг и как везете: аэропорт / граница / поезд. Я посчитаю точно.", "Постановление КМ РУз №244 от 19.04.2025 и ПҚ-4508 от 07.11.2019")
        if remembered == "vehicle":
            return self.format_answer("Напишите: временный ввоз или временный вывоз, чье авто и на какой срок.", "Таможенный кодекс РУз, статьи 62 и 159")
        return None


def get_physical_keyboard():
    if not ReplyKeyboardMarkup or not KeyboardButton:
        return None
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("💰 Валюта"), KeyboardButton("💊 Лекарства"),
        KeyboardButton("📱 Техника"), KeyboardButton("🚗 Авто"),
        KeyboardButton("🍎 Продукты"), KeyboardButton("🚫 Запрещено"),
        KeyboardButton("💎 Ювелирка"), KeyboardButton("⚖️ Ответственность"),
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
