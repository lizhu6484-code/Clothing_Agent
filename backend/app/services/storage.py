import hashlib
import uuid
from datetime import date
from pathlib import Path

ALLOWED_EXT = {"jpg", "jpeg", "png", "webp"}
UPLOAD_ROOT = Path(__file__).resolve().parent.parent.parent / "uploads"


def save_wardrobe_image(file_bytes: bytes, user_id: int, ext: str) -> tuple[str, str]:
    ext = ext.lower().lstrip(".")
    if ext not in ALLOWED_EXT:
        raise ValueError(f"Unsupported extension: {ext}")

    image_hash = hashlib.sha256(file_bytes).hexdigest()
    day_dir = date.today().strftime("%Y%m%d")
    filename = f"{uuid.uuid4().hex[:8]}.{ext}"

    rel_path = f"uploads/wardrobe/{user_id}/{day_dir}/{filename}"
    abs_path = UPLOAD_ROOT.parent / rel_path

    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(file_bytes)

    return rel_path, image_hash


def delete_wardrobe_image(relative_path: str) -> None:
    abs_path = get_absolute_path(relative_path)
    if abs_path.exists():
        abs_path.unlink()


def get_absolute_path(relative_path: str) -> Path:
    return UPLOAD_ROOT.parent / relative_path
