from fastapi import APIRouter, HTTPException

from app.db import get_conn
from app.models.schemas import UserProfile

router = APIRouter(prefix="/api/user", tags=["user"])


def _row_to_profile(row) -> UserProfile:
    return UserProfile(
        id=row["id"],
        name=row["name"],
        gender=row["gender"],
        height_cm=row["height_cm"],
        weight_kg=row["weight_kg"],
        age=row["age"],
        notes=row["notes"],
        is_active=bool(row["is_active"]),
        updated_at=row["updated_at"],
    )


@router.get("")
def list_profiles():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM user_profile ORDER BY is_active DESC, id ASC").fetchall()
    conn.close()
    return [_row_to_profile(r).model_dump() for r in rows]


@router.post("")
def create_profile(body: UserProfile):
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) AS c FROM user_profile").fetchone()["c"]
    is_active = 1 if count == 0 else 0
    cur = conn.execute(
        """INSERT INTO user_profile (name, gender, height_cm, weight_kg, age, notes, is_active, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
        (body.name, body.gender, body.height_cm, body.weight_kg, body.age, body.notes, is_active),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM user_profile WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return _row_to_profile(row).model_dump()


@router.put("/{profile_id}")
def update_profile(profile_id: int, body: UserProfile):
    conn = get_conn()
    exists = conn.execute("SELECT id FROM user_profile WHERE id = ?", (profile_id,)).fetchone()
    if not exists:
        conn.close()
        raise HTTPException(404, detail={"error": "USER_NOT_FOUND"})

    conn.execute(
        """UPDATE user_profile
           SET name=?, gender=?, height_cm=?, weight_kg=?, age=?, notes=?, updated_at=CURRENT_TIMESTAMP
           WHERE id=?""",
        (body.name, body.gender, body.height_cm, body.weight_kg, body.age, body.notes, profile_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM user_profile WHERE id = ?", (profile_id,)).fetchone()
    conn.close()
    return _row_to_profile(row).model_dump()


@router.post("/{profile_id}/activate")
def activate_profile(profile_id: int):
    conn = get_conn()
    exists = conn.execute("SELECT id FROM user_profile WHERE id = ?", (profile_id,)).fetchone()
    if not exists:
        conn.close()
        raise HTTPException(404, detail={"error": "USER_NOT_FOUND"})

    conn.execute("UPDATE user_profile SET is_active = 0")
    conn.execute("UPDATE user_profile SET is_active = 1 WHERE id = ?", (profile_id,))
    conn.commit()
    conn.close()
    return {"ok": True, "active_id": profile_id}


@router.delete("/{profile_id}")
def delete_profile(profile_id: int):
    conn = get_conn()
    row = conn.execute("SELECT is_active FROM user_profile WHERE id = ?", (profile_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, detail={"error": "USER_NOT_FOUND"})

    was_active = row["is_active"]
    conn.execute("DELETE FROM user_profile WHERE id = ?", (profile_id,))
    if was_active:
        first = conn.execute("SELECT id FROM user_profile ORDER BY id ASC LIMIT 1").fetchone()
        if first:
            conn.execute("UPDATE user_profile SET is_active = 1 WHERE id = ?", (first["id"],))
    conn.commit()
    conn.close()
    return {"ok": True}
