"""Persistent backend service for the Switch It Up MVP.

The service intentionally uses the Python standard library so the backend can
run locally without installing packages. It stores demo app state in JSON and
reuses the rule-based style engine for outfit recommendations.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from src.style_engine import StyleRequest, WardrobeItem, build_style_plan, sample_stylists


VALID_ROLES = {"normal", "stylist"}
VALID_WISHLIST_ACTIONS = {"accept", "discard"}


class BackendError(ValueError):
    """Raised when an API request cannot be processed."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_state() -> dict[str, Any]:
    return {
        "profile": {
            "id": "user_raymond",
            "name": "Raymond",
            "role": "normal",
            "measurements": {
                "heightCm": 178,
                "topSize": "M",
                "waistIn": 32,
                "shoeSize": "UK 10",
            },
            "scan": {
                "status": "ready",
                "quality": 91,
                "capturedAt": None,
            },
        },
        "wardrobe": [
            {
                "name": "White Oxford Shirt",
                "category": "top",
                "fit": "tailored",
                "material": "brushed cotton",
                "colorName": "white",
                "color": "white",
                "formality": 4,
                "warmth": 1,
                "colors": ["#ffffff", "#cbd5e1"],
            },
            {
                "name": "Black Relaxed Tee",
                "category": "top",
                "fit": "relaxed",
                "material": "premium cotton",
                "colorName": "black",
                "color": "black",
                "formality": 2,
                "warmth": 1,
                "colors": ["#111827", "#334155"],
            },
            {
                "name": "Stone Chinos",
                "category": "bottom",
                "fit": "straight",
                "material": "cotton twill",
                "colorName": "beige",
                "color": "stone",
                "formality": 4,
                "warmth": 2,
                "colors": ["#cdbb9d", "#a8906f"],
            },
            {
                "name": "Dark Denim",
                "category": "bottom",
                "fit": "tapered",
                "material": "raw denim",
                "colorName": "indigo",
                "color": "indigo",
                "formality": 2,
                "warmth": 2,
                "colors": ["#1e3a8a", "#0f172a"],
            },
            {
                "name": "White Trainers",
                "category": "shoes",
                "fit": "low profile",
                "material": "leather",
                "colorName": "white",
                "color": "white",
                "formality": 3,
                "warmth": 1,
                "colors": ["#ffffff", "#dbeafe"],
            },
            {
                "name": "Navy Overshirt",
                "category": "jacket",
                "fit": "boxy",
                "material": "linen blend",
                "colorName": "navy",
                "color": "navy",
                "formality": 3,
                "warmth": 3,
                "colors": ["#1e3a8a", "#0f172a"],
            },
        ],
        "selected": ["White Oxford Shirt", "Stone Chinos", "White Trainers"],
        "stylists": [
            {
                "name": "Tami Looks",
                "specialty": "Smart casual · dates · brunch",
                "rating": 4.9,
                "helped": 214,
                "paid": True,
                "avatar": "linear-gradient(145deg,#7b4f38,#f3d2b2 58%,#1d2636 59%)",
            },
            {
                "name": "Kola Fits",
                "specialty": "Streetwear · concerts · campus",
                "rating": 4.8,
                "helped": 187,
                "paid": True,
                "avatar": "linear-gradient(145deg,#6e4635,#caa07b 55%,#233047 56%)",
            },
            {
                "name": "Ari Tailored",
                "specialty": "Weddings · formal · business",
                "rating": 4.7,
                "helped": 143,
                "paid": True,
                "avatar": "linear-gradient(145deg,#8a5f46,#e2b991 55%,#111827 56%)",
            },
            {
                "name": "Maya FreeFit",
                "specialty": "Budget wardrobe remix",
                "rating": 4.6,
                "helped": 91,
                "paid": False,
                "avatar": "linear-gradient(145deg,#8a583e,#d9a780 55%,#f7dce4 56%)",
            },
        ],
        "mall": [
            {
                "item": "Structured navy blazer",
                "category": "jacket",
                "store": "Metro Mall",
                "price": 78,
                "match": "Sharpens dinner fit",
                "bg": "linear-gradient(135deg,#081827,#0d2e55)",
                "wardrobeItem": {
                    "name": "Structured Navy Blazer",
                    "category": "jacket",
                    "fit": "structured",
                    "material": "woven wool blend",
                    "colorName": "navy",
                    "color": "navy",
                    "formality": 5,
                    "warmth": 3,
                    "colors": ["#081827", "#0d2e55"],
                },
            },
            {
                "item": "Minimal leather loafers",
                "category": "shoes",
                "store": "StyleHub",
                "price": 64,
                "match": "Upgrades footwear",
                "bg": "linear-gradient(135deg,#7a3f1f,#c87a3a)",
                "wardrobeItem": {
                    "name": "Minimal Leather Loafers",
                    "category": "shoes",
                    "fit": "low profile",
                    "material": "polished leather",
                    "colorName": "tan",
                    "color": "tan",
                    "formality": 4,
                    "warmth": 1,
                    "colors": ["#7a3f1f", "#c87a3a"],
                },
            },
            {
                "item": "Silver chain accessory",
                "category": "accessory",
                "store": "Urban Rack",
                "price": 22,
                "match": "Adds quiet detail",
                "bg": "linear-gradient(135deg,#e7edf5,#9ba9bb)",
                "wardrobeItem": {
                    "name": "Silver Chain Accessory",
                    "category": "accessory",
                    "fit": "one size",
                    "material": "stainless steel",
                    "colorName": "silver",
                    "color": "silver",
                    "formality": 3,
                    "warmth": 1,
                    "colors": ["#e7edf5", "#9ba9bb"],
                },
            },
        ],
        "styleRequests": [],
        "wishlistEvents": [],
        "posts": [
            {
                "author": "@tamilooks",
                "subject": "@ray",
                "caption": "Smart casual remix using wardrobe pieces plus one mall jacket. Saved as Friday dinner.",
                "likes": 248,
                "comments": 39,
                "saves": 18,
                "bookingRequests": 12,
            }
        ],
        "competitions": [
            {
                "name": "Weekend City Vibes",
                "prize": 60,
                "stylistsEntered": 8,
                "winnersAllowed": 2,
                "hoursLeft": 18,
            }
        ],
    }


class JsonStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            state = default_state()
            self.save(state)
            return state
        with self.path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def save(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2)
            handle.write("\n")
        temp_path.replace(self.path)

    def reset(self) -> dict[str, Any]:
        state = default_state()
        self.save(state)
        return state


class SwitchItUpBackend:
    def __init__(self, store: JsonStore) -> None:
        self.store = store

    def get_state(self) -> dict[str, Any]:
        return deepcopy(self.store.load())

    def reset(self) -> dict[str, Any]:
        return deepcopy(self.store.reset())

    def set_role(self, role: str) -> dict[str, Any]:
        if role not in VALID_ROLES:
            raise BackendError("role must be 'normal' or 'stylist'")
        state = self.store.load()
        state["profile"]["role"] = role
        self.store.save(state)
        return {"profile": state["profile"]}

    def add_wardrobe_item(self, payload: dict[str, Any]) -> dict[str, Any]:
        item = payload.get("item", payload)
        if not isinstance(item, dict):
            raise BackendError("wardrobe item must be an object")
        normalized = self._normalize_wardrobe_item(item)
        state = self.store.load()
        if any(existing["name"].lower() == normalized["name"].lower() for existing in state["wardrobe"]):
            raise BackendError(f"{normalized['name']} is already in the wardrobe", status=409)
        state["wardrobe"].append(normalized)
        self.store.save(state)
        return {"item": normalized, "wardrobe": state["wardrobe"]}

    def select_item(self, name: str) -> dict[str, Any]:
        if not name:
            raise BackendError("item name is required")
        state = self.store.load()
        item = self._find_wardrobe_item(state, name)
        selected = [
            selected_name
            for selected_name in state["selected"]
            if self._find_wardrobe_item(state, selected_name)["category"] != item["category"]
        ]
        selected.append(item["name"])
        state["selected"] = selected
        self.store.save(state)
        return {"selected": state["selected"]}

    def complete_scan(self, quality: int = 96) -> dict[str, Any]:
        state = self.store.load()
        state["profile"]["scan"] = {
            "status": "captured",
            "quality": max(1, min(100, int(quality))),
            "capturedAt": utc_now(),
        }
        self.store.save(state)
        return {"scan": state["profile"]["scan"]}

    def create_style_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        state = self.store.load()
        occasion = str(payload.get("occasion", "Smart casual dinner")).strip()
        budget = float(payload.get("budget", 0))
        replace_mode = str(payload.get("replaceMode", "some"))
        delivery = str(payload.get("delivery", "Within 24 hours"))
        paid_allowed = bool(payload.get("paidAllowed", True))
        target_formality = self._target_formality(occasion)
        open_to_replacements = replace_mode != "none"
        request = StyleRequest(
            occasion=occasion,
            target_formality=target_formality,
            weather="mild",
            budget=budget,
            open_to_replacements=open_to_replacements,
        )
        plan = build_style_plan(self._wardrobe_for_engine(state), sample_stylists(), request)
        selected_stylist = "Maya FreeFit" if replace_mode == "none" or not paid_allowed else plan.recommended_stylists[0]
        request_record = {
            "id": f"request_{len(state['styleRequests']) + 1:04d}",
            "createdAt": utc_now(),
            "occasion": occasion,
            "budget": budget,
            "replaceMode": replace_mode,
            "delivery": delivery,
            "paidAllowed": paid_allowed,
            "stylist": selected_stylist,
            "plan": {
                "outfitItems": list(plan.outfit_items),
                "missingCategories": list(plan.missing_categories),
                "replacementSuggestions": list(plan.replacement_suggestions),
                "recommendedStylists": list(plan.recommended_stylists),
                "confidencePercent": plan.confidence_percent,
            },
        }
        state["styleRequests"].append(request_record)
        if plan.outfit_items:
            state["selected"] = list(plan.outfit_items)
        self.store.save(state)
        action = {
            "all": "full outfit rebuild",
            "none": "wardrobe-only remix",
        }.get(replace_mode, "partial replacement")
        message = (
            f"{selected_stylist} received your {occasion.lower()} {action} request "
            f"with GBP {budget:g} budget. Delivery: {delivery.lower()}. "
            f"Backend style plan selected: {', '.join(plan.outfit_items)}."
        )
        return {
            "message": message,
            "request": request_record,
            "selected": state["selected"],
            "confidence": plan.confidence_percent,
        }

    def wishlist_action(self, item_name: str, action: str) -> dict[str, Any]:
        if action not in VALID_WISHLIST_ACTIONS:
            raise BackendError("wishlist action must be accept or discard")
        state = self.store.load()
        mall_item = next((item for item in state["mall"] if item["item"] == item_name), None)
        if not mall_item:
            raise BackendError(f"{item_name} is not in the mall wishlist", status=404)
        event = {
            "id": f"wishlist_{len(state['wishlistEvents']) + 1:04d}",
            "createdAt": utc_now(),
            "item": item_name,
            "action": action,
        }
        state["wishlistEvents"].append(event)
        if action == "accept":
            wardrobe_item = deepcopy(mall_item["wardrobeItem"])
            if not any(existing["name"].lower() == wardrobe_item["name"].lower() for existing in state["wardrobe"]):
                state["wardrobe"].append(wardrobe_item)
            message = (
                f"{item_name} accepted and saved to your wardrobe in the stylist's outfit order."
            )
        else:
            message = f"{item_name} discarded. Your stylist board was updated."
        self.store.save(state)
        return {
            "message": message,
            "event": event,
            "wardrobe": state["wardrobe"],
        }

    def _normalize_wardrobe_item(self, item: dict[str, Any]) -> dict[str, Any]:
        name = str(item.get("name", "")).strip()
        category = str(item.get("category", "")).strip()
        if not name:
            raise BackendError("wardrobe item name is required")
        if category not in {"top", "bottom", "shoes", "jacket", "accessory"}:
            raise BackendError("wardrobe item category is invalid")
        colors = item.get("colors") or ["#dbeafe", "#94a3b8"]
        if not isinstance(colors, list) or len(colors) < 2:
            raise BackendError("wardrobe item colors must include two values")
        formality = int(item.get("formality", 3))
        warmth = int(item.get("warmth", 1))
        if not 1 <= formality <= 5:
            raise BackendError("wardrobe item formality must be between 1 and 5")
        return {
            "name": name,
            "category": category,
            "fit": str(item.get("fit", "regular")),
            "material": str(item.get("material", "uploaded item")),
            "colorName": str(item.get("colorName", item.get("color", "custom"))),
            "color": str(item.get("color", item.get("colorName", "custom"))),
            "formality": formality,
            "warmth": warmth,
            "colors": colors[:2],
        }

    def _find_wardrobe_item(self, state: dict[str, Any], name: str) -> dict[str, Any]:
        item = next((entry for entry in state["wardrobe"] if entry["name"] == name), None)
        if not item:
            raise BackendError(f"{name} is not in the wardrobe", status=404)
        return item

    def _wardrobe_for_engine(self, state: dict[str, Any]) -> tuple[WardrobeItem, ...]:
        return tuple(
            WardrobeItem(
                name=item["name"],
                category=item["category"],
                color=item.get("color", item.get("colorName", "custom")),
                formality=int(item.get("formality", 3)),
                warmth=int(item.get("warmth", 1)),
            )
            for item in state["wardrobe"]
        )

    def _target_formality(self, occasion: str) -> int:
        text = occasion.lower()
        if any(word in text for word in ("wedding", "interview", "formal", "business")):
            return 5
        if any(word in text for word in ("dinner", "guest", "holiday")):
            return 4
        if any(word in text for word in ("concert", "campus", "street")):
            return 2
        return 3
