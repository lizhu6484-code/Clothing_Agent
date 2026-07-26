"""Unified LLM service: outfit recommend + free recommend + shopping advice + purchase plan."""

import json
import uuid

from openai import OpenAI

from app.config import settings
from app.models.schemas import (
    FreeOutfit,
    FreeRecommendRequest,
    FreeRecommendResponse,
    OfflineShoppingRequest,
    OfflineShoppingResponse,
    Outfit,
    OutfitItem,
    OutfitPlan,
    OutfitSlot,
    PurchaseRecommendRequest,
    RecommendRequest,
    RecommendResponse,
    ShoppingItem,
    UserProfile,
    Weather,
)

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.SENSENOVA_API_KEY,
            base_url=settings.SENSENOVA_BASE_URL,
        )
    return _client


SYSTEM_PROMPT = "你是一个专业又亲切的穿搭顾问，像朋友一样聊天。用口语化中文，结合天气、场景、使用者自身条件和衣橱给出搭配，说话有温度，不刻板，建议实在不虚浮。"


def _profile_text(profile: UserProfile | None) -> str:
    if not profile:
        return "使用者信息：未填写"
    parts = []
    if profile.name:
        parts.append(profile.name)
    if profile.gender:
        parts.append(profile.gender)
    if profile.height_cm:
        parts.append(f"身高{profile.height_cm:g}cm")
    if profile.weight_kg:
        parts.append(f"体重{profile.weight_kg:g}kg")
    if profile.age:
        parts.append(f"{profile.age}岁")
    if profile.notes:
        parts.append(profile.notes)
    if not parts:
        return "使用者信息：未填写"
    return "使用者信息：" + "，".join(parts)


class EmptyWardrobeError(Exception):
    pass


class LLMUnavailableError(Exception):
    pass


class LLMHallucinationError(Exception):
    pass


def _parse_llm_json(resp) -> dict:
    try:
        content = resp.choices[0].message.content
    except (IndexError, AttributeError) as e:
        raise LLMUnavailableError(f"LLM response malformed: {e}") from e

    if not content:
        raise LLMUnavailableError("LLM returned empty content")

    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise LLMUnavailableError(f"LLM returned invalid JSON: {e}") from e


# ── 衣柜推荐 ──────────────────────────────────────────────────


def generate_outfit(weather: Weather, request: RecommendRequest, wardrobe: list[dict], profile: UserProfile | None = None) -> RecommendResponse:
    if not wardrobe:
        raise EmptyWardrobeError("Wardrobe is empty")

    valid_ids = {item["id"] for item in wardrobe}
    id_to_name = {item["id"]: item["name"] for item in wardrobe}

    wardrobe_text = "\n".join(
        f"- id={item['id']} | {item['name']} | {item['type']} | {item['color']} | formality={item['formality']}"
        for item in wardrobe
    )

    user_prompt = f"""当前天气：{weather.temp}℃，{weather.text}，湿度{weather.humidity}%，{weather.wind}

{_profile_text(profile)}

出行场景：{request.occasion}
目的：{request.purpose or '无特别说明'}

用户偏好：{request.preferences or '无'}

衣橱清单：
{wardrobe_text}

请从上述衣橱中选择搭配，每套包含上装、下装、鞋子各一件（填对应 id），输出 JSON：
{{"outfits": [{{"summary": "...", "top": 1, "bottom": 2, "shoes": 3, "reason": "...", "formality_match": 3}}], "fallback_tips": "..."}}

要求：
- 至少 2 套方案
- top/bottom/shoes 必须是衣橱清单里真实存在的 id；若衣橱里确实没有合适的某一类，该字段填 null
- reason 要用口语化中文，像朋友给出建议一样自然，同时提到天气适配和场景适配，并结合使用者身材条件
- 若衣橱里没有合适单品，写到 fallback_tips，语气像朋友支招"""

    try:
        resp = _get_client().chat.completions.create(
            model=settings.SENSENOVA_LLM_MODEL,
            temperature=0.7,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as e:
        raise LLMUnavailableError(f"LLM request failed: {e}") from e

    result = _parse_llm_json(resp)

    def _slot(v) -> OutfitSlot | None:
        if v is None:
            return None
        if v not in valid_ids:
            raise LLMHallucinationError(f"wardrobe_id {v} not in wardrobe")
        return OutfitSlot(wardrobe_id=v, name=id_to_name[v])

    outfits = []
    for o in result.get("outfits", []):
        outfits.append(Outfit(
            summary=o.get("summary", ""),
            top=_slot(o.get("top")),
            bottom=_slot(o.get("bottom")),
            shoes=_slot(o.get("shoes")),
            reason=o.get("reason", ""),
            formality_match=o.get("formality_match", 3),
        ))

    return RecommendResponse(
        request_id=str(uuid.uuid4()),
        weather=weather,
        outfits=outfits,
        fallback_tips=result.get("fallback_tips", ""),
    )


# ── 自由推荐 ──────────────────────────────────────────────────


def generate_free_outfit(weather: Weather, request: FreeRecommendRequest, profile: UserProfile | None = None) -> FreeRecommendResponse:
    user_prompt = f"""当前天气：{weather.temp}℃，{weather.text}，湿度{weather.humidity}%，{weather.wind}

{_profile_text(profile)}

出行场景：{request.occasion}
目的：{request.purpose or '无特别说明'}
用户偏好：{request.preferences or '无'}

请直接给出穿搭建议（不需要从特定衣橱选），每套包含上装、下装、鞋子，输出 JSON：
{{"outfits": [{{"summary": "...", "top": "上装单品及建议", "bottom": "下装单品及建议", "shoes": "鞋子单品及建议", "reason": "..."}}], "tips": "额外小贴士"}}

要求：
- 至少 2 套方案
- top/bottom/shoes 各给出具体单品建议（如"白色圆领短袖T恤"），补充颜色/面料/版型等选购要点
- reason 要用口语化中文，像朋友聊天一样自然，同时提到天气适配和场景适配，并结合使用者身材条件
- tips 像朋友提醒注意事项（如防晒、带伞等），口语化"""

    try:
        resp = _get_client().chat.completions.create(
            model=settings.SENSENOVA_LLM_MODEL,
            temperature=0.7,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as e:
        raise LLMUnavailableError(f"LLM request failed: {e}") from e

    result = _parse_llm_json(resp)

    outfits = []
    for o in result.get("outfits", []):
        outfits.append(FreeOutfit(
            summary=o.get("summary", ""),
            top=o.get("top", ""),
            bottom=o.get("bottom", ""),
            shoes=o.get("shoes", ""),
            reason=o.get("reason", ""),
        ))

    return FreeRecommendResponse(
        weather=weather,
        outfits=outfits,
        tips=result.get("tips", ""),
    )


# ── 线下购衣建议 ──────────────────────────────────────────────


def generate_shopping_advice(
    weather: Weather,
    request: OfflineShoppingRequest,
    profile: UserProfile | None = None,
) -> OfflineShoppingResponse:
    user_prompt = f"""当前天气：{weather.temp}℃，{weather.text}，湿度{weather.humidity}%，{weather.wind}

{_profile_text(profile)}

购衣需求：{request.need or '没有明确需求，根据天气和场景推荐'}
出行场景：{request.occasion or '日常'}
预算：{request.budget or '不限'}
偏好：{request.preferences or '无'}

请给出线下购衣建议，输出 JSON：
{{"shopping_list": [{{"item": "具体单品名称", "reason": "为什么买", "tips": "选购要点（面料/版型/颜色/价格区间等）"}}], "advice": "整体购衣建议，像朋友聊天一样自然，2-4句话，包含去哪类店铺、怎么挑、注意什么"}}

要求：
- shopping_list 至少 2 项、最多 5 项
- item 要具体（如"浅蓝色直筒牛仔裤"而非"裤子"）
- tips 要实用，包含面料/版型/颜色/价格参考
- advice 用口语化中文，像朋友陪逛街时给的建议
- 结合天气和使用者身材条件"""

    try:
        resp = _get_client().chat.completions.create(
            model=settings.SENSENOVA_LLM_MODEL,
            temperature=0.7,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as e:
        raise LLMUnavailableError(f"LLM request failed: {e}") from e

    result = _parse_llm_json(resp)

    shopping_list = [
        ShoppingItem(
            item=s.get("item", ""),
            reason=s.get("reason", ""),
            tips=s.get("tips", ""),
        )
        for s in result.get("shopping_list", [])
    ]

    return OfflineShoppingResponse(
        weather=weather,
        shopping_list=shopping_list,
        stores=[],
        advice=result.get("advice", ""),
    )


# ── 线上购衣方案生成 ──────────────────────────────────────────

SCOPE_CATEGORIES: dict[str, list[str]] = {
    "top": ["top"],
    "bottom": ["bottom"],
    "shoes": ["shoes"],
    "top_bottom": ["top", "bottom"],
    "full": ["top", "bottom", "shoes"],
}

CAT_NAMES = {"top": "上衣", "bottom": "下装", "shoes": "鞋子"}
SCOPE_NAMES = {
    "top": "上衣", "bottom": "下装", "shoes": "鞋子",
    "top_bottom": "上衣+下装", "full": "全套",
}

OUTFIT_PLAN_SYSTEM_PROMPT = """\
你是一个专业又亲切的穿搭顾问，像朋友聊天一样给建议。根据用户信息生成穿搭方案。只输出 JSON，不要添加任何额外说明。

输出格式（严格遵守）：
{
  "summary": "整体穿搭理念，像朋友给建议一样口语自然，2-4句话，结合用户实际情况",
  "items": [
    {
      "category": "top（或 bottom 或 shoes）",
      "name": "品类简称，2-6字，如：日系宽松衬衫",
      "description": "详细款式描述，像朋友推荐一样讲清楚颜色、版型、面料、细节等，3-5句话",
      "role": "这件单品在整体搭配中的作用，1-2句话，口语化",
      "search_keyword": "在拼多多搜索时使用的关键词，包含性别+风格+品类，10-15字以内"
    }
  ]
}

要求：
- items 仅包含用户所需品类（top/bottom/shoes 按实际需要）
- search_keyword 需要精准，能搜到对应商品，避免太笼统
- 结合用户身高体重推荐适合的版型
- 结合预算推荐对应定位的商品
- category 字段只能是 "top"、"bottom"、"shoes" 三选一
- summary 用口语化中文，像朋友给穿搭建议一样自然
"""


def generate_outfit_plan(
    request: PurchaseRecommendRequest,
    profile: UserProfile | None = None,
) -> OutfitPlan:
    """LLM 生成线上购衣穿搭方案（含搜索关键词）。"""
    categories = SCOPE_CATEGORIES[request.purchase_scope]

    budget_lines: list[str] = []
    if request.budget_mode == "custom":
        for cat in categories:
            cat_budget = getattr(request, f"budget_{cat}", None)
            budget_lines.append(f"{CAT_NAMES[cat]}预算：{cat_budget if cat_budget else '未指定'}元")
    elif request.budget:
        per = round(request.budget / len(categories))
        for cat in categories:
            budget_lines.append(f"{CAT_NAMES[cat]}预算：约{per}元")

    # 从 profile 构建用户信息
    gender_cn = ""
    height_str = ""
    weight_str = ""
    if profile:
        gender_cn = profile.gender or ""
        if profile.height_cm:
            height_str = f"，身高{profile.height_cm}cm"
        if profile.weight_kg:
            weight_str = f"，体重{profile.weight_kg}kg"

    user_msg = (
        f"帮我给{gender_cn}推荐几件衣服{height_str}{weight_str}。\n"
        f"想买：{', '.join(CAT_NAMES[c] for c in categories)}。\n"
        f"穿去什么场合：{request.scene or '日常通勤'}。\n"
        f"风格偏好：{request.style or '没特别要求'}。\n"
        f"预算：{request.budget or '没定'}元（{request.budget_mode}分配）。\n"
        + ("\n".join(budget_lines) + "\n" if budget_lines else "")
        + f"其他要求：{request.other or '没了'}。"
    )

    for attempt in range(2):
        try:
            resp = _get_client().chat.completions.create(
                model=settings.SENSENOVA_LLM_MODEL,
                messages=[
                    {"role": "system", "content": OUTFIT_PLAN_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.7,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or "{}"
            data = json.loads(content)
            plan = OutfitPlan(**data)

            plan_cats = {item.category for item in plan.items}
            expected = set(categories)
            if plan_cats != expected:
                if attempt == 0:
                    continue
                raise LLMUnavailableError(f"方案品类不匹配：期望 {expected}，得到 {plan_cats}")
            return plan

        except LLMUnavailableError:
            raise
        except Exception as exc:
            if attempt == 0:
                continue
            raise LLMUnavailableError(f"方案生成失败: {type(exc).__name__}: {exc}") from exc

    raise LLMUnavailableError("方案生成失败（已重试一次）")
