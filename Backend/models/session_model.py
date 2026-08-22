# models/session_model.py

from typing import Optional

from pydantic import BaseModel, Field


class SessionSummary(BaseModel):
    id: str
    title: str
    has_video: bool = False
    has_notes: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class SessionDetail(BaseModel):
    id: str
    title: str
    video: Optional[dict] = None
    notes_markdown: Optional[str] = None
    messages: list[ChatMessage] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class RenameModel(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
