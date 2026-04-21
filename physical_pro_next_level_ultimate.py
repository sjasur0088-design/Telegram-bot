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
            # ru typos
            "телфон": "телефон",
            "телефн": "телефон",
            "сколка": "сколько",
            "скока": "сколько",
            "ввозит": "ввозить",
            "вывозит": "вывозить",
            "лекарство": "лекарства",
            "таблетка": "таблетки",
            "сигара": "сигары",
            "сигар": "сигары",
            "айфон": "iphone",
            "самсунг": "samsung",
            "телик": "телевизор",
            "ноут": "ноутбук",
            "психотропические": "психотропные",
            # uz helpers
            "bojsiz": "без пошлины",
            "valyuta": "валюта",
            "dori": "лекарства",
            "telefon": "телефон",
            "sigara": "сигары",
            "sigaret": "сигареты",
            "alkogol": "алкоголь",
            "aeroport": "аэропорт",
            "samolyot": "аэропорт",
            "samalet": "аэропорт",
            "poezd": "поезд",
            "chegara": "граница",
            "registratsiya": "регистрация",
            "ro'yxat": "регистрация",
            "qozog'iston": "казахстан",
            "qozogiston": "казахстан",
        }
        # concrete tech from 463
        self.tech_specific_keywords = [
            "телефон", "iphone", "samsung", "смартфон", "мобиль",
            "телевизор", "tv", "холодильник", "морозильник", "кондиционер",
            "стиральн", "пылесос", "газовая плита", "электроплита", "плита",
            "микроволнов", "духовка", "мясорубка", "утюг", "фен", "кухонный комбайн",
            "компьютер", "принтер", "мфу", "планшет", "ноутбук", "laptop",
        ]
        self.food_keywords = ["рис", "сахар", "мясо", "масло", "хлеб", "овощ", "фрук", "сухофрукт"]
        self.forbidden_keywords = ["запрещ", "оруж", "дрон", "квадрокоптер", "пиротех", "петарда", "фейерверк", "порно", "экстрем"]
        self.alcohol_tobacco_keywords = ["алкоголь", "вино", "водка", "пиво", "сигарет", "сигары", "табак", "парфюм", "духи"]
        self.medicine_keywords = ["лекар", "препарат", "таблет", "анальгин", "ибупрофен", "цитрамон", "соннат", "психотроп", "наркот"]
        self.currency_keywords = ["валюта", "доллар", "usd", "евро", "налич", "сум"]
        self.registration_keywords = ["регистрац", "регестра", "миграц", "гостиниц", "лечение", "казахстан"]
        self.liability_keywords = ["штраф", "ответствен", "конфискац", "уголов", "административ", "контрабанд"]
        self.jewelry_keywords = ["ювелир", "кольцо", "цепоч", "серьг", "браслет", "золото"]
        self.vehicle_keywords = ["авто", "машин", "автомоб", "иномарк", "номера", "временный ввоз", "временный вывоз"]

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
        t = re.sub(r"[^\w\s$€₽.,:/-]", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        for src, dst in self.synonyms.items():
            t = re.sub(rf"\b{re.escape(src)}\b", dst, t)
        return t

    def set_topic(self, user_id: int, topic: str, text: str) -> None:
        self.user_ctx[user_id] = {"topic": topic, "last_text": text}

    def get_topic(self, user_id: int) -> Optional[str]:
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
        elif "граница" in text or "авто" in text or "пеш" in text:
            mode = "border"
        elif "поезд" in text or "ж/д" in text or "жд" in text or "речной" in text:
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
        final_duty = max(duty_30, duty_min) if duty_min is not None else duty_30
        extra = f"Сверх лимита: {over:.0f}$. 30% = {duty_30:.2f}$."
        if duty_min is not None:
            extra += f" Минимум по весу: {duty_min:.2f}$."
        else:
            extra += " Для расчёта минимума по весу нужен вес в кг."
        return self.format_answer(
            f"Ориентировочная пошлина: {final_duty:.2f}$.",
            "ПҚ-4508 от 07.11.2019 и Постановление КМ РУз №244 от 19.04.2025",
            extra,
        )

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
                p_norm = self.normalize_text(str(p))
                if p_norm and p_norm in text:
                    score += max(4, len(p_norm.split()))
            if score > best_score:
                best_score = score
                best = item
        return best if best_score > 0 else None

    def detect_topic(self, text: str) -> Optional[str]:
        # strict priority
        if any(k in text for k in self.registration_keywords):
            return "migration"
        if any(k in text for k in self.forbidden_keywords):
            return "prohibited"
        if any(k in text for k in self.medicine_keywords):
            return "medicine"
        if any(k in text for k in self.alcohol_tobacco_keywords):
            return "alcohol_tobacco"
        if any(k in text for k in self.tech_specific_keywords):
            return "tech_specific"
        if any(k in text for k in self.food_keywords):
            return "food"
        if any(k in text for k in self.vehicle_keywords):
            return "vehicle"
        if any(k in text for k in self.jewelry_keywords):
            return "jewelry"
        if any(k in text for k in self.liability_keywords):
            return "liability"
        if any(k in text for k in self.currency_keywords):
            return "currency"
        if "без пошлины" in text or "лимит" in text or "сколько можно" in text:
            return "limits"
        return None

    def _answer_migration(self, text: str) -> str:
        if "казахстан" in text and ("без регистрации" in text or "регистрация" in text):
            return self.format_answer(
                "Гражданин Казахстана может находиться в Узбекистане без регистрации до 10 дней.",
                "предоставленная пользователем база по миграции",
                "Если дольше — обычно нужна гостиница или лечение.",
            )
        if "без регистрации" in text or "регистрация" in text:
            return self.format_answer(
                "По регистрации важно смотреть гражданство, срок пребывания и основание. По твоей базе для гражданина Казахстана — до 10 дней без регистрации.",
                "предоставленная пользователем база по миграции",
                "Если дольше — обычно нужна гостиница или лечение.",
            )
        return self.format_answer(
            "По регистрации важно смотреть гражданство и срок пребывания. Напишите гражданство и сколько дней хотите находиться — отвечу точнее.",
            "предоставленная пользователем база по миграции",
        )

    def _answer_medicine(self, text: str) -> str:
        if "психотроп" in text or "наркот" in text or "соннат" in text:
            return self.format_answer(
                "Если препарат содержит наркотические вещества — ввоз и вывоз допускается только при наличии медицинских документов, и не более чем на 7 суток потребности. Если препарат содержит психотропные вещества — без меддокумента допускается до 5 видов и не более 2 упаковок каждого в рамках курса лечения. Такие препараты нужно указывать в декларации.",
                "Постановление КМ РУз №191 от 08.06.2016 и предоставленный пользователем блок по специальным препаратам",
                "Напишите точное название препарата — специалист проверит состав по перечню и ответит точно.",
            )
        if any(x in text for x in ["цитрамон", "анальгин", "ибупрофен", "парацетамол"]):
            return self.format_answer(
                "Для личного пользования обычно допускается до 10 разных лекарств и не более 5 упаковок каждого. Если препарат не относится к наркотическим или психотропным, применяется общий порядок.",
                "Постановление КМ РУз №191 от 08.06.2016",
                "Если хотите точную проверку — напишите полное название препарата.",
            )
        return self.format_answer(
            "Для личного пользования обычно допускается до 10 разных лекарств и не более 5 упаковок каждого. Для наркотических, психотропных препаратов и прекурсоров действует отдельный порядок и могут требоваться специальные документы.",
            "Постановление КМ РУз №191 от 08.06.2016",
            "Напишите точное название препарата — специалист проверит состав и ответит точно.",
        )

    def _answer_alcohol_tobacco(self, text: str) -> str:
        if "сигар" in text and "сигарет" not in text:
            return self.format_answer(
                "Сигары можно ввозить до 5 штук.",
                "Постановление КМ РУз №244 от 19.04.2025",
            )
        if "сигарет" in text:
            return self.format_answer(
                "Сигареты можно ввозить до 200 штук.",
                "Постановление КМ РУз №244 от 19.04.2025",
            )
        if "табак" in text:
            return self.format_answer(
                "Табак можно ввозить до 100 грамм.",
                "Постановление КМ РУз №244 от 19.04.2025",
            )
        if "парфюм" in text or "духи" in text:
            return self.format_answer(
                "Парфюмерию можно ввозить до 3 флаконов, объёмом не более 300 мл каждый.",
                "Постановление КМ РУз №244 от 19.04.2025",
            )
        return self.format_answer(
            "Алкоголь можно ввозить до 2 литров.",
            "Постановление КМ РУз №244 от 19.04.2025",
            "Если вопрос про сигареты, сигары, табак или парфюмерию — напишите конкретно.",
        )

    def _answer_food(self, text: str) -> str:
        if "рис" in text:
            return self.format_answer("Рис можно вывозить до 3 кг.", "Постановление КМ РУз №244 от 19.04.2025")
        if "сахар" in text:
            return self.format_answer("Сахар можно вывозить до 2 кг.", "Постановление КМ РУз №244 от 19.04.2025")
        if "мяс" in text:
            return self.format_answer("Мясо и мясные продукты можно вывозить до 2 кг.", "Постановление КМ РУз №244 от 19.04.2025")
        if "масло" in text:
            return self.format_answer("Растительное масло можно вывозить до 2 кг.", "Постановление КМ РУз №244 от 19.04.2025")
        if "хлеб" in text:
            return self.format_answer("Хлебобулочные изделия можно вывозить до 5 кг.", "Постановление КМ РУз №244 от 19.04.2025")
        return self.format_answer(
            "Для продуктов действуют отдельные количественные нормы по каждому виду товара.",
            "Постановление КМ РУз №244 от 19.04.2025",
            "Напишите конкретный продукт.",
        )

    def _answer_prohibited(self, text: str) -> str:
        if "дрон" in text or "квадрокоптер" in text:
            return self.format_answer("Дроны и квадрокоптеры нельзя ввозить, хранить и использовать без специального разрешения.", "Постановление КМ РУз №658 от 15.11.2022")
        if "оруж" in text:
            return self.format_answer("Оружие и боеприпасы нельзя ввозить или вывозить без специальных разрешений.", "Закон РУз «Об оружии» №ЎРҚ-550 от 29.07.2019")
        if "пиротех" in text or "петарда" in text or "фейерверк" in text:
            return self.format_answer("Пиротехнические средства относятся к товарам с ограничением или запретом. Для них нужен отдельный разрешительный порядок.", "Указ Президента №ПФ-5286 от 15.12.2017 и профильные акты по пиротехнике")
        return self.format_answer(
            "К запрещённым или строго ограниченным товарам относятся, в частности, наркотические средства, психотропные вещества, прекурсоры, оружие и боеприпасы, дроны, пиротехника, экстремистские и порнографические материалы.",
            "Указ Президента №ПФ-5286 от 15.12.2017 и специальные акты",
            "Напишите конкретный товар — скажу точнее.",
        )

    def _answer_vehicle(self, text: str) -> str:
        return self.format_answer(
            "По автотранспорту действует отдельный порядок. Для физлиц временный вывоз для некоммерческих целей допускается на время нахождения за границей. Общая продолжительность пребывания временно ввезённого авто для некоммерческих целей обычно не должна превышать 90 календарных дней в году.",
            "Таможенный кодекс РУз, статьи 62 и 159",
            "Напишите: временный ввоз или вывоз, чьё авто и на какой срок.",
        )

    def _answer_jewelry(self, text: str) -> str:
        if "полу" in text:
            return self.format_answer("Полуготовые ювелирные изделия нельзя вывозить без специального заключения инспекции.", "Постановление КМ №281 от 29.04.2025")
        return self.format_answer(
            "По ювелирным изделиям важно различать готовое изделие, полуфабрикат и сырьё. Для полуготовых изделий действует отдельный разрешительный порядок.",
            "Постановление КМ №281 от 29.04.2025 и ПҚ-207 от 26.06.2025",
            "Напишите, что именно: кольцо, цепочка, золото, полуфабрикат.",
        )

    def _answer_liability(self, text: str) -> str:
        return self.format_answer(
            "За нарушение таможенных правил может быть административная или уголовная ответственность: штраф, конфискация, а в тяжёлых случаях — лишение свободы.",
            "КоАО и УК РУз, в том числе статьи 227(10)-227(25) КоАО, 182, 184, 246 УК",
        )

    def _answer_currency(self, text: str) -> str:
        if "вывоз" in text or "вывезти" in text or "olib chiq" in text:
            return self.format_answer(
                "Вывоз наличной валюты разрешён в сумме не более эквивалента 100 000 000 сумов.",
                "Положение №66 от 30.01.2018",
            )
        return self.format_answer(
            "Ввоз наличной валюты не ограничен. При необходимости можно заполнить декларацию, таможня подтвердит её с печатью.",
            "Положение №66 от 30.01.2018",
        )

    def _answer_limits(self, text: str) -> str:
        return self.format_answer(
            "Лимит беспошлинного ввоза зависит от способа въезда: аэропорт — 1000$, ж/д и речные пункты — 500$, авто и пешком — 300$, международный курьер — 200$, международная почта — 100$.",
            "Постановление КМ РУз №244 от 19.04.2025",
            "Если лимит превышен, применяется 30% от стоимости, но не менее 3$ за кг.",
        )

    def _answer_tech_specific(self, text: str) -> str:
        item = None
        if "телефон" in text or "iphone" in text or "samsung" in text or "смартфон" in text:
            item = "phone"
        elif "телевизор" in text or "tv" in text:
            item = "tv"
        elif "ноутбук" in text or "laptop" in text:
            item = "laptop"
        elif "планшет" in text:
            item = "tablet"
        elif "компьютер" in text:
            item = "computer"
        else:
            item = "generic"

        if item == "phone":
            return self.format_answer(
                "Через аэропорт можно ввезти до 2 телефонов за один въезд. Через авто, ж/д и речные пункты — 1 телефон, 1 раз в 6 календарных месяцев. По стоимости лимит: аэропорт — 1000$, ж/д и речные пункты — 500$, авто/пешком — 300$. При превышении — 30% от превышения, но не менее 3$ за кг.",
                "Постановление КМ РУз №463 от 22.06.2018, Постановление КМ РУз №244 от 19.04.2025, ПҚ-4508 от 07.11.2019",
            )

        noun = {
            "tv": "Телевизор",
            "laptop": "Ноутбук",
            "tablet": "Планшет",
            "computer": "Компьютерная техника",
            "generic": "Техника",
        }[item]
        return self.format_answer(
            f"{noun} через авто, ж/д и речные пункты можно ввозить по 1 штуке, 1 раз в 6 календарных месяцев. По стоимости лимит беспошлинного ввоза зависит от способа въезда: аэропорт — 1000$, ж/д и речные пункты — 500$, авто/пешком — 300$. При превышении применяется 30% от суммы превышения, но не менее 3$ за кг.",
            "Постановление КМ РУз №463 от 22.06.2018, Постановление КМ РУз №244 от 19.04.2025, ПҚ-4508 от 07.11.2019",
            "Если напишете стоимость и как везёте, я посчитаю точнее.",
        )

    def find_answer(self, user_id: int, text: str) -> Optional[str]:
        normalized = self.normalize_text(text)

        # 1. duty calculator first if user provided enough numbers
        duty_answer = self.calculate_duty(normalized)
        if duty_answer:
            topic = self.detect_topic(normalized) or self.get_topic(user_id) or "tech_specific"
            self.set_topic(user_id, topic, normalized)
            return duty_answer

        # 2. determine NEW topic first, before memory
        topic = self.detect_topic(normalized)
        if topic:
            self.set_topic(user_id, topic, normalized)
            # direct high-confidence rules
            if topic == "migration":
                return self._answer_migration(normalized)
            if topic == "medicine":
                return self._answer_medicine(normalized)
            if topic == "alcohol_tobacco":
                return self._answer_alcohol_tobacco(normalized)
            if topic == "food":
                return self._answer_food(normalized)
            if topic == "prohibited":
                return self._answer_prohibited(normalized)
            if topic == "vehicle":
                return self._answer_vehicle(normalized)
            if topic == "jewelry":
                return self._answer_jewelry(normalized)
            if topic == "liability":
                return self._answer_liability(normalized)
            if topic == "currency":
                return self._answer_currency(normalized)
            if topic == "limits":
                return self._answer_limits(normalized)
            if topic == "tech_specific":
                return self._answer_tech_specific(normalized)

        # 3. FAQ search if no direct topic or as optional enhancement
        matched = self._find_faq_match(normalized, topic or self.get_topic(user_id))
        if matched:
            answer = matched.get("answer") or matched.get("title")
            source = matched.get("law") or matched.get("source") or matched.get("basis")
            follow = matched.get("follow_up")
            return self.format_answer(answer, source, follow)

        # 4. short follow-up by memory only on short clarifications
        remembered = self.get_topic(user_id)
        if remembered and len(normalized.split()) <= 4:
            if remembered == "food":
                return self._answer_food(normalized)
            if remembered == "medicine":
                return self._answer_medicine(normalized)
            if remembered == "alcohol_tobacco":
                return self._answer_alcohol_tobacco(normalized)
            if remembered == "tech_specific":
                return self._answer_tech_specific(normalized)
            if remembered == "currency":
                return self._answer_currency(normalized)
            if remembered == "migration":
                return self._answer_migration(normalized)

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
