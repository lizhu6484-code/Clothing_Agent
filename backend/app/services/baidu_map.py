"""百度地图 Place API —— 搜索附近服装店。"""

import httpx

from app.config import settings

BAIDU_PLACE_URL = "https://api.map.baidu.com/place/v2/search"


class BaiduMapUnavailableError(Exception):
    pass


def search_nearby_stores(
    lat: float,
    lon: float,
    keyword: str = "服装店",
    radius: int = 3000,
    page_size: int = 10,
) -> list[dict]:
    if not settings.BAIDU_MAP_AK:
        raise BaiduMapUnavailableError("BAIDU_MAP_AK not configured")

    params = {
        "query": keyword,
        "location": f"{lat},{lon}",
        "radius": radius,
        "output": "json",
        "ak": settings.BAIDU_MAP_AK,
        "page_size": page_size,
        "scope": 2,
    }

    try:
        resp = httpx.get(BAIDU_PLACE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise BaiduMapUnavailableError(f"Baidu Map API failed: {e}") from e

    if data.get("status") != 0:
        raise BaiduMapUnavailableError(
            f"Baidu Map API error: {data.get('message', 'unknown')}"
        )

    stores: list[dict] = []
    for r in data.get("results", []):
        detail = r.get("detail_info", {})
        stores.append(
            {
                "name": r.get("name", ""),
                "address": r.get("address", ""),
                "phone": r.get("telephone", ""),
                "tags": detail.get("tag", ""),
                "rating": detail.get("overall_rating", ""),
                "lat": r.get("location", {}).get("lat", 0),
                "lon": r.get("location", {}).get("lng", 0),
            }
        )
    return stores
