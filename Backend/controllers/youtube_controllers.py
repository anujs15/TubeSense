# controllers/youtube_controller.py

from fastapi import HTTPException

from services.Aichat_service import chatwithAi
from services.youtube_services import YouTubeService
from AiModel.review import summarize_comment_feedback
from services.notes_service import run_note_writer
from database.database import database



service = YouTubeService()


def _status_for(message: str) -> int:
    """Map upstream rate-limit errors (Mistral/HTTP 429, etc.) to 429 so the
    frontend can show a 'please wait and retry' message instead of a generic
    500. Providers phrase this differently: 'rate limit exceeded',
    'rate_limited', 'rate-limited', or a bare '429'."""
    m = message.lower()
    if "429" in m or "rate limit" in m or "rate-limited" in m or "rate_limited" in m:
        return 429
    return 500


async def videoLoad(url: str, lang:str):

    try:
        return service.VideoDataLoaded(url,lang)

    except Exception as e:
        message = str(e)
        raise HTTPException(
            status_code=_status_for(message),
            detail=message,
        )


async def QAWithAi(user_query:str):
    try:
        return await chatwithAi(user_query)

    except Exception as e:
        message = str(e)
        raise HTTPException(
            status_code=_status_for(message),
            detail=message,
        )


async def analyzeSentiment():
    try:
        # summarize_comment_feedback is synchronous (returns a str), so we must
        # not await it — doing so raises "'str' object can't be awaited".
        return summarize_comment_feedback()

    except Exception as e:
        message = str(e)
        raise HTTPException(
            status_code=_status_for(message),
            detail=message,
        )

async def makeNotes():
    try:
        # Placeholder for the actual implementation of makeNotes
        transcript=  database["transcript"]

        return await run_note_writer(transcript=transcript)

    except Exception as e:
        message = str(e)
        raise HTTPException(
            status_code=_status_for(message),
            detail=message,
        )