import json
from pathlib import Path
from typing import Any, Dict, Optional


class PhysicalDocumentEngine:
    def __init__(self, knowledge_path: Optional[str] = None) -> None:
        base_dir = Path(__file__).resolve().parent
        self.knowledge_path = Path(knowledge_path) if knowledge_path else base_dir / "physical_knowledge_pro_clean.json"
        self.data = self._load_knowledge()
        self.rules = self.data.get("rules", {})
        self.categories = self.data.get("categories", {})

    def _load_knowledge(self) -> Dict[str, Any]:
        with open(self.knowledge_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _lang(self, route):
        return route.get("lang", "ru")

    def _limits(self):
        return self.rules.get("limits_usd", {})

    def _duty_rule(self, lang):
        return self.rules.get("duty_rule", {}).get(lang, "")

    def _crossing_label(self, crossing_type, lang):
        labels={"ru":{"airport":"аэропорт","rail_river":"ж/д или речной пункт","car":"автодорожный пункт","foot":"пешеходный пункт","courier":"международный курьер","post":"международная почта"},"uz":{"airport":"aeroport","rail_river":"temir yo'l yoki daryo punkti","car":"avtomobil punkti","foot":"piyoda punkti","courier":"xalqaro kuryer","post":"xalqaro pochta"}}
        return labels.get(lang,labels["ru"]).get(crossing_type or "", crossing_type or "")

    def _format_limits_text(self, lang):
        limits=self._limits()
        if lang=="uz":
            return f"aeroport — {limits.get('airport',1000)}$, temir yo'l va daryo punktlari — {limits.get('rail_river',500)}$, avto va piyoda — {limits.get('car',300)}$, xalqaro kuryer — {limits.get('courier',200)}$, xalqaro pochta — {limits.get('post',100)}$"
        return f"аэропорт — {limits.get('airport',1000)}$, ж/д и речные пункты — {limits.get('rail_river',500)}$, авто и пешком — {limits.get('car',300)}$, международный курьер — {limits.get('courier',200)}$, международная почта — {limits.get('post',100)}$"

    def _electronics_item(self, route):
        return self.categories.get("electronics",{}).get("items",{}).get(route.get("item"))

    def _medicine_item(self, route):
        return self.categories.get("medicine",{}).get("named_items",{}).get(route.get("item"))

    def _forbidden_item(self, route):
        return self.categories.get("forbidden",{}).get("items",{}).get(route.get("item"))

    def _build_electronics_basic(self, route):
        lang=self._lang(route)
        cat=self.categories.get("electronics",{})
        item=self._electronics_item(route)
        if not item:
            rule=cat.get("default_followup",{}).get(lang,"")
            if lang=="uz":
                return f"Texnika bo'yicha shaxsiy foydalanish uchun me'yorlar tovar turiga va kirish usuliga bog'liq.\n\n{rule}"
            return f"По технике для личного пользования нормы зависят от вида товара и способа въезда.\n\n{rule}"
        base_answer=item.get("base_answer",{}).get(lang,"")
        limits_text=self._format_limits_text(lang)
        duty_rule=self._duty_rule(lang)
        followup=item.get("calc_followup",{}).get(lang) or cat.get("default_followup",{}).get(lang,"")
        if lang=="uz":
            return f"{base_answer}\nQiymat limiti kirish usuliga bog'liq: {limits_text}.\n{duty_rule}\n\n{followup}"
        return f"{base_answer}\nПо сумме лимит зависит от способа въезда: {limits_text}.\n{duty_rule}\n\n{followup}"

    def _build_electronics_calculation(self, route):
        lang=self._lang(route)
        item=self._electronics_item(route)
        cat=self.categories.get("electronics",{})
        facts=route.get("facts",{}) or {}
        parts=[]
        if item:
            parts.append(item.get("base_answer",{}).get(lang,""))
        price=(facts.get("price") or {}).get("value")
        currency=(facts.get("price") or {}).get("currency")
        crossing_type=facts.get("crossing_type")
        weight_kg=facts.get("weight_kg")
        limit_value=self._limits().get(crossing_type) if crossing_type else None
        if crossing_type and limit_value is not None:
            label=self._crossing_label(crossing_type,lang)
            if lang=="uz":
                parts.append(f"{label.capitalize()} orqali limit {int(limit_value)}$.")
            else:
                parts.append(f"Через {label} лимит {int(limit_value)}$.")
        if price is not None and limit_value is not None and currency in ("доллар","$"):
            exceed=price-limit_value
            if exceed>0:
                ex_text=int(exceed) if float(exceed).is_integer() else exceed
                if lang=="uz":
                    parts.append(f"Sizda oshish {ex_text}$.")
                    parts.append(self._duty_rule(lang))
                    parts.append("Amalda oshgan qismdan 30% va vazn bo'yicha kamida 3$/kg alohida solishtiriladi, keyin kattasi olinadi.")
                else:
                    parts.append(f"У вас превышение {ex_text}$.")
                    parts.append(self._duty_rule(lang))
                    parts.append("На практике отдельно считают 30% от превышения и минимум 3$ за кг, затем берут большее значение.")
            else:
                parts.append("Это не превышает лимит." if lang=="ru" else "Bu limitdan oshmaydi.")
        else:
            parts.append(self._duty_rule(lang))
        if weight_kg:
            parts.append((f"При необходимости можно отдельно проверить минимальный платёж по весу: {weight_kg} кг.") if lang=="ru" else (f"Agar kerak bo'lsa, vazn {weight_kg} kg bo'yicha ham minimal to'lovni tekshirish mumkin."))
        if not price or not crossing_type:
            followup=item.get("calc_followup",{}).get(lang) if item else cat.get("default_followup",{}).get(lang,"")
            if followup:
                parts.append("")
                parts.append(followup)
        return "\n".join([p for p in parts if p])

    def _build_medicine_general(self, route):
        lang=self._lang(route)
        cat=self.categories.get("medicine",{})
        return f"{cat.get('general_rule',{}).get(lang,'')}\n{cat.get('restricted_rule',{}).get(lang,'')}\n\n{cat.get('default_followup',{}).get(lang,'')}"

    def _build_medicine_item(self, route):
        lang=self._lang(route)
        item=self._medicine_item(route)
        if not item:
            return self._build_medicine_general(route)
        extra="Напишите, сколько упаковок вы везёте." if lang=="ru" else "Nechta qadoq olib kirayotganingizni yozing."
        if route.get("facts",{}).get("has_recipe"):
            extra += " Если у вас есть рецепт, это тоже можно учитывать." if lang=="ru" else " Retsept bor bo'lsa, buni ham inobatga olish mumkin."
        return f"{item.get('base_answer',{}).get(lang,'')}\n\n{extra}"

    def _build_simple(self, category_name, route):
        lang=self._lang(route)
        cat=self.categories.get(category_name,{})
        return f"{cat.get('general_rule',{}).get(lang,'')}\n\n{cat.get('default_followup',{}).get(lang,'')}"

    def _build_forbidden(self, route):
        lang=self._lang(route)
        cat=self.categories.get("forbidden",{})
        item=self._forbidden_item(route)
        followup=cat.get("default_followup",{}).get(lang,"")
        if item:
            return f"{item.get('answer',{}).get(lang,'')}\n\n{followup}"
        if lang=="uz":
            return f"Ba'zi tovarlar cheklangan yoki alohida ruxsat tartibiga ega: dronlar, pirotexnika, qurol, o'q-dori, narkotik va psixotrop moddalar.\n\n{followup}"
        return f"Часть товаров относится к ограниченным или требует отдельного разрешительного порядка: дроны, пиротехника, оружие, боеприпасы, наркотические и психотропные вещества.\n\n{followup}"

    def build_answer(self, route):
        category=route.get("category")
        intent=route.get("intent")
        if category=="electronics":
            return self._build_electronics_calculation(route) if intent in ("calculation","over_limit") else self._build_electronics_basic(route)
        if category=="medicine":
            return self._build_medicine_item(route) if route.get("item") else self._build_medicine_general(route)
        if category=="currency":
            return self._build_simple("currency",route)
        if category=="tobacco_alcohol":
            return self._build_simple("tobacco_alcohol",route)
        if category=="jewelry":
            return self._build_simple("jewelry",route)
        if category=="forbidden":
            return self._build_forbidden(route)
        if category=="auto":
            return self._build_simple("auto",route)
        return self._build_simple("general_limits",route)


def load_physical_document_engine(knowledge_path: Optional[str] = None) -> PhysicalDocumentEngine:
    return PhysicalDocumentEngine(knowledge_path=knowledge_path)
