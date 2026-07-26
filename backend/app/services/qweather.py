import time

import httpx

from app.config import settings
from app.models.schemas import Weather

_cache: dict[tuple[float, float], tuple[Weather, float]] = {}
_geo_cache: dict[tuple[float, float], str] = {}
TTL = 30 * 60


class WeatherUnavailableError(Exception):
    pass


def get_location_name(lat: float, lon: float) -> str:
    """用 QWeather GeoAPI 把经纬度转成地区名（市/区）。失败时返回空串。"""
    key = (round(lat, 2), round(lon, 2))
    if key in _geo_cache:
        return _geo_cache[key]

    query = f"{lon:.2f},{lat:.2f}"
    url = f"{settings.QWEATHER_BASE_URL}/geo/v2/city/lookup"
    try:
        resp = httpx.get(
            url,
            params={"location": query, "number": 1},
            headers={"X-QW-Api-Key": settings.QWEATHER_API_KEY},
            verify=False,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return ""

    if data.get("code") != "200" or not data.get("location"):
        return ""

    loc = data["location"][0]
    name = f"{loc.get('adm', '')} {loc.get('name', '')}".strip()
    _geo_cache[key] = name
    return name


def get_weather(lat: float, lon: float) -> Weather:
    key = (round(lat, 2), round(lon, 2))
    now = time.time()

    if key in _cache:
        cached_weather, cached_at = _cache[key]
        if now - cached_at < TTL:
            return cached_weather

    query = f"{lon:.2f},{lat:.2f}"
    url = f"{settings.QWEATHER_BASE_URL}/v7/weather/now"
    try:
        resp = httpx.get(url, params={"location": query}, headers={"X-QW-Api-Key": settings.QWEATHER_API_KEY}, verify=False, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise WeatherUnavailableError(f"Weather API failed: {e}") from e

    if data.get("code") != "200":
        raise WeatherUnavailableError(f"Weather API error: {data.get('code', 'unknown')}")

    now_data = data["now"]
    weather = Weather(
        temp=int(now_data.get("temp") or 0),
        text=now_data.get("text", ""),
        humidity=int(now_data.get("humidity") or 0),
        wind=f"{now_data.get('windDir', '')}{now_data.get('windScale', '')}级",
    )

    _cache[key] = (weather, now)
    return weather
