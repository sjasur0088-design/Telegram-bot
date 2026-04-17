import json
from pathlib import Path
from typing import Any, Dict, Optional


class PhysicalDocumentEngine:
    def __init__(self, knowledge_path: Optional[str] = None) -> None:
        base_dir = Path(__file__).resolve().parent
        self.knowledge_path = Path(knowledge_path) if knowledge_path else base_dir / "physical_knowledge_pro.json"
        self.data = self._load_knowledge()
        self.rules = self.data.get("rules", {})
        self.categories = self.data.get("categories", {})

    def _load_knowledge(self) -> Dict[str, Any]:
        with open(self.knowledge_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _lang(self, route: Dict[str, Any]) -> str:
        return route.get("lang", "ru")

    def _category_data(self, route: Dict[str, Any]) -> Dict[str, Any]:
        return self.categories.get(route.get("category"), {})

    def _limits(self) -> Dict[str, Any]:
        return self.rules.get("limits_usd", {})

    def _duty_rule(self, lang: str) -> str:
        return self.rules.get("duty_rule", {}).get(lang, "")

    def _crossing_label(self, crossing_type: Optional[str], lang: str) -> str:
        labels = {
            "ru": {
                "airport": "аэропорт",
                "rail_river": "ж/д или речной пункт",
                "car": "автодорожный пункт",
                "foot": "пешеходный пункт",
                "courier": "международный курьер",
                "post": "международная почта",
            },
            "uz": {
                "airport": "aeroport",
                "rail_river": "temir yo'l yoki daryo punkti",
                "car": "avtomobil punkti",
                "foot": "piyoda punkti",
                "courier": "xalqaro kuryer",
                "post": "xalqaro pochta",
            }
        }
        return labels.get(lang, labels["ru"]).get(crossing_type or "", crossing_type or "")

    def _limit_for_crossing(self, crossing_type: Optional[str]) -> Optional[float]:
        limits = self._limits()
        if not crossing_type:
            return None
        return limits.get(crossing_type)

    def _format_limits_text(self, lang: str) -> str:
        limits = self._limits()
        if lang == "uz":
            return (
                f"aeroport — {limits.get('airport', 1000)}$, "
                f"temir yo'l va daryo punktlari — {limits.get('rail_river', 500)}$, "
                f"avto va piyoda — {limits.get('car', 300)}$, "
                f"xalqaro kuryer — {limits.get('courier', 200)}$, "
                f"xalqaro pochta — {limits.get('post', 100)}$"
            )
        return (
            f"аэропорт — {limits.get('airport', 1000)}$, "
            f"ж/д и речные пункты — {limits.get('rail_river', 500)}$, "
            f"авто и пешком — {limits.get('car', 300)}$, "
            f"международный курьер — {limits.get('courier', 200)}$, "
            f"международная почта — {limits.get('post', 100)}$"
        )

    def _electronics_item(self, route: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        cat = self.categories.get("electronics", {})
        item_key = route.get("item")
        if not item_key:
            return None
        return cat.get("items", {}).get(item_key)

    def _medicine_item(self, route: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        cat = self.categories.get("medicine", {})
        item_key = route.get("item")
        if not item_key:
            return None
        return cat.get("named_items", {}).get(item_key)

    def _forbidden_item(self, route: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        cat = self.categories.get("forbidden", {})
        item_key = route.get("item")
        if not item_key:
            return None
        return cat.get("items", {}).get(item_key)

    def _build_electronics_basic(self, route: Dict[str, Any]) -> str:
        lang = self._lang(route)
        item = self._electronics_item(route)
        cat = self.categories.get("electronics", {})

        if not item:
            rule = cat.get("default_followup", {}).get(lang, "")
            if lang == "uz":
                return f"Texnika bo'yicha shaxsiy foydalanish uchun me'yorlar tovar turiga va kirish usuliga bog'liq.\n\n{rule}"
            return f"По технике для личного пользования нормы зависят от вида товара и способа въезда.\n\n{rule}"

        base_answer = item.get("base_answer", {}).get(lang, "")
        quantity_rule = item.get("quantity_rule", {}).get(lang, "")
        limits_text = self._format_limits_text(lang)
        duty_rule = self._duty_rule(lang)
        followup = item.get("calc_followup", {}).get(lang) or cat.get("default_followup", {}).get(lang, "")

        if lang == "uz":
            return (
                f"{base_answer}\n"
                f"Qiymat limiti kirish usuliga bog'liq: {limits_text}.\n"
                f"{duty_rule}\n\n"
                f"{followup}"
            )

        return (
            f"{base_answer}\n"
            f"По сумме лимит зависит от способа въезда: {limits_text}.\n"
            f"{duty_rule}\n\n"
            f"{followup}"
        )

    def _build_electronics_calculation(self, route: Dict[str, Any]) -> str:
        lang = self._lang(route)
        item = self._electronics_item(route)
        cat = self.categories.get("electronics", {})
        facts = route.get("facts", {})

        base_answer = ""
        quantity_rule = ""
        if item:
            base_answer = item.get("base_answer", {}).get(lang, "")
            quantity_rule = item.get("quantity_rule", {}).get(lang, "")

        price = (facts.get("price") or {}).get("value")
        currency = (facts.get("price") or {}).get("currency")
        crossing_type = facts.get("crossing_type")
        weight_kg = facts.get("weight_kg")
        limit_value = self._limit_for_crossing(crossing_type)
        duty_rule = self._duty_rule(lang)

        parts = []

        if base_answer:
            parts.append(base_answer)

        if crossing_type and limit_value is not None:
            crossing_label = self._crossing_label(crossing_type, lang)
            if lang == "uz":
                parts.append(f"{crossing_label.capitalize()} orqali limit {int(limit_value)}$.")
            else:
                parts.append(f"Через {crossing_label} лимит {int(limit_value)}$.")

        if price is not None and limit_value is not None and currency in ("доллар", "$"):
            exceed = price - limit_value
            if exceed > 0:
                if lang == "uz":
                    parts.append(f"Sizda oshish {int(exceed) if exceed.is_integer() else exceed}$.")
                    parts.append(duty_rule)
                    parts.append("Amalda oshgan qismdan 30% va vazn bo'yicha kamida 3$/kg alohida solishtiriladi, keyin kattasi olinadi.")
                else:
                    parts.append(f"У вас превышение {int(exceed) if exceed.is_integer() else exceed}$.")
                    parts.append(duty_rule)
                    parts.append("На практике отдельно считают 30% от превышения и минимум 3$ за кг, затем берут большее значение.")
            else:
                if lang == "uz":
                    parts.append("Bu limitdan oshmaydi.")
                else:
                    parts.append("Это не превышает лимит.")
        else:
            parts.append(duty_rule)

        if weight_kg:
            if lang == "uz":
                parts.append(f"Agar kerak bo'lsa, vazn {weight_kg} kg bo'yicha ham minimal to'lovni tekshirish mumkin.")
            else:
                parts.append(f"При необходимости можно отдельно проверить минимальный платёж по весу: {weight_kg} кг.")

        if not price or not crossing_type:
            followup = item.get("calc_followup", {}).get(lang) if item else cat.get("default_followup", {}).get(lang, "")
            if followup:
                parts.append("")
                parts.append(followup)

        return "\n".join([p for p in parts if p])

    def _build_medicine_general(self, route: Dict[str, Any]) -> str:
        lang = self._lang(route)
        cat = self.categories.get("medicine", {})
        general_rule = cat.get("general_rule", {}).get(lang, "")
        restricted_rule = cat.get("restricted_rule", {}).get(lang, "")
        followup = cat.get("default_followup", {}).get(lang, "")

        return f"{general_rule}\n{restricted_rule}\n\n{followup}"

    def _build_medicine_item(self, route: Dict[str, Any]) -> str:
        lang = self._lang(route)
        cat = self.categories.get("medicine", {})
        item = self._medicine_item(route)
        followup = cat.get("default_followup", {}).get(lang, "")

        if not item:
            return self._build_medicine_general(route)

        answer = item.get("base_answer", {}).get(lang, "")
        if lang == "uz":
            extra = "Nechta qadoq olib kirayotganingizni yozing."
        else:
            extra = "Напишите, сколько упаковок вы везёте."

        if route.get("facts", {}).get("has_recipe"):
            if lang == "uz":
                extra += " Retsept bor bo'lsa, buni ham inobatga olish mumkin."
            else:
                extra += " Если у вас есть рецепт, это тоже можно учитывать."

        return f"{answer}\n\n{extra}"

    def _build_currency(self, route: Dict[str, Any]) -> str:
        lang = self._lang(route)
        cat = self.categories.get("currency", {})
        answer = cat.get("general_rule", {}).get(lang, "")
        followup = cat.get("default_followup", {}).get(lang, "")
        return f"{answer}\n\n{followup}"

    def _build_tobacco_alcohol(self, route: Dict[str, Any]) -> str:
        lang = self._lang(route)
        cat = self.categories.get("tobacco_alcohol", {})
        answer = cat.get("general_rule", {}).get(lang, "")
        followup = cat.get("default_followup", {}).get(lang, "")
        return f"{answer}\n\n{followup}"

    def _build_jewelry(self, route: Dict[str, Any]) -> str:
        lang = self._lang(route)
        cat = self.categories.get("jewelry", {})
        answer = cat.get("general_rule", {}).get(lang, "")
        followup = cat.get("default_followup", {}).get(lang, "")
        return f"{answer}\n\n{followup}"

    def _build_forbidden(self, route: Dict[str, Any]) -> str:
        lang = self._lang(route)
        cat = self.categories.get("forbidden", {})
        item = self._forbidden_item(route)
        followup = cat.get("default_followup", {}).get(lang, "")

        if item:
            answer = item.get("answer", {}).get(lang, "")
            return f"{answer}\n\n{followup}"

        restricted_items = ", ".join([
            "дроны, пиротехника, оружие, боеприпасы, наркотические и психотропные вещества"
            if lang == "ru" else
            "dronlar, pirotexnika, qurol, o'q-dori, narkotik va psixotrop moddalar"
        ])
        if lang == "uz":
            return f"Ba'zi tovarlar cheklangan yoki alohida ruxsat tartibiga ega: {restricted_items}.\n\n{followup}"
        return f"Часть товаров относится к ограниченным или требует отдельного разрешительного порядка: {restricted_items}.\n\n{followup}"

    def _build_auto(self, route: Dict[str, Any]) -> str:
        lang = self._lang(route)
        cat = self.categories.get("auto", {})
        answer = cat.get("general_rule", {}).get(lang, "")
        followup = cat.get("default_followup", {}).get(lang, "")
        return f"{answer}\n\n{followup}"

    def _build_general_limits(self, route: Dict[str, Any]) -> str:
        lang = self._lang(route)
        cat = self.categories.get("general_limits", {})
        answer = cat.get("general_rule", {}).get(lang, "")
        followup = cat.get("default_followup", {}).get(lang, "")
        return f"{answer}\n\n{followup}"

    def build_answer(self, route: Dict[str, Any]) -> str:
        category = route.get("category")
        intent = route.get("intent")

        if category == "electronics":
            if intent in ("calculation", "over_limit"):
                return self._build_electronics_calculation(route)
            return self._build_electronics_basic(route)

        if category == "medicine":
            if route.get("item"):
                return self._build_medicine_item(route)
            return self._build_medicine_general(route)

        if category == "currency":
            return self._build_currency(route)

        if category == "tobacco_alcohol":
            return self._build_tobacco_alcohol(route)

        if category == "jewelry":
            return self._build_jewelry(route)

        if category == "forbidden":
            return self._build_forbidden(route)

        if category == "auto":
            return self._build_auto(route)

        return self._build_general_limits(route)


def load_physical_document_engine(knowledge_path: Optional[str] = None) -> PhysicalDocumentEngine:
    return PhysicalDocumentEngine(knowledge_path=knowledge_path)
