"""Persistent backend service for the Switch It Up MVP.

The service intentionally uses the Python standard library so the backend can
run locally without installing packages. It stores demo app state in JSON and
reuses the rule-based style engine for outfit recommendations.
"""

from __future__ import annotations

import base64
import binascii
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from threading import RLock
from typing import Any, Protocol
from urllib import error as url_error
from urllib import parse, request
from uuid import uuid4

from src.style_engine import StyleRequest, WardrobeItem, build_style_plan, sample_stylists


VALID_ROLES = {"normal", "stylist"}
VALID_WISHLIST_ACTIONS = {"accept", "discard"}
VALID_WARDROBE_CATEGORIES = {"top", "bottom", "shoes", "jacket", "accessory"}
VALID_REPLACE_MODES = {"some", "all", "none"}
VALID_DELIVERIES = {"Within 24 hours", "Within 2 hours", "This weekend"}
VALID_STYLIST_PLANS = {"pro_monthly", "pro_annual", "founding_stylist"}
VALID_SOCIAL_ACTIONS = {"like", "save", "comment", "booking"}
VALID_FOLLOW_ACTIONS = {"follow", "unfollow"}
VALID_MALL_PLANS = {"starter", "pro", "enterprise"}
MAX_UPLOAD_BYTES = 6 * 1024 * 1024


class BackendError(ValueError):
    """Raised when an API request cannot be processed."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class StateStore(Protocol):
    def load(self) -> dict[str, Any]:
        ...

    def save(self, state: dict[str, Any]) -> None:
        ...

    def reset(self) -> dict[str, Any]:
        ...


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
                "photo": "assets/photos/white-shirt.jpg",
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
                "photo": "assets/photos/black-tee.jpg",
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
                "photo": "assets/photos/stone-chinos.jpg",
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
                "photo": "assets/photos/dark-denim.jpg",
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
                "photo": "assets/photos/white-trainers.jpg",
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
                "photo": "assets/photos/navy-overshirt.jpg",
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
                "photo": "assets/photos/blazer-portrait.jpg",
            },
            {
                "name": "Kola Fits",
                "specialty": "Streetwear · concerts · campus",
                "rating": 4.8,
                "helped": 187,
                "paid": True,
                "avatar": "linear-gradient(145deg,#6e4635,#caa07b 55%,#233047 56%)",
                "photo": "assets/photos/style-feed.jpg",
            },
            {
                "name": "Ari Tailored",
                "specialty": "Weddings · formal · business",
                "rating": 4.7,
                "helped": 143,
                "paid": True,
                "avatar": "linear-gradient(145deg,#8a5f46,#e2b991 55%,#111827 56%)",
                "photo": "assets/photos/avatar-model.jpg",
            },
            {
                "name": "Maya FreeFit",
                "specialty": "Budget wardrobe remix",
                "rating": 4.6,
                "helped": 91,
                "paid": False,
                "avatar": "linear-gradient(145deg,#8a583e,#d9a780 55%,#f7dce4 56%)",
                "photo": "assets/photos/black-tee.jpg",
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
                "photo": "assets/photos/mall-blazer.jpg",
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
                    "photo": "assets/photos/mall-blazer.jpg",
                },
            },
            {
                "item": "Minimal leather loafers",
                "category": "shoes",
                "store": "StyleHub",
                "price": 64,
                "match": "Upgrades footwear",
                "bg": "linear-gradient(135deg,#7a3f1f,#c87a3a)",
                "photo": "assets/photos/loafers.jpg",
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
                    "photo": "assets/photos/loafers.jpg",
                },
            },
            {
                "item": "Silver chain accessory",
                "category": "accessory",
                "store": "Urban Rack",
                "price": 22,
                "match": "Adds quiet detail",
                "bg": "linear-gradient(135deg,#e7edf5,#9ba9bb)",
                "photo": "assets/photos/style-feed.jpg",
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
                    "photo": "assets/photos/style-feed.jpg",
                },
            },
        ],
        "styleRequests": [],
        "wishlistEvents": [],
        "messages": [],
        "stylistApplications": [],
        "mallRegistrations": [],
        "competitionEntries": [],
        "followers": [],
        "postComments": [],
        "posts": [
            {
                "id": "post_0001",
                "author": "@tamilooks",
                "subject": "@ray",
                "caption": "Smart casual remix using wardrobe pieces plus one mall jacket. Saved as Friday dinner.",
                "likes": 248,
                "comments": 39,
                "saves": 18,
                "bookingRequests": 12,
                "photo": "assets/photos/style-feed.jpg",
            }
        ],
        "competitions": [
            {
                "id": "competition_0001",
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
        self._lock = RLock()

    def load(self) -> dict[str, Any]:
        with self._lock:
            if not self.path.exists():
                state = default_state()
                self.save(state)
                return state
            with self.path.open("r", encoding="utf-8") as handle:
                state = json.load(handle)
            migrated = merge_state_defaults(state)
            if migrated != state:
                self.save(migrated)
            return migrated

    def save(self, state: dict[str, Any]) -> None:
        with self._lock:
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


class SupabaseStateStore:
    """Persist the whole MVP state in a single Supabase/Postgres JSONB row."""

    def __init__(self, url: str, key: str, table: str = "switchitup_state", record_id: str = "production") -> None:
        if not url or not key:
            raise BackendError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
        self.url = url.rstrip("/")
        self.key = key
        self.table = table
        self.record_id = record_id
        self._lock = RLock()

    def load(self) -> dict[str, Any]:
        with self._lock:
            rows = self._request(
                "GET",
                f"/rest/v1/{parse.quote(self.table)}"
                f"?id=eq.{parse.quote(self.record_id, safe='')}&select=state",
            )
            if not rows:
                state = default_state()
                self.save(state)
                return state
            state = rows[0].get("state") or {}
            migrated = merge_state_defaults(state)
            if migrated != state:
                self.save(migrated)
            return migrated

    def save(self, state: dict[str, Any]) -> None:
        with self._lock:
            self._request(
                "POST",
                f"/rest/v1/{parse.quote(self.table)}?on_conflict=id",
                [
                    {
                        "id": self.record_id,
                        "state": state,
                        "updated_at": utc_now(),
                    }
                ],
                {"Prefer": "resolution=merge-duplicates,return=representation"},
            )

    def reset(self) -> dict[str, Any]:
        state = default_state()
        self.save(state)
        return state

    def _request(
        self,
        method: str,
        path: str,
        payload: Any | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            **(extra_headers or {}),
        }
        req = request.Request(f"{self.url}{path}", data=body, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=10) as response:
                raw = response.read().decode("utf-8")
        except url_error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise BackendError(f"Supabase request failed ({exc.code}): {detail[:240]}", status=502) from exc
        except url_error.URLError as exc:
            raise BackendError(f"Supabase request failed: {exc.reason}", status=502) from exc
        return json.loads(raw) if raw else None


def merge_state_defaults(state: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(default_state())
    deep_update(merged, state)
    for index, post in enumerate(merged.get("posts", []), start=1):
        post.setdefault("id", f"post_{index:04d}")
    for index, competition in enumerate(merged.get("competitions", []), start=1):
        competition.setdefault("id", f"competition_{index:04d}")
    return merged


def deep_update(base: dict[str, Any], override: dict[str, Any]) -> None:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_update(base[key], value)
        else:
            base[key] = value


class SwitchItUpBackend:
    def __init__(self, store: StateStore) -> None:
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

    def update_measurements(self, payload: dict[str, Any]) -> dict[str, Any]:
        state = self.store.load()
        current = dict(state["profile"].get("measurements", {}))
        if "heightCm" in payload:
            current["heightCm"] = self._int_range(payload["heightCm"], "heightCm", 90, 230)
        if "waistIn" in payload:
            current["waistIn"] = self._int_range(payload["waistIn"], "waistIn", 20, 60)
        if "topSize" in payload:
            current["topSize"] = self._text(payload["topSize"], "topSize", min_len=1, max_len=12)
        if "shoeSize" in payload:
            current["shoeSize"] = self._text(payload["shoeSize"], "shoeSize", min_len=1, max_len=16)
        state["profile"]["measurements"] = current
        self.store.save(state)
        return {"profile": state["profile"]}

    def upgrade_stylist_account(self, payload: dict[str, Any]) -> dict[str, Any]:
        specialty = self._text(payload.get("specialty", "Personal styling"), "specialty", min_len=3, max_len=90)
        plan = str(payload.get("plan", "pro_monthly"))
        if plan not in VALID_STYLIST_PLANS:
            raise BackendError("stylist plan is invalid")
        state = self.store.load()
        state["profile"]["role"] = "stylist"
        application = next(
            (
                entry
                for entry in state["stylistApplications"]
                if entry.get("accountId") == state["profile"]["id"] and entry.get("status") == "active"
            ),
            None,
        )
        if application:
            application.update(
                {
                    "updatedAt": utc_now(),
                    "specialty": specialty,
                    "plan": plan,
                    "paymentReference": str(payload.get("paymentReference", application.get("paymentReference", "")))[:80],
                }
            )
        else:
            application = {
                "id": self._next_id(state["stylistApplications"], "stylist_application"),
                "createdAt": utc_now(),
                "accountId": state["profile"]["id"],
                "specialty": specialty,
                "plan": plan,
                "status": "active",
                "paymentStatus": "required",
                "paymentReference": str(payload.get("paymentReference", "demo_checkout_pending"))[:80],
            }
            state["stylistApplications"].append(application)
        marketplace_name = state["profile"]["name"]
        marketplace_stylist = next(
            (stylist for stylist in state["stylists"] if stylist["name"].lower() == marketplace_name.lower()),
            None,
        )
        if marketplace_stylist:
            marketplace_stylist["specialty"] = specialty
            marketplace_stylist["paid"] = True
        else:
            state["stylists"].append(
                {
                    "name": marketplace_name,
                    "specialty": specialty,
                    "rating": 5.0,
                    "helped": 0,
                    "paid": True,
                    "avatar": "linear-gradient(145deg,#111827,#4b5563 55%,#dbeafe 56%)",
                    "photo": "assets/photos/avatar-model.jpg",
                }
            )
        self.store.save(state)
        return {"profile": state["profile"], "application": application, "stylists": state["stylists"]}

    def add_wardrobe_item(self, payload: dict[str, Any]) -> dict[str, Any]:
        item = payload.get("item", payload)
        if not isinstance(item, dict):
            raise BackendError("wardrobe item must be an object")
        item = dict(item)
        photo_data = item.pop("photoData", None)
        if photo_data:
            item["photo"] = self._save_uploaded_photo(str(photo_data), str(item.get("photoName", item.get("name", "wardrobe"))))
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
        occasion = self._text(payload.get("occasion", "Smart casual dinner"), "occasion", min_len=3, max_len=80)
        budget = self._float_range(payload.get("budget", 0), "budget", 0, 10000)
        replace_mode = str(payload.get("replaceMode", "some"))
        if replace_mode not in VALID_REPLACE_MODES:
            raise BackendError("replaceMode must be some, all, or none")
        delivery = str(payload.get("delivery", "Within 24 hours"))
        if delivery not in VALID_DELIVERIES:
            raise BackendError("delivery option is invalid")
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

    def create_post(self, payload: dict[str, Any]) -> dict[str, Any]:
        state = self.store.load()
        caption = self._text(payload.get("caption", ""), "caption", min_len=3, max_len=280)
        author = str(payload.get("author") or f"@{state['profile']['name'].lower()}").strip()[:40]
        post = {
            "id": self._next_id(state["posts"], "post"),
            "createdAt": utc_now(),
            "author": author,
            "subject": str(payload.get("subject", "@ray"))[:40],
            "caption": caption,
            "likes": 0,
            "comments": 0,
            "saves": 0,
            "bookingRequests": 0,
            "photo": str(payload.get("photo", "assets/photos/style-feed.jpg"))[:160],
        }
        state["posts"].insert(0, post)
        self.store.save(state)
        return {"post": post, "posts": state["posts"]}

    def react_to_post(self, payload: dict[str, Any]) -> dict[str, Any]:
        action = str(payload.get("action", ""))
        if action not in VALID_SOCIAL_ACTIONS:
            raise BackendError("social action must be like, save, comment, or booking")
        state = self.store.load()
        post = self._find_post(state, str(payload.get("postId", "")))
        comment = None
        if action == "comment":
            text = self._text(payload.get("text", ""), "comment text", min_len=1, max_len=240)
            post["comments"] = int(post.get("comments", 0)) + 1
            comment = {
                "id": self._next_id(state["postComments"], "comment"),
                "postId": post["id"],
                "author": str(payload.get("author", "@ray"))[:40],
                "text": text,
                "createdAt": utc_now(),
            }
            state["postComments"].append(comment)
        elif action == "like":
            post["likes"] = int(post.get("likes", 0)) + 1
        elif action == "save":
            post["saves"] = int(post.get("saves", 0)) + 1
        elif action == "booking":
            post["bookingRequests"] = int(post.get("bookingRequests", 0)) + 1
        self.store.save(state)
        return {"post": post, "comment": comment}

    def send_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        recipient = self._text(payload.get("to", ""), "message recipient", min_len=2, max_len=80)
        text = self._text(payload.get("text", ""), "message text", min_len=1, max_len=1000)
        state = self.store.load()
        message = {
            "id": self._next_id(state["messages"], "message"),
            "createdAt": utc_now(),
            "from": str(payload.get("from", "@ray"))[:40],
            "to": recipient,
            "text": text,
            "requestId": str(payload.get("requestId", ""))[:80],
            "read": False,
        }
        state["messages"].append(message)
        self.store.save(state)
        return {"message": message, "messages": state["messages"]}

    def register_mall(self, payload: dict[str, Any]) -> dict[str, Any]:
        company_name = self._text(payload.get("companyName", ""), "companyName", min_len=2, max_len=90)
        contact_email = self._email(payload.get("contactEmail", ""))
        plan = str(payload.get("plan", "starter"))
        if plan not in VALID_MALL_PLANS:
            raise BackendError("mall registration plan is invalid")
        state = self.store.load()
        registration = {
            "id": self._next_id(state["mallRegistrations"], "mall_registration"),
            "createdAt": utc_now(),
            "companyName": company_name,
            "contactEmail": contact_email,
            "plan": plan,
            "status": "pending_verification",
            "paymentStatus": "required",
        }
        state["mallRegistrations"].append(registration)
        self.store.save(state)
        return {"registration": registration}

    def create_competition(self, payload: dict[str, Any]) -> dict[str, Any]:
        state = self.store.load()
        competition = {
            "id": self._next_id(state["competitions"], "competition"),
            "createdAt": utc_now(),
            "name": self._text(payload.get("name", "New styling challenge"), "competition name", min_len=3, max_len=80),
            "prize": self._float_range(payload.get("prize", 0), "prize", 1, 10000),
            "stylistsEntered": 0,
            "winnersAllowed": self._int_range(payload.get("winnersAllowed", 1), "winnersAllowed", 1, 5),
            "hoursLeft": self._int_range(payload.get("hoursLeft", 24), "hoursLeft", 1, 336),
        }
        state["competitions"].insert(0, competition)
        self.store.save(state)
        return {"competition": competition, "competitions": state["competitions"]}

    def submit_competition_entry(self, payload: dict[str, Any]) -> dict[str, Any]:
        state = self.store.load()
        competition = self._find_competition(state, str(payload.get("competitionId", "")))
        stylist_name = self._text(payload.get("stylistName", ""), "stylistName", min_len=2, max_len=80)
        outfit_items = payload.get("outfitItems", state["selected"])
        if not isinstance(outfit_items, list) or not outfit_items:
            raise BackendError("outfitItems must be a non-empty list")
        known = {item["name"] for item in state["wardrobe"]}
        missing = [name for name in outfit_items if name not in known]
        if missing:
            raise BackendError(f"competition outfit contains unknown wardrobe items: {', '.join(missing)}")
        entry = {
            "id": self._next_id(state["competitionEntries"], "competition_entry"),
            "createdAt": utc_now(),
            "competitionId": competition["id"],
            "stylistName": stylist_name,
            "outfitItems": list(outfit_items),
            "status": "submitted",
        }
        already_entered = any(
            existing["competitionId"] == competition["id"] and existing["stylistName"].lower() == stylist_name.lower()
            for existing in state["competitionEntries"]
        )
        if not already_entered:
            competition["stylistsEntered"] = int(competition.get("stylistsEntered", 0)) + 1
        state["competitionEntries"].append(entry)
        self.store.save(state)
        return {"entry": entry, "competition": competition}

    def follow_stylist(self, payload: dict[str, Any]) -> dict[str, Any]:
        action = str(payload.get("action", "follow"))
        if action not in VALID_FOLLOW_ACTIONS:
            raise BackendError("follow action must be follow or unfollow")
        stylist_name = self._text(payload.get("stylistName", ""), "stylistName", min_len=2, max_len=80)
        state = self.store.load()
        if not any(stylist["name"].lower() == stylist_name.lower() for stylist in state["stylists"]):
            raise BackendError(f"{stylist_name} is not in the stylist marketplace", status=404)
        account_id = state["profile"]["id"]
        state["followers"] = [
            follow
            for follow in state["followers"]
            if not (follow["accountId"] == account_id and follow["stylistName"].lower() == stylist_name.lower())
        ]
        if action == "follow":
            state["followers"].append(
                {
                    "id": self._next_id(state["followers"], "follow"),
                    "createdAt": utc_now(),
                    "accountId": account_id,
                    "stylistName": stylist_name,
                }
            )
        self.store.save(state)
        return {"followers": state["followers"]}

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
        if category not in VALID_WARDROBE_CATEGORIES:
            raise BackendError("wardrobe item category is invalid")
        colors = item.get("colors") or ["#dbeafe", "#94a3b8"]
        if not isinstance(colors, list) or len(colors) < 2:
            raise BackendError("wardrobe item colors must include two values")
        if not all(isinstance(color, str) and re.match(r"^#[0-9a-fA-F]{6}$", color) for color in colors[:2]):
            raise BackendError("wardrobe item colors must be hex values")
        formality = int(item.get("formality", 3))
        warmth = int(item.get("warmth", 1))
        if not 1 <= formality <= 5:
            raise BackendError("wardrobe item formality must be between 1 and 5")
        if not 1 <= warmth <= 5:
            raise BackendError("wardrobe item warmth must be between 1 and 5")
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
            "photo": str(item.get("photo", "assets/photos/style-feed.jpg")),
        }

    def _save_uploaded_photo(self, data_url: str, source_name: str) -> str:
        match = re.match(r"^data:(image/(png|jpeg|jpg|webp));base64,(.+)$", data_url)
        if not match:
            raise BackendError("uploaded photo must be a PNG, JPEG, or WebP data URL")
        extension = "jpg" if match.group(2) in {"jpeg", "jpg"} else match.group(2)
        try:
            raw = base64.b64decode(match.group(3), validate=True)
        except binascii.Error as exc:
            raise BackendError("uploaded photo data is not valid base64") from exc
        if len(raw) > MAX_UPLOAD_BYTES:
            raise BackendError("uploaded photo must be 6MB or smaller")
        self._validate_image_signature(raw, extension)
        store_path = getattr(self.store, "path", None)
        if store_path is None:
            return data_url
        safe_stem = re.sub(r"[^a-zA-Z0-9]+", "-", Path(source_name).stem).strip("-").lower() or "wardrobe"
        filename = f"{safe_stem}-{uuid4().hex[:10]}.{extension}"
        upload_dir = Path(store_path).parent / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        upload_path = upload_dir / filename
        upload_path.write_bytes(raw)
        return f"data/uploads/{filename}"

    def _find_wardrobe_item(self, state: dict[str, Any], name: str) -> dict[str, Any]:
        item = next((entry for entry in state["wardrobe"] if entry["name"] == name), None)
        if not item:
            raise BackendError(f"{name} is not in the wardrobe", status=404)
        return item

    def _find_post(self, state: dict[str, Any], post_id: str) -> dict[str, Any]:
        post = next((entry for entry in state["posts"] if entry.get("id") == post_id), None)
        if not post:
            raise BackendError(f"{post_id} is not in the style feed", status=404)
        return post

    def _find_competition(self, state: dict[str, Any], competition_id: str) -> dict[str, Any]:
        competition = next(
            (
                entry
                for entry in state["competitions"]
                if entry.get("id") == competition_id or entry.get("name") == competition_id
            ),
            None,
        )
        if not competition:
            raise BackendError(f"{competition_id} is not an active competition", status=404)
        return competition

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

    def _next_id(self, records: list[dict[str, Any]], prefix: str) -> str:
        highest = 0
        for record in records:
            match = re.match(rf"^{re.escape(prefix)}_(\d+)$", str(record.get("id", "")))
            if match:
                highest = max(highest, int(match.group(1)))
        return f"{prefix}_{highest + 1:04d}"

    def _text(self, value: Any, field: str, min_len: int, max_len: int) -> str:
        text = str(value or "").strip()
        if len(text) < min_len:
            raise BackendError(f"{field} is required")
        if len(text) > max_len:
            raise BackendError(f"{field} must be {max_len} characters or fewer")
        return text

    def _email(self, value: Any) -> str:
        email = self._text(value, "contactEmail", min_len=5, max_len=120)
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise BackendError("contactEmail must be a valid email address")
        return email

    def _int_range(self, value: Any, field: str, minimum: int, maximum: int) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise BackendError(f"{field} must be a number") from exc
        if not minimum <= number <= maximum:
            raise BackendError(f"{field} must be between {minimum} and {maximum}")
        return number

    def _float_range(self, value: Any, field: str, minimum: float, maximum: float) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise BackendError(f"{field} must be a number") from exc
        if not minimum <= number <= maximum:
            raise BackendError(f"{field} must be between {minimum:g} and {maximum:g}")
        return number

    def _validate_image_signature(self, raw: bytes, extension: str) -> None:
        if extension == "png" and raw.startswith(b"\x89PNG\r\n\x1a\n"):
            return
        if extension == "jpg" and raw.startswith(b"\xff\xd8\xff"):
            return
        if extension == "webp" and len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
            return
        raise BackendError("uploaded photo content does not match its image type")
