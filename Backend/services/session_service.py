# services/session_service.py

import uuid
from datetime import datetime, timezone

from database.database import get_db, sessions_col


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_session(user_id: str, title: str = "New chat") -> dict:
    session_id = str(uuid.uuid4())
    doc = {
        "_id": session_id,
        "user_id": str(user_id),
        "title": title,
        "video": None,
        "notes_markdown": None,
        "created_at": _now(),
        "updated_at": _now(),
    }
    sessions_col().insert_one(doc)
    return doc


def list_sessions(user_id: str) -> list[dict]:
    cur = sessions_col().find({"user_id": str(user_id)}).sort("updated_at", -1)
    return list(cur)


def get_session(session_id: str, user_id: str) -> dict | None:
    return sessions_col().find_one({"_id": session_id, "user_id": str(user_id)})


def save_video(session_id: str, content: dict, title: str | None = None) -> None:
    update = {"video": content, "updated_at": _now()}
    if title:
        update["title"] = title
    sessions_col().update_one({"_id": session_id}, {"$set": update})


def save_notes(session_id: str, markdown: str) -> None:
    sessions_col().update_one(
        {"_id": session_id},
        {"$set": {"notes_markdown": markdown, "updated_at": _now()}},
    )


def set_title(session_id: str, title: str) -> None:
    sessions_col().update_one(
        {"_id": session_id},
        {"$set": {"title": title, "updated_at": _now()}},
    )


def delete_session(session_id: str, user_id: str) -> bool:
    res = sessions_col().delete_one({"_id": session_id, "user_id": str(user_id)})
    if not res.deleted_count:
        return False
    _delete_checkpoints(session_id)
    return True


def _delete_checkpoints(session_id: str) -> None:
    """Best-effort removal of this session's chat history so a deleted session
    doesn't leave orphaned checkpoint docs behind. The collection names match
    ``MongoDBSaver`` defaults (``checkpoints`` / ``checkpoint_writes``)."""
    db = get_db()
    for name in ("checkpoints", "checkpoint_writes"):
        try:
            db[name].delete_many({"thread_id": session_id})
        except Exception:
            pass
