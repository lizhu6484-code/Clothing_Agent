"""线上购衣推荐路由：LLM 方案 + 拼多多商品搜索。"""

import uuid

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models.schemas import (
    PurchaseRecommendRequest,
    PurchaseRecommendResponse,
    UserProfile,
)
from app.services.llm import (
    SCOPE_NAMES,
    LLMUnavailableError,
    generate_outfit_plan,
)
from app.services.pdd_search import PddSearchClient, PddSearchError
from app.db import get_conn

router = APIRouter(prefix="/api/purchase", tags=["purchase"])

PRODUCTS_PER_CATEGORY = 10


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


@router.post("/recommend")
def create_recommendation(request: PurchaseRecommendRequest):
    # 读取当前激活用户
    profile = _load_profile()

    # Step 1: LLM 生成穿搭方案
    try:
        plan = generate_outfit_plan(request, profile)
    except LLMUnavailableError as exc:
        raise HTTPException(503, detail={"error": "LLM_UNAVAILABLE", "message": str(exc)})

    # Step 2: PDD 搜索商品
    pdd_client = PddSearchClient(
        client_id=settings.PDD_CLIENT_ID,
        client_secret=settings.PDD_CLIENT_SECRET,
        pid=settings.PDD_PID,
    )

    products_by_category: dict[str, list] = {}
    for item in plan.items:
        try:
            products = pdd_client.search(item.search_keyword, count=PRODUCTS_PER_CATEGORY)
            products_by_category[item.category] = [p.model_dump() for p in products]
        except PddSearchError:
            products_by_category[item.category] = []

    # 构建摘要
    gender_cn = profile.gender if profile else ""
    summary = (
        f"适合{gender_cn}的{request.scene or '日常'}"
        f"{SCOPE_NAMES[request.purchase_scope]}穿搭方案"
    )

    return PurchaseRecommendResponse(
        run_id=str(uuid.uuid4()),
        summary=summary,
        outfit_plan=plan,
        products_by_category=products_by_category,
    ).model_dump()
