import json
import logging

from fastapi import APIRouter, HTTPException, UploadFile

from app.db import get_conn
from app.models.schemas import WardrobeItem, WardrobeItemCreate
from app.services.sensenova import VLMUnavailableError, recognize_clothing
from app.services.storage import delete_wardrobe_image, save_wardrobe_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wardrobe", tags=["wardrobe"])


def _get_active_user_id() -> int:
    conn = get_conn()
    row = conn.execute("SELECT id FROM user_profile WHERE is_active = 1 LIMIT 1").fetchone()
    conn.close()
    return row["id"] if row else 1


@router.post("/upload")
def upload(file: UploadFile):
    file_bytes = file.file.read()
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "jpg"
    user_id = _get_active_user_id()

    try:
        rel_path, image_hash = save_wardrobe_image(file_bytes, user_id, ext)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))

    conn = get_conn()
    existing = conn.execute(
        "SELECT * FROM wardrobe_items WHERE image_hash = ?", (image_hash,)
    ).fetchone()
    if existing:
        conn.close()
        return {"id": existing["id"], "image_path": existing["image_path"], "recognized": _row_to_item(existing)}

    try:
        recognized = recognize_clothing(file_bytes)
    except VLMUnavailableError:
        conn.close()
        raise HTTPException(503, detail={"error": "VLM_UNAVAILABLE"})

    cur = conn.execute(
        """INSERT INTO wardrobe_items (user_id, image_path, image_hash, name, type, category, color, material, season, formality, style, features)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            rel_path,
            image_hash,
            recognized.get("name") or "",
            recognized.get("type") or "",
            recognized.get("category") or "",
            recognized.get("color") or "",
            recognized.get("material") or "",
            json.dumps(recognized.get("season") or [], ensure_ascii=False),
            recognized.get("formality") or 3,
            json.dumps(recognized.get("style") or [], ensure_ascii=False),
            json.dumps(recognized.get("features") or [], ensure_ascii=False),
        ),
    )
    conn.commit()
    item_id = cur.lastrowid
    row = conn.execute("SELECT * FROM wardrobe_items WHERE id = ?", (item_id,)).fetchone()
    conn.close()

    return {"id": item_id, "image_path": rel_path, "recognized": _row_to_item(row)}


@router.get("/items")
def list_items():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM wardrobe_items ORDER BY created_at DESC").fetchall()
    conn.close()
    return [_row_to_item(r) for r in rows]


@router.put("/items/{item_id}")
def update_item(item_id: int, body: WardrobeItemCreate):
    conn = get_conn()
    row = conn.execute("SELECT * FROM wardrobe_items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, detail="Item not found")

    conn.execute(
        """UPDATE wardrobe_items SET name=?, type=?, category=?, color=?, material=?, season=?, formality=?, style=?, features=?
           WHERE id=?""",
        (
            body.name,
            body.type,
            body.category,
            body.color,
            body.material or "",
            json.dumps(body.season, ensure_ascii=False),
            body.formality,
            json.dumps(body.style, ensure_ascii=False),
            json.dumps(body.features, ensure_ascii=False),
            item_id,
        ),
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM wardrobe_items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    return _row_to_item(updated)


@router.delete("/items/{item_id}")
def delete_item(item_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM wardrobe_items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, detail="Item not found")

    conn.execute("DELETE FROM wardrobe_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

    try:
        delete_wardrobe_image(row["image_path"])
    except Exception as e:
        logger.warning("Failed to delete file %s: %s", row["image_path"], e)

    return {"ok": True}


def _row_to_item(row) -> dict:
    return WardrobeItem(
        id=row["id"],
        user_id=row["user_id"],
        image_path=row["image_path"],
        image_hash=row["image_hash"],
        name=row["name"],
        type=row["type"],
        category=row["category"],
        color=row["color"],
        material=row["material"],
        season=json.loads(row["season"]),
        formality=row["formality"],
        style=json.loads(row["style"]),
        features=json.loads(row["features"]),
        created_at=row["created_at"],
    ).model_dump()
