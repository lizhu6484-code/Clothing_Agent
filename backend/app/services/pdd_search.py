"""Pinduoduo open platform API client for product search."""

from __future__ import annotations

import hashlib
import random
import time

import requests

from app.models.schemas import PddProduct


class PddSearchError(Exception):
    pass


class PddSearchClient:
    URL = "https://gw-api.pinduoduo.com/api/router"

    def __init__(self, client_id: str, client_secret: str, pid: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.pid = pid

    def _sign(self, params: dict) -> str:
        raw = "".join(f"{k}{params[k]}" for k in sorted(params))
        raw = self.client_secret + raw + self.client_secret
        return hashlib.md5(raw.encode("utf-8")).hexdigest().upper()

    def _call(self, params: dict) -> dict:
        p = dict(params)
        p["client_id"] = self.client_id
        p["timestamp"] = str(int(time.time()))
        p["sign"] = self._sign(p)
        try:
            resp = requests.post(self.URL, data=p, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            raise PddSearchError(f"PDD HTTP 请求失败: {exc}") from exc

    def search(self, keyword: str, count: int = 5) -> list[PddProduct]:
        page = random.randint(1, 5)
        base_params = {
            "type": "pdd.ddk.goods.search",
            "keyword": keyword,
            "page_size": max(count, 10),
            "pid": self.pid,
            "sort_type": 6,
        }

        goods_list = self._search_page(base_params, page)
        if not goods_list and page > 1:
            goods_list = self._search_page(base_params, 1)

        return self._parse_goods(goods_list, count)

    def _search_page(self, base_params: dict, page: int) -> list[dict]:
        params = dict(base_params)
        params["page"] = page
        try:
            data = self._call(params)
        except PddSearchError:
            raise
        except Exception as exc:
            raise PddSearchError(f"PDD 搜索调用异常: {exc}") from exc

        error_response = data.get("error_response")
        if error_response:
            code = error_response.get("error_code", "")
            msg = error_response.get("error_msg", "未知错误")
            raise PddSearchError(f"PDD API 错误 [{code}]: {msg}")

        return data.get("goods_search_response", {}).get("goods_list") or []

    def _parse_goods(self, goods_list: list[dict], count: int) -> list[PddProduct]:
        products: list[PddProduct] = []
        for g in goods_list[:count]:
            try:
                products.append(PddProduct(
                    goods_name=g.get("goods_name", ""),
                    min_group_price=g.get("min_group_price", 0),
                    min_normal_price=g.get("min_normal_price", 0),
                    coupon_discount=g.get("coupon_discount", 0) or 0,
                    sales_tip=g.get("sales_tip", ""),
                    promotion_rate=g.get("promotion_rate", 0) or 0,
                    goods_image_url=g.get("goods_image_url", ""),
                    unified_tags=g.get("unified_tags", []) or [],
                ))
            except Exception:
                continue
        return products
