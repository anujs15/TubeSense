# controllers/session_controller.py

from fastapi import HTTPException

from auth.deps import require_session
from services import session_service
from services.Aichat_service import get_chat_history


def _iso(value):
    return value.isoformat() if value else None


def _summary(doc: dict) -> dict:
    return {
        "id": doc["_id"],
        "title": doc.get("title", "New chat"),
        "has_video": bool(doc.get("video")),
        "has_notes": bool(doc.get("notes_markdown")),
        "created_at": _iso(doc.get("created_at")),
        "updated_at": _iso(doc.get("updated_at")),
    }


async def create(user: dict) -> dict:
    doc = session_service.create_session(str(user["_id"]))
    return _summary(doc)


async def list_all(user: dict) -> list[dict]:
    return [_summary(d) for d in session_service.list_sessions(str(user["_id"]))]


async def detail(session_id: str, user: dict) -> dict:
    doc = require_session(session_id, user)
    messages = await get_chat_history(session_id)
    return {
        "id": doc["_id"],
        "title": doc.get("title", "New chat"),
        "video": doc.get("video"),
        "notes_markdown": doc.get("notes_markdown"),
        "messages": messages,
        "created_at": _iso(doc.get("created_at")),
        "updated_at": _iso(doc.get("updated_at")),
    }


async def rename(session_id: str, title: str, user: dict) -> dict:
    require_session(session_id, user)
    clean = (title or "").strip()
    if not clean:
        raise HTTPException(status_code=400, detail="Title cannot be empty.")
    session_service.set_title(session_id, clean)
    return {"ok": True, "title": clean}


async def remove(session_id: str, user: dict) -> dict:
    ok = session_service.delete_session(session_id, str(user["_id"]))
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"ok": True}
