"""SwitchAI v1: local, explainable styling intelligence.

This is intentionally dependency-free. It gives the product a real AI-shaped
decision layer now, while keeping the seam clean for future model-backed
vision, embeddings, and personalized ranking.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


REQUIRED_CATEGORIES = ("top", "bottom", "shoes")
OPTIONAL_CATEGORIES = ("jacket", "accessory")
VALID_FEEDBACK_ACTIONS = {"love", "like", "dislike"}


def default_switch_ai_memory() -> dict[str, Any]:
    return {
        "version": "SwitchAI v1.0",
        "preferences": {
            "colors": {},
            "categories": {},
            "materials": {},
            "formalityBias": 0,
        },
        "recommendations": [],
        "feedback": [],
    }


def build_switch_ai_recommendation(state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    wardrobe = list(state.get("wardrobe", []))
    if not wardrobe:
        raise ValueError("wardrobe must include at least one item")

    occasion = str(payload.get("occasion") or "Smart casual dinner").strip()
    replace_mode = str(payload.get("replaceMode") or "some")
    budget = float(payload.get("budget") or 0)
    paid_allowed = bool(payload.get("paidAllowed", True))
    selected_names = set(state.get("selected", []))
    memory = state.get("switchAi") or default_switch_ai_memory()
    preferences = memory.get("preferences", {})
    target_formality = _target_formality(occasion, preferences)

    scored_items = [_score_item(item, occasion, target_formality, selected_names, preferences) for item in wardrobe]
    selected = _choose_outfit(scored_items, target_formality, occasion)
    missing = [category for category in REQUIRED_CATEGORIES if not any(item["category"] == category for item in selected)]
    mall_wishlist = _mall_suggestions(state.get("mall", []), missing, target_formality, budget, replace_mode)
    stylist = _pick_stylist(state.get("stylists", []), occasion, paid_allowed)
    reasons = _build_reasons(selected, missing, mall_wishlist, stylist, target_formality, memory)
    confidence = _confidence(selected, missing, memory)

    return {
        "model": "SwitchAI v1.0 local stylist brain",
        "occasion": occasion,
        "targetFormality": target_formality,
        "confidence": confidence,
        "outfitItems": [item["name"] for item in selected],
        "stylistMatch": stylist,
        "mallWishlist": mall_wishlist,
        "reasons": reasons,
        "fitScores": [
            {
                "name": item["name"],
                "category": item["category"],
                "score": round(item["score"], 1),
                "reason": item["reason"],
            }
            for item in selected
        ],
        "missingCategories": missing,
        "learningSummary": _learning_summary(memory),
    }


def apply_switch_ai_feedback(
    memory: dict[str, Any],
    wardrobe: list[dict[str, Any]],
    recommendation: dict[str, Any],
    action: str,
) -> dict[str, Any]:
    updated = deepcopy(memory or default_switch_ai_memory())
    preferences = updated.setdefault("preferences", default_switch_ai_memory()["preferences"])
    weight = {"love": 3, "like": 2, "dislike": -2}[action]
    recommended_names = set(recommendation.get("outfitItems", []))
    recommended_items = [item for item in wardrobe if item.get("name") in recommended_names]
    if not recommended_items:
        return updated

    for item in recommended_items:
        _bump(preferences.setdefault("colors", {}), str(item.get("color", item.get("colorName", "custom"))), weight)
        _bump(preferences.setdefault("categories", {}), str(item.get("category", "custom")), weight)
        _bump(preferences.setdefault("materials", {}), str(item.get("material", "custom")), weight)

    average_formality = sum(int(item.get("formality", 3)) for item in recommended_items) / len(recommended_items)
    direction = 1 if average_formality >= 3.5 else -1
    preferences["formalityBias"] = max(-3, min(3, int(preferences.get("formalityBias", 0)) + direction * (1 if weight > 0 else -1)))
    return updated


def _score_item(
    item: dict[str, Any],
    occasion: str,
    target_formality: int,
    selected_names: set[str],
    preferences: dict[str, Any],
) -> dict[str, Any]:
    category = str(item.get("category", ""))
    formality = int(item.get("formality", 3))
    warmth = int(item.get("warmth", 1))
    color = str(item.get("color", item.get("colorName", "custom")))
    material = str(item.get("material", "custom"))
    fit = str(item.get("fit", "regular"))

    score = 48.0
    score += (5 - abs(formality - target_formality)) * 8
    score += _preference(preferences.get("colors", {}), color) * 3
    score += _preference(preferences.get("categories", {}), category) * 2
    score += _preference(preferences.get("materials", {}), material) * 1.5
    if item.get("name") in selected_names:
        score += 7
    if target_formality >= 4 and category in {"jacket", "shoes"}:
        score += 5
    if any(word in occasion.lower() for word in ("concert", "campus", "street")) and formality <= 3:
        score += 5
    if any(word in material.lower() for word in ("leather", "wool", "linen", "cotton")):
        score += 2
    if "tailored" in fit.lower() and target_formality >= 4:
        score += 3
    if warmth >= 3 and any(word in occasion.lower() for word in ("holiday", "night", "dinner")):
        score += 2

    return {
        **item,
        "score": max(0.0, min(100.0, score)),
        "reason": _item_reason(item, target_formality),
    }


def _choose_outfit(scored_items: list[dict[str, Any]], target_formality: int, occasion: str) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for category in REQUIRED_CATEGORIES:
        candidate = _best_for_category(scored_items, category)
        if candidate:
            selected.append(candidate)

    wants_jacket = target_formality >= 4 or any(word in occasion.lower() for word in ("dinner", "wedding", "interview"))
    if wants_jacket:
        jacket = _best_for_category(scored_items, "jacket")
        if jacket:
            selected.append(jacket)

    accessory = _best_for_category(scored_items, "accessory")
    if accessory and target_formality >= 3:
        selected.append(accessory)

    return selected


def _best_for_category(scored_items: list[dict[str, Any]], category: str) -> dict[str, Any] | None:
    candidates = [item for item in scored_items if item.get("category") == category]
    if not candidates:
        return None
    return max(candidates, key=lambda item: (float(item.get("score", 0)), str(item.get("name", ""))))


def _mall_suggestions(
    mall: list[dict[str, Any]],
    missing: list[str],
    target_formality: int,
    budget: float,
    replace_mode: str,
) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    for item in mall:
        category = str(item.get("category", ""))
        price = float(item.get("price", 0))
        should_suggest = category in missing or replace_mode == "all" or (target_formality >= 4 and category in {"jacket", "shoes"})
        if not should_suggest:
            continue
        if budget and price > max(budget, 1) * 1.15:
            continue
        suggestions.append(
            {
                "item": item.get("item"),
                "store": item.get("store"),
                "price": price,
                "reason": item.get("match") or "Improves the outfit score.",
            }
        )
    return suggestions[:2]


def _pick_stylist(stylists: list[dict[str, Any]], occasion: str, paid_allowed: bool) -> dict[str, Any]:
    if not stylists:
        return {"name": "SwitchAI", "specialty": "Wardrobe intelligence", "score": 0}
    occasion_text = occasion.lower()

    def stylist_score(stylist: dict[str, Any]) -> float:
        specialty = str(stylist.get("specialty", "")).lower()
        overlap = sum(1 for word in occasion_text.split() if len(word) > 3 and word in specialty)
        score = float(stylist.get("rating", 0)) * 12 + min(float(stylist.get("helped", 0)) / 12, 20) + overlap * 10
        if stylist.get("paid") and not paid_allowed:
            score -= 28
        if not stylist.get("paid") and not paid_allowed:
            score += 8
        return score

    best = max(stylists, key=stylist_score)
    return {
        "name": best.get("name"),
        "specialty": best.get("specialty"),
        "paid": bool(best.get("paid")),
        "score": round(stylist_score(best), 1),
    }


def _build_reasons(
    selected: list[dict[str, Any]],
    missing: list[str],
    mall_wishlist: list[dict[str, Any]],
    stylist: dict[str, Any],
    target_formality: int,
    memory: dict[str, Any],
) -> list[str]:
    reasons = [
        f"Built around a {target_formality}/5 formality target using your saved wardrobe.",
        f"Matched you with {stylist.get('name')} for the strongest specialty fit.",
    ]
    if selected:
        names = ", ".join(item["name"] for item in selected[:4])
        reasons.append(f"Selected {names} because they scored highest across fit, category coverage, and learned preference.")
    if missing:
        reasons.append(f"Missing wardrobe categories: {', '.join(missing)}.")
    if mall_wishlist:
        reasons.append("Added mall wishlist options only where they improve a weak or missing category.")
    feedback_count = len(memory.get("feedback", []))
    if feedback_count:
        reasons.append(f"Adjusted ranking using {feedback_count} previous feedback signal{'s' if feedback_count != 1 else ''}.")
    return reasons[:5]


def _confidence(selected: list[dict[str, Any]], missing: list[str], memory: dict[str, Any]) -> int:
    required_found = len({item.get("category") for item in selected if item.get("category") in REQUIRED_CATEGORIES})
    average_score = sum(float(item.get("score", 0)) for item in selected) / max(len(selected), 1)
    feedback_bonus = min(len(memory.get("feedback", [])), 12) * 0.8
    confidence = 42 + required_found * 12 + average_score * 0.18 + feedback_bonus - len(missing) * 12
    return int(max(35, min(98, round(confidence))))


def _target_formality(occasion: str, preferences: dict[str, Any]) -> int:
    text = occasion.lower()
    if any(word in text for word in ("wedding", "interview", "formal", "business")):
        base = 5
    elif any(word in text for word in ("dinner", "date", "guest", "holiday")):
        base = 4
    elif any(word in text for word in ("concert", "campus", "street", "gym")):
        base = 2
    else:
        base = 3
    return max(1, min(5, base + int(preferences.get("formalityBias", 0))))


def _item_reason(item: dict[str, Any], target_formality: int) -> str:
    formality = int(item.get("formality", 3))
    delta = abs(formality - target_formality)
    if delta == 0:
        return "Exact formality match for this occasion."
    if delta == 1:
        return "Close formality match with useful styling flexibility."
    return "Useful category coverage, but less exact for the occasion."


def _learning_summary(memory: dict[str, Any]) -> dict[str, Any]:
    preferences = memory.get("preferences", {})
    return {
        "feedbackCount": len(memory.get("feedback", [])),
        "favoriteColors": _top_preferences(preferences.get("colors", {}), positive=True),
        "avoidColors": _top_preferences(preferences.get("colors", {}), positive=False),
        "favoriteCategories": _top_preferences(preferences.get("categories", {}), positive=True),
    }


def _top_preferences(values: dict[str, Any], positive: bool) -> list[str]:
    filtered = [(key, float(score)) for key, score in values.items() if (float(score) > 0 if positive else float(score) < 0)]
    return [key for key, _score in sorted(filtered, key=lambda pair: abs(pair[1]), reverse=True)[:3]]


def _preference(values: dict[str, Any], key: str) -> float:
    return max(-4.0, min(4.0, float(values.get(key, 0))))


def _bump(values: dict[str, Any], key: str, amount: int) -> None:
    values[key] = int(values.get(key, 0)) + amount
