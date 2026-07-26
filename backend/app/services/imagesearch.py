"""图片搜索服务：复用 grep 搜索引擎为推荐关键词抓取/生成图片。"""
from __future__ import annotations

import os
import re
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

from app.config import settings

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
GREP_DIR = BASE_DIR / "grep"
OUTPUT_DIR = BASE_DIR / "output"

if str(GREP_DIR) not in sys.path:
    sys.path.insert(0, str(GREP_DIR))

from image_module_a import get_material_image_path_a  # noqa: E402

if settings.DASHSCOPE_API_KEY:
    os.environ.setdefault("DASHSCOPE_API_KEY", settings.DASHSCOPE_API_KEY)

_executor = ThreadPoolExecutor(max_workers=3)

_PAREN_RE = re.compile(r"[（(][^（）()]*[）)]")
_MAX_ATTEMPTS = 2


def _clean_keyword(keyword: str) -> str:
    cleaned = _PAREN_RE.sub("", keyword)
    return cleaned.strip()


def _safe_filename(keyword: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "_", keyword).strip("_") or "item"


def _is_placeholder_gray(path: str) -> bool:
    try:
        with Image.open(path) as img:
            rgb = img.convert("RGB")
            w, h = rgb.size
            samples = [
                rgb.getpixel((w // 2, h // 2)),
                rgb.getpixel((w // 4, h // 4)),
                rgb.getpixel((3 * w // 4, 3 * h // 4)),
            ]
            return all(abs(c - 240) < 8 for px in samples for c in px)
    except Exception:
        return False


def _fetch_once(cleaned: str) -> str | None:
    try:
        src_path = get_material_image_path_a(cleaned)
    except Exception as e:
        print(f"[imagesearch] 搜索 '{cleaned}' 异常: {e}")
        return None

    if not src_path or not os.path.exists(src_path):
        return None
    if _is_placeholder_gray(src_path):
        return None
    return src_path


def _search_one(keyword: str) -> dict:
    cleaned = _clean_keyword(keyword)
    if not cleaned:
        return {"keyword": keyword, "url": None}

    src_path = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        src_path = _fetch_once(cleaned)
        if src_path:
            break

    if not src_path:
        return {"keyword": keyword, "url": None}

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{_safe_filename(cleaned)}_{int(time.time() * 1000)}.jpg"
    dst = OUTPUT_DIR / filename
    try:
        shutil.copy2(src_path, dst)
    except Exception:
        return {"keyword": keyword, "url": None}

    return {"keyword": keyword, "url": f"/output/{filename}"}


def search_images(keywords: list[str]) -> list[dict]:
    if not keywords:
        return []

    futures = [_executor.submit(_search_one, kw) for kw in keywords]
    results = []
    for kw, fut in zip(keywords, futures):
        try:
            results.append(fut.result())
        except Exception:
            results.append({"keyword": kw, "url": None})
    return results
