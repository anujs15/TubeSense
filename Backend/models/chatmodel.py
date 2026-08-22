#models/chatmodel.py

from pydantic import BaseModel, Field

class ChatModel(BaseModel):
    user_query: str = Field(..., description="The user's query for the AI chat.")
    session_id: str = Field(..., description="The workspace/session this chat belongs to.")


class ChatResponseModel(BaseModel):
    feedback: str = Field(..., description="The user's feedback on the basis of comment analysis.")