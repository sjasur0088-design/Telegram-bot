import json
import re
from pathlib import Path


class PhysicalRouter:
    def __init__(self, knowledge_path=None):
        base_dir = Path(__file__).resolve().parent
        self.knowledge_path = Path(knowledge_path) if knowledge_path else base_dir / "physical_knowledge_pro_clean.json"

        with open(self.knowledge_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        self.categories = self.data.get("categories", {})
        self.crossing_aliases = self.data.get("crossing_aliases", {})

    def normalize_text(self, text):
        t = (text or "").lower().strip()

        replacements = {
            "ё": "е",
            "телик": "телевизор",
            "айфон": "телефон",
        }

        for k, v in replacements.items():
            t = t.replace(k, v)

        t = re.sub(r"[,;\n\t]+", " ", t)
        t = re.sub(r"\s+", " ", t)

        return t

    def detect_crossing_type(self, text):
        for key, values in self.crossing_aliases.items():
            for v in values:
                if v in text:
                    return key
        return None

    def extract_price(self, text):
        match = re.search(r"(\d+(?:[.,]\d+)?)", text)
        if not match:
            return None

        try:
            value = float(match.group(1).replace(",", "."))
        except:
            return None

        return {
            "value": value,
            "currency": "доллар"
        }

    def route(self, text, context=None):
        text = self.normalize_text(text)

        category = "general_limits"
        item = None

        if "телевизор" in text or "телефон" in text:
            category = "electronics"

        if "лекар" in text or "препарат" in text:
            category = "medicine"

        if "цитрамон" in text:
            category = "medicine"
            item = "citramon"

        facts = {
            "price": self.extract_price(text),
            "crossing_type": self.detect_crossing_type(text)
        }

        intent = "basic_permission"

        if facts["price"]:
            intent = "calculation"

        return {
            "category": category,
            "item": item,
            "intent": intent,
            "facts": facts
        }


def load_physical_router(path=None):
    return PhysicalRouter(path)
