"""Unified Pydantic schemas for the merged demo app."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


# ── User Profile ──────────────────────────────────────────────


class UserProfile(BaseModel):
    id: int | None = None
    name: str = ""
    gender: str = ""
    height_cm: float | None = None
    weight_kg: float | None = None
    age: int | None = None
    notes: str = ""
    is_active: bool = False
    updated_at: str | None = None


# ── Wardrobe ──────────────────────────────────────────────────


class WardrobeItem(BaseModel):
    id: int | None = None
    user_id: int = 1
    image_path: str = ""
    image_hash: str = ""
    name: str = ""
    type: str = ""
    category: str = ""
    color: str = ""
    material: str | None = None
    season: list[str] = []
    formality: int = Field(ge=1, le=5, default=3)
    style: list[str] = []
    features: list[str] = []
    created_at: str | None = None


class WardrobeItemCreate(BaseModel):
    name: str
    type: str
    category: str = ""
    color: str = ""
    material: str | None = None
    season: list[str] = []
    formality: int = Field(ge=1, le=5, default=3)
    style: list[str] = []
    features: list[str] = []


# ── Weather ───────────────────────────────────────────────────


class Weather(BaseModel):
    temp: int
    text: str
    humidity: int
    wind: str


# ── Outfit Recommend (wardrobe-based) ─────────────────────────


class RecommendRequest(BaseModel):
    lat: float
    lon: float
    occasion: str
    purpose: str = ""
    preferences: str = ""


class OutfitSlot(BaseModel):
    wardrobe_id: int | None = None
    name: str = ""


class Outfit(BaseModel):
    summary: str
    top: OutfitSlot | None = None
    bottom: OutfitSlot | None = None
    shoes: OutfitSlot | None = None
    reason: str
    formality_match: int = Field(ge=1, le=5)


class RecommendResponse(BaseModel):
    request_id: str
    weather: Weather
    outfits: list[Outfit]
    fallback_tips: str = ""


# ── Free Recommend ────────────────────────────────────────────


class FreeRecommendRequest(BaseModel):
    lat: float
    lon: float
    occasion: str
    purpose: str = ""
    preferences: str = ""


class FreeOutfit(BaseModel):
    summary: str
    top: str = ""
    bottom: str = ""
    shoes: str = ""
    reason: str


class FreeRecommendResponse(BaseModel):
    weather: Weather
    outfits: list[FreeOutfit]
    tips: str = ""


# ── Image Search (配图集) ─────────────────────────────────────


class ImageSearchRequest(BaseModel):
    keywords: list[str] = []


# ── Online Purchase (线上购衣) ────────────────────────────────

PurchaseScope = Literal["top", "bottom", "shoes", "top_bottom", "full"]


class PurchaseRecommendRequest(BaseModel):
    purchase_scope: PurchaseScope
    scene: str = ""
    budget: float | None = Field(default=None, gt=0)
    budget_top: float | None = Field(default=None, gt=0)
    budget_bottom: float | None = Field(default=None, gt=0)
    budget_shoes: float | None = Field(default=None, gt=0)
    budget_mode: Literal["average", "custom"] = "average"
    style: str = ""
    other: str = ""

    @model_validator(mode="after")
    def at_least_one_requirement(self) -> "PurchaseRecommendRequest":
        if not any([
            self.scene.strip(),
            self.budget is not None,
            self.budget_top is not None,
            self.budget_bottom is not None,
            self.budget_shoes is not None,
            self.style.strip(),
            self.other.strip(),
        ]):
            raise ValueError("scene, budget, style, other 等字段不能全部为空")
        return self


class OutfitItem(BaseModel):
    category: Literal["top", "bottom", "shoes"]
    name: str
    description: str
    role: str
    search_keyword: str


class OutfitPlan(BaseModel):
    summary: str
    items: list[OutfitItem]


class PddProduct(BaseModel):
    goods_name: str
    min_group_price: int
    min_normal_price: int
    coupon_discount: int = 0
    sales_tip: str = ""
    promotion_rate: int = 0
    goods_image_url: str = ""
    unified_tags: list[str] = Field(default_factory=list)


class PurchaseRecommendResponse(BaseModel):
    run_id: str
    summary: str
    outfit_plan: OutfitPlan
    products_by_category: dict[str, list[PddProduct]]
    status: str = "success"
    created_at: str = ""


# ── Offline Shopping (线下购衣) ───────────────────────────────


class OfflineShoppingRequest(BaseModel):
    lat: float
    lon: float
    need: str = ""
    occasion: str = ""
    budget: str = ""
    preferences: str = ""


class ShoppingItem(BaseModel):
    item: str
    reason: str
    tips: str = ""


class StoreInfo(BaseModel):
    name: str
    address: str
    phone: str = ""
    tags: str = ""
    rating: str = ""
    lat: float = 0.0
    lon: float = 0.0


class OfflineShoppingResponse(BaseModel):
    weather: Weather
    shopping_list: list[ShoppingItem]
    stores: list[StoreInfo]
    advice: str
