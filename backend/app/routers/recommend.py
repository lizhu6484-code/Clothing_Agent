from fastapi import APIRouter, HTTPException, Query

from app.db import get_conn
from app.models.schemas import (
    FreeRecommendRequest,
    ImageSearchRequest,
    RecommendRequest,
    UserProfile,
)
from app.services.imagesearch import search_images
from app.services.llm import (
    EmptyWardrobeError,
    LLMHallucinationError,
    LLMUnavailableError,
    generate_free_outfit,
    generate_outfit,
)
from app.services.qweather import WeatherUnavailableError, get_location_name, get_weather

router = APIRouter(prefix="/api/recommend", tags=["recommend"])


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


def _get_active_user_id() -> int:
    conn = get_conn()
    row = conn.execute("SELECT id FROM user_profile WHERE is_active = 1 LIMIT 1").fetchone()
    conn.close()
    return row["id"] if row else 1


@router.get("/weather")
def weather(lat: float = Query(...), lon: float = Query(...)):
    try:
        w = get_weather(lat, lon)
    except WeatherUnavailableError:
        raise HTTPException(503, detail={"error": "WEATHER_UNAVAILABLE"})
    result = w.model_dump()
    result["location"] = get_location_name(lat, lon)
    return result


@router.post("/images")
def search_outfit_images(req: ImageSearchRequest):
    results = search_images(req.keywords)
    return {"images": results}


@router.post("/free")
def recommend_free(req: FreeRecommendRequest):
    try:
        w = get_weather(req.lat, req.lon)
    except WeatherUnavailableError:
        raise HTTPException(503, detail={"error": "WEATHER_UNAVAILABLE"})

    try:
        response = generate_free_outfit(w, req, _load_profile())
    except LLMUnavailableError:
        raise HTTPException(503, detail={"error": "LLM_UNAVAILABLE"})

    return response.model_dump()


@router.post("")
def recommend(req: RecommendRequest):
    user_id = _get_active_user_id()
    conn = get_conn()
    try:
        rows = conn.execute("SELECT * FROM wardrobe_items WHERE user_id = ?", (user_id,)).fetchall()

        if not rows:
            raise HTTPException(400, detail={"error": "EMPTY_WARDROBE"})

        wardrobe = [
            {
                "id": r["id"],
                "name": r["name"],
                "type": r["type"],
                "color": r["color"],
                "formality": r["formality"],
            }
            for r in rows
        ]

        try:
            w = get_weather(req.lat, req.lon)
        except WeatherUnavailableError:
            raise HTTPException(503, detail={"error": "WEATHER_UNAVAILABLE"})

        try:
            response = generate_outfit(w, req, wardrobe, _load_profile())
        except EmptyWardrobeError:
            raise HTTPException(400, detail={"error": "EMPTY_WARDROBE"})
        except LLMUnavailableError:
            raise HTTPException(503, detail={"error": "LLM_UNAVAILABLE"})
        except LLMHallucinationError as e:
            raise HTTPException(502, detail={"error": "LLM_HALLUCINATION", "message": str(e)})

        return response.model_dump()
    finally:
        conn.close()
