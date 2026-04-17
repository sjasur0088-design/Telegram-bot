from typing import Any, Dict


def _ensure_bucket(ctx_obj: Dict[str, Any]) -> Dict[str, Any]:
    bucket = ctx_obj.get("physical_pro_context")
    if not isinstance(bucket, dict):
        bucket = {}
        ctx_obj["physical_pro_context"] = bucket
    return bucket


def get_physical_context(ctx_obj: Dict[str, Any]) -> Dict[str, Any]:
    bucket = _ensure_bucket(ctx_obj)
    return {
        "last_category": bucket.get("last_category"),
        "last_item": bucket.get("last_item"),
        "last_intent": bucket.get("last_intent"),
        "last_crossing_type": bucket.get("last_crossing_type"),
        "last_price": bucket.get("last_price"),
        "last_quantity": bucket.get("last_quantity"),
        "last_lang": bucket.get("last_lang"),
        "last_answer": bucket.get("last_answer"),
    }


def save_physical_context(ctx_obj: Dict[str, Any], route: Dict[str, Any], answer: str = "") -> None:
    bucket = _ensure_bucket(ctx_obj)
    facts = route.get("facts", {}) or {}
    bucket["last_category"] = route.get("category")
    bucket["last_item"] = route.get("item")
    bucket["last_intent"] = route.get("intent")
    bucket["last_crossing_type"] = facts.get("crossing_type")
    bucket["last_price"] = facts.get("price")
    bucket["last_quantity"] = facts.get("quantity")
    bucket["last_lang"] = route.get("lang")
    bucket["last_answer"] = answer


def clear_physical_context(ctx_obj: Dict[str, Any]) -> None:
    ctx_obj["physical_pro_context"] = {}
