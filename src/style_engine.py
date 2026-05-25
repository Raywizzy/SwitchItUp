"""Rule-based outfit and stylist marketplace logic for the SwitchItUp MVP."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WardrobeItem:
    name: str
    category: str
    color: str
    formality: int
    warmth: int


@dataclass(frozen=True)
class Stylist:
    name: str
    specialty: str
    rating: float
    paid: bool
    helped_count: int


@dataclass(frozen=True)
class StyleRequest:
    occasion: str
    target_formality: int
    weather: str
    budget: float
    open_to_replacements: bool


@dataclass(frozen=True)
class StylePlan:
    outfit_items: tuple[str, ...]
    missing_categories: tuple[str, ...]
    replacement_suggestions: tuple[str, ...]
    recommended_stylists: tuple[str, ...]
    confidence_percent: float


REQUIRED_CATEGORIES = ("top", "bottom", "shoes")


def validate_wardrobe(items: tuple[WardrobeItem, ...]) -> None:
    if not items:
        raise ValueError("wardrobe must include at least one item")
    for item in items:
        if item.category not in {"top", "bottom", "shoes", "jacket", "accessory"}:
            raise ValueError(f"{item.name} has an invalid category")
        if not 1 <= item.formality <= 5:
            raise ValueError(f"{item.name} formality must be between 1 and 5")


def select_outfit(items: tuple[WardrobeItem, ...], request: StyleRequest) -> tuple[WardrobeItem, ...]:
    validate_wardrobe(items)
    selected: list[WardrobeItem] = []
    for category in REQUIRED_CATEGORIES:
        candidates = [item for item in items if item.category == category]
        if candidates:
            selected.append(
                min(candidates, key=lambda item: abs(item.formality - request.target_formality))
            )
    if request.weather == "cold":
        jackets = [item for item in items if item.category == "jacket"]
        if jackets:
            selected.append(max(jackets, key=lambda item: item.warmth))
    return tuple(selected)


def build_style_plan(
    items: tuple[WardrobeItem, ...],
    stylists: tuple[Stylist, ...],
    request: StyleRequest,
) -> StylePlan:
    outfit = select_outfit(items, request)
    present = {item.category for item in outfit}
    missing = tuple(category for category in REQUIRED_CATEGORIES if category not in present)
    replacements: list[str] = []
    if request.open_to_replacements:
        if "shoes" in missing:
            replacements.append("Add clean neutral trainers or loafers to complete the look.")
        if request.target_formality >= 4:
            replacements.append("Consider a structured jacket for a sharper occasion outfit.")
        if request.budget >= 80:
            replacements.append("Wishlist one premium statement piece from the mall.")
    ranked_stylists = sorted(
        stylists,
        key=lambda stylist: (request.occasion.lower() in stylist.specialty.lower(), stylist.rating, stylist.helped_count),
        reverse=True,
    )
    confidence = max(35, min(98, 55 + len(outfit) * 12 - len(missing) * 15))
    return StylePlan(
        outfit_items=tuple(item.name for item in outfit),
        missing_categories=missing,
        replacement_suggestions=tuple(replacements),
        recommended_stylists=tuple(stylist.name for stylist in ranked_stylists[:3]),
        confidence_percent=float(confidence),
    )


def sample_wardrobe() -> tuple[WardrobeItem, ...]:
    return (
        WardrobeItem("White Oxford Shirt", "top", "white", 4, 1),
        WardrobeItem("Black Relaxed Tee", "top", "black", 2, 1),
        WardrobeItem("Stone Chinos", "bottom", "stone", 4, 2),
        WardrobeItem("Dark Denim", "bottom", "indigo", 2, 2),
        WardrobeItem("White Trainers", "shoes", "white", 3, 1),
        WardrobeItem("Navy Overshirt", "jacket", "navy", 3, 3),
    )


def sample_stylists() -> tuple[Stylist, ...]:
    return (
        Stylist("Tami Looks", "smart casual, dates, brunch", 4.9, True, 214),
        Stylist("Kola Fits", "streetwear, concerts, campus", 4.8, True, 187),
        Stylist("Ari Tailored", "weddings, formal, business", 4.7, True, 143),
        Stylist("Maya FreeFit", "budget styling, wardrobe remix", 4.6, False, 91),
    )


def sample_request() -> StyleRequest:
    return StyleRequest("smart casual dinner", 4, "mild", 120, True)
