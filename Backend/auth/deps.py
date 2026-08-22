# auth/deps.py

import jwt
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Header, HTTPException

from auth.security import decode_token
from database.database import sessions_col, users_col


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise _unauthorized()

    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise _unauthorized("Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise _unauthorized("Invalid token payload")

    try:
        user = users_col().find_one({"_id": ObjectId(user_id)})
    except InvalidId:
        raise _unauthorized("Invalid token subject")

    if not user:
        raise _unauthorized("User no longer exists")

    return user


def require_session(session_id: str, user: dict) -> dict:
    """Load a session and enforce that it belongs to ``user``.

    Raises 404 if the session doesn't exist, 403 if it's owned by someone else.
    Returns the session document (which carries the video/notes subdocs) so the
    caller can avoid a second read.
    """
    session = sessions_col().find_one({"_id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if str(session.get("user_id")) != str(user["_id"]):
        raise HTTPException(status_code=403, detail="You don't have access to this session.")
    return session
