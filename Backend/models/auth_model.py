# models/auth_model.py

from pydantic import BaseModel, Field

class SignupModel(BaseModel):
    email: str = Field(..., description="Email address (used to log in).")
    password: str = Field(..., min_length=6, description="Plaintext password (min 6 chars).")
    display_name: str = Field("", description="Optional display name.")


class LoginModel(BaseModel):
    email: str = Field(..., description="Email address.")
    password: str = Field(..., description="Plaintext password.")


class UserPublic(BaseModel):
    id: str
    email: str
    display_name: str = ""


class TokenResponse(BaseModel):
    token: str
    user: UserPublic
