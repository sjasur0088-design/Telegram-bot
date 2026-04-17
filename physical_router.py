import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class PhysicalRouter:
    def __init__(self, knowledge_path: Optional[str] = None) -> None:
        base_dir = Path(__file__).resolve().parent
        self.knowledge_path = Path(knowledge_path) if knowledge_path else base_dir / "physical_knowledge_pro.json"
        self.data = self._load_knowledge()
        self.rules = self.data.get("rules", {})
        self.categories = self.data.get("categories", {})
        self.crossing_aliases = self.data.get("crossing_aliases", {})
        self.intent_markers = self.data.get("intent_markers", {})

    def _load_knowledge(self) -> Dict[str, Any]:
        with open(self.knowledge_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def normalize_text(self, text: str) -> str:
        t = (text or "").lower().strip()

        replacements = {
            "ё": "е",
            "телик": "телевизор",
            "айфон": "телефон",
            "смарт тв": "smart tv",
            "смарт-тв": "smart tv",
            "ж/д": "жд",
            "самолётом": "самолетом",
            "самолёт": "самолет",
            "пограничный пункт": "граница",
            "пешеходный пункт": "пешком",
            "через границу": "граница",
            "usd": "доллар",
            "eur": "евро",
            "у.е.": "доллар",
            "уе": "доллар",
            "kg": "кг",
            "килограмма": "кг",
            "килограммов": "кг",
            "килограмм": "кг",
            "долларов": "доллар",
            "доллара": "доллар",
            "сумов": "сум",
            "сума": "сум",
        }

        for old, new in replacements.items():
            t = t.replace(old, new)

        t = re.sub(r"[,\n\t]+", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def detect_language(self, text_norm: str) -> str:
        cyr_count = sum(1 for ch in text_norm if "а" <= ch <= "я" or ch in "ўқғҳё")
        lat_count = sum(1 for ch in text_norm if "a" <= ch <= "z" or ch in "o'gʻshch")
        return "ru" if cyr_count >= lat_count else "uz"

    def _score_category(self, text_norm: str, category_name: str, lang: str) -> int:
        category = self.categories.get(category_name, {})
        score_keywords = category.get("score_keywords", {}).get(lang, [])
        score = 0

        for kw in score_keywords:
            if kw and kw in text_norm:
                score += 3

        if category_name == "electronics":
            for item in category.get("items", {}).values():
                for alias in item.get("aliases", {}).get(lang, []):
                    if alias and alias in text_norm:
                        score += 5

        if category_name == "medicine":
            for item in category.get("named_items", {}).values():
                for alias in item.get("aliases", {}).get(lang, []):
                    if alias and alias in text_norm:
                        score += 5

        if category_name == "forbidden":
            for item in category.get("items", {}).values():
                for alias in item.get("aliases", {}).get(lang, []):
                    if alias and alias in text_norm:
                        score += 5

        return score

    def detect_category(self, text_norm: str, lang: str) -> Dict[str, Any]:
        scores: Dict[str, int] = {}

        for category_name in self.categories.keys():
            scores[category_name] = self._score_category(text_norm, category_name, lang)

        best_category = max(scores, key=scores.get) if scores else "general_limits"
        best_score = scores.get(best_category, 0)

        if best_score <= 0:
            best_category = "general_limits"

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return {
            "category": best_category,
            "score": best_score,
            "ranked": ranked,
        }

    def detect_crossing_type(self, text_norm: str) -> Optional[str]:
        for crossing_type, aliases in self.crossing_aliases.items():
            for alias in aliases:
                if alias and alias in text_norm:
                    return crossing_type
        return None

    def detect_item(self, text_norm: str, category: str, lang: str) -> Optional[str]:
        cat = self.categories.get(category, {})

        if category == "electronics":
            for item_name, item_data in cat.get("items", {}).items():
                for alias in item_data.get("aliases", {}).get(lang, []):
                    if alias and alias in text_norm:
                        return item_name

        elif category == "medicine":
            for item_name, item_data in cat.get("named_items", {}).items():
                for alias in item_data.get("aliases", {}).get(lang, []):
                    if alias and alias in text_norm:
                        return item_name

        elif category == "forbidden":
            for item_name, item_data in cat.get("items", {}).items():
                for alias in item_data.get("aliases", {}).get(lang, []):
                    if alias and alias in text_norm:
                        return item_name

        return None

    def _extract_price(self, text_norm: str) -> Optional[Dict[str, Any]]:
        patterns = [
            r"(\d+(?:[.,]\d+)?)\s*(доллар|евро|сум)",
            r"(\d+(?:[.,]\d+)?)\s*(\$)",
        ]

        for pattern in patterns:
            m = re.search(pattern, text_norm)
            if m:
                value_raw = m.group(1).replace(",", ".")
                currency = m.group(2)
                try:
                    value = float(value_raw)
                except ValueError:
                    continue

                if currency == "$":
                    currency = "доллар"

                return {
                    "value": value,
                    "currency": currency,
                }
        return None

    def _extract_weight(self, text_norm: str) -> Optional[float]:
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*кг", text_norm)
        if not m:
            return None
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            return None

    def _extract_quantity(self, text_norm: str) -> Optional[int]:
        patterns = [
            r"(\d+)\s*(штук|штуки|штука|дона|упаковок|упаковки|упаковка|телефона|телефон|товара)",
            r"везу\s+(\d+)",
            r"хочу привезти\s+(\d+)",
        ]
        for pattern in patterns:
            m = re.search(pattern, text_norm)
            if m:
                try:
                    return int(m.group(1))
                except ValueError:
                    continue
        return None

    def extract_facts(self, text_norm: str) -> Dict[str, Any]:
        return {
            "price": self._extract_price(text_norm),
            "weight_kg": self._extract_weight(text_norm),
            "quantity": self._extract_quantity(text_norm),
            "crossing_type": self.detect_crossing_type(text_norm),
            "has_recipe": "рецепт" in text_norm or "retsept" in text_norm,
            "for_sale": "на продажу" in text_norm or "sotish uchun" in text_norm,
        }

    def detect_intent(self, text_norm: str, facts: Dict[str, Any], lang: str) -> str:
        if facts.get("price") or facts.get("weight_kg") or facts.get("crossing_type"):
            return "calculation"

        quantity = facts.get("quantity")
        if quantity and quantity > 1:
            return "commercial_risk"

        markers = self.intent_markers

        for marker in markers.get("over_limit", {}).get(lang, []):
            if marker in text_norm:
                return "over_limit"

        for marker in markers.get("quantity_limit", {}).get(lang, []):
            if marker in text_norm:
                return "quantity_limit"

        for marker in markers.get("basic_permission", {}).get(lang, []):
            if marker in text_norm:
                return "basic_permission"

        if len(text_norm.split()) <= 3:
            return "item_rule"

        return "basic_permission"

    def resolve_followup(self, text_norm: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not context:
            return {}

        followup_hits = 0
        for lang_key in ("ru", "uz"):
            for marker in self.intent_markers.get("followup_clarification", {}).get(lang_key, []):
                if marker in text_norm:
                    followup_hits += 1

        short_message = len(text_norm.split()) <= 5

        if followup_hits > 0 or short_message:
            return {
                "is_followup": True,
                "use_context": True,
                "context_category": context.get("last_category"),
                "context_item": context.get("last_item"),
                "context_intent": context.get("last_intent"),
            }

        return {"is_followup": False, "use_context": False}

    def route(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        text_norm = self.normalize_text(text)
        lang = self.detect_language(text_norm)
        followup = self.resolve_followup(text_norm, context)

        category_info = self.detect_category(text_norm, lang)
        category = category_info["category"]

        if followup.get("use_context") and followup.get("context_category"):
            if category_info["score"] < 5:
                category = followup["context_category"]

        item = self.detect_item(text_norm, category, lang)

        if not item and followup.get("use_context") and followup.get("context_item"):
            item = followup["context_item"]

        facts = self.extract_facts(text_norm)
        intent = self.detect_intent(text_norm, facts, lang)

        if followup.get("use_context") and intent == "item_rule" and followup.get("context_intent"):
            if facts.get("price") or facts.get("crossing_type") or facts.get("weight_kg"):
                intent = "calculation"

        return {
            "text_norm": text_norm,
            "lang": lang,
            "category": category,
            "item": item,
            "intent": intent,
            "facts": facts,
            "category_score": category_info["score"],
            "category_ranked": category_info["ranked"],
            "followup": followup,
        }


def load_physical_router(knowledge_path: Optional[str] = None) -> PhysicalRouter:
    return PhysicalRouter(knowledge_path=knowledge_path)
