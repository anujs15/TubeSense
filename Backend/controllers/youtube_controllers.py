# controllers/youtube_controller.py

import json

from fastapi import HTTPException

from services.Aichat_service import chatwithAi
from services.youtube_services import YouTubeService
from AiModel.review import summarize_comment_feedback
from services.notes_service import run_note_writer, run_note_writer_stream
from database.database import database



service = YouTubeService()


def _status_for(message: str) -> int:
    """Map upstream rate-limit errors (HTTP 429, etc.) to 429 so the
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

    except HTTPException:

        raise
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
        # Notes are generated from the video's summary (produced during
        # /youtube/analyze), NOT the raw transcript — the summary is a cleaner,
        # shorter seed for the notes writer. Require it: no video analyzed yet
        # (or a restart wiped the in-memory store) means there's nothing to
        # write about, so fail early with an actionable message.
        summary = database.get("summary")
        if not summary or not str(summary).strip():
            raise HTTPException(
                status_code=400,
                detail="No video loaded yet. Analyze a video (POST /youtube/analyze) first — "
                       "notes are generated from its summary.",
            )

        return await run_note_writer(topic=summary)

    except HTTPException:
        raise
    except Exception as e:
        message = str(e)
        raise HTTPException(
            status_code=_status_for(message),
            detail=message,
        )


async def makeNotesStream():
    """NDJSON streaming variant of makeNotes.

    Same summary precondition as makeNotes, but instead of blocking for the whole
    ~2-3 min run it returns an async generator of newline-delimited JSON events
    (see run_note_writer_stream) so the UI can render the outline and each section
    as they arrive.

    The 400 "no video" precondition is raised synchronously — BEFORE the generator
    is returned — so the route surfaces it as a normal JSON error with the right
    status. Runtime failures happen after the 200 response stream is already open,
    so they cannot be an HTTP status; they are emitted as a terminal
    {"type":"error","detail","status"} event instead.
    """
    summary = database.get("summary")
    if not summary or not str(summary).strip():
        raise HTTPException(
            status_code=400,
            detail="No video loaded yet. Analyze a video (POST /youtube/analyze) first — "
                   "notes are generated from its summary.",
        )

    async def event_stream():
        try:
            async for event in run_note_writer_stream(topic=summary):
                yield json.dumps(event, ensure_ascii=False) + "\n"
        except Exception as e:
            message = str(e)
            yield json.dumps(
                {"type": "error", "detail": message, "status": _status_for(message)},
                ensure_ascii=False,
            ) + "\n"

    return event_stream()