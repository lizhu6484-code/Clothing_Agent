"""线下购衣推荐路由。"""

from fastapi import APIRouter, HTTPException

from app.models.schemas import OfflineShoppingRequest, StoreInfo, UserProfile
from app.services.baidu_map import BaiduMapUnavailableError, search_nearby_stores
from app.services.llm import LLMUnavailableError, generate_shopping_advice
from app.services.qweather import WeatherUnavailableError, get_weather
from app.db import get_conn

router = APIRouter(prefix="/api/shopping", tags=["shopping"])


def _load_profile() -> UserProfile | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM user_profile WHERE is_active = 1 LIMIT 1").fetchone()
    conn.close()
    if not row:
        return None
    return UserProfile(
        id=row["id"],
        name=row["name"],
        gender=row["gender"],
        height_cm=row["height_cm"],
        weight_kg=row["weight_kg"],
        age=row["age"],
        notes=row["notes"],
        is_active=True,
    )


@router.post("/offline")
def offline_shopping(req: OfflineShoppingRequest):
    try:
        weather = get_weather(req.lat, req.lon)
    except WeatherUnavailableError:
        raise HTTPException(503, detail={"error": "WEATHER_UNAVAILABLE"})

    try:
        response = generate_shopping_advice(weather, req, _load_profile())
    except LLMUnavailableError:
        raise HTTPException(503, detail={"error": "LLM_UNAVAILABLE"})

    try:
        raw_stores = search_nearby_stores(req.lat, req.lon)
        response.stores = [StoreInfo(**s) for s in raw_stores]
    except BaiduMapUnavailableError:
        pass

    return response.model_dump()
