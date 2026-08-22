#models/uploadModel.py

from pydantic import BaseModel, Field

class UploadModel(BaseModel):
    url: str = Field(..., description="The URL of the YouTube video to analyze.")
    lang: str = Field("en", description="The language code for the transcript (default is 'en').")
    session_id: str = Field(..., description="The workspace/session this video belongs to.")