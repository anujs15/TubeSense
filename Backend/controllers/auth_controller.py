# controllers/auth_controller.py


from datetime import datetime, timezone

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from auth.security import create_token, hash_password, verify_password
from database.database import users_col
from models.auth_model import LoginModel, SignupModel


def public_user(user: dict) -> dict:
    return {
        "id": str(user["_id"]),
        "email": user.get("email", ""),
        "display_name": user.get("display_name", ""),
    }


async def signup(payload: SignupModel) -> dict:
    email = (payload.email or "").strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Please provide a valid email address.")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    if users_col().find_one({"email": email}):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    pwd_hash, pwd_salt = hash_password(payload.password)
    doc = {
        "email": email,
        "display_name": (payload.display_name or email.split("@")[0]).strip(),
        "pwd_hash": pwd_hash,
        "pwd_salt": pwd_salt,
        "created_at": datetime.now(timezone.utc),
    }
    try:
        result = users_col().insert_one(doc)
    except DuplicateKeyError:
        # Lost a race against a concurrent signup with the same email.
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    doc["_id"] = result.inserted_id
    return {"token": create_token(result.inserted_id), "user": public_user(doc)}


async def login(payload: LoginModel) -> dict:
    email = (payload.email or "").strip().lower()
    user = users_col().find_one({"email": email})
    if not user or not verify_password(
        payload.password, user.get("pwd_hash", ""), user.get("pwd_salt", "")
    ):
       
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    return {"token": create_token(user["_id"]), "user": public_user(user)}
