"""
Bridge module for document-first physical-person flow.

Usage in legacy_bot.py:

1) add imports near the top:
    from physical_router import load_physical_router
    from physical_document_engine import load_physical_document_engine
    from physical_context import get_physical_context, save_physical_context

2) initialize once after BASE_DIR:
    PHYSICAL_ROUTER = load_physical_router(os.path.join(BASE_DIR, "physical_knowledge_pro.json"))
    PHYSICAL_ENGINE = load_physical_document_engine(os.path.join(BASE_DIR, "physical_knowledge_pro.json"))

3) add this helper function into legacy_bot.py or import it from here and call it in physical_chat branch.
"""
from typing import Any, Dict, Tuple


def build_physical_reply(
    text: str,
    lang: str,
    ctx_obj: Dict[str, Any],
    router: Any,
    engine: Any,
    specialist_text: str,
) -> Tuple[str, Dict[str, Any]]:
    prior = get_physical_context(ctx_obj)
    route = router.route(text, context=prior)
    answer = engine.build_answer(route).strip()

    if specialist_text:
        answer = f"{answer}\n\n{specialist_text}"

    save_physical_context(ctx_obj, route, answer)
    return answer, route


def should_use_ai_fallback(route: Dict[str, Any]) -> bool:
    score = route.get("category_score", 0)
    category = route.get("category")
    item = route.get("item")
    intent = route.get("intent")

    if score <= 0:
        return True

    if category in ("electronics", "medicine", "forbidden") and not item and intent == "item_rule":
        return True

    return False


# delayed imports to avoid circular import when pasted into legacy_bot
from physical_context import get_physical_context, save_physical_context
