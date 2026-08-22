# controllers/youtube_controller.py

import json
import re

from fastapi import HTTPException

from auth.deps import require_session
from services.Aichat_service import chatwithAi
from services.youtube_services import YouTubeService
from services import session_service
from AiModel.review import summarize_comment_feedback
from services.notes_service import run_note_writer, run_note_writer_stream
from services.pdf_service import notes_markdown_to_pdf



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


async def videoLoad(url: str, lang: str, session_id: str, user: dict):

    try:
        require_session(session_id, user)  # 404/403 if not the caller's session
        return service.VideoDataLoaded(url, lang, session_id)

    except HTTPException:

        raise
    except Exception as e:
        message = str(e)
        raise HTTPException(
            status_code=_status_for(message),
            detail=message,
        )


async def QAWithAi(session_id: str, user_query: str, user: dict):
    try:
        require_session(session_id, user)
        return await chatwithAi(session_id, user_query)

    except HTTPException:
        raise
    except Exception as e:
        message = str(e)
        raise HTTPException(
            status_code=_status_for(message),
            detail=message,
        )


async def analyzeSentiment(session_id: str, user: dict):
    try:
        require_session(session_id, user)
       
        return summarize_comment_feedback(session_id)

    except HTTPException:
        raise
    except Exception as e:
        message = str(e)
        raise HTTPException(
            status_code=_status_for(message),
            detail=message,
        )


async def makeNotes(session_id: str, user: dict):
    try:
       
        session = require_session(session_id, user)
        summary = (session.get("video") or {}).get("summary")
        if not summary or not str(summary).strip():
            raise HTTPException(
                status_code=400,
                detail="No video loaded yet. Analyze a video (POST /youtube/analyze) first — "
                       "notes are generated from its summary.",
            )

        result = await run_note_writer(topic=summary)

       
        try:
            final_md = result.get("final") if isinstance(result, dict) else None
            if final_md:
                session_service.save_notes(session_id, final_md)
        except Exception:
            pass

        return result

    except HTTPException:
        raise
    except Exception as e:
        message = str(e)
        raise HTTPException(
            status_code=_status_for(message),
            detail=message,
        )


async def makeNotesStream(session_id: str, user: dict):
    """NDJSON streaming variant of makeNotes.

    Same summary precondition as makeNotes, but instead of blocking for the whole
    ~2-3 min run it returns an async generator of newline-delimited JSON events
    (see run_note_writer_stream) so the UI can render the outline and each section
    as they arrive.

    The 400 "no video" precondition — and the 404/403 ownership checks — are
    raised synchronously BEFORE the generator is returned, so the route surfaces
    them as normal JSON errors with the right status. Runtime failures happen
    after the 200 response stream is already open, so they cannot be an HTTP
    status; they are emitted as a terminal {"type":"error",...} event instead.
    """
    session = require_session(session_id, user)
    summary = (session.get("video") or {}).get("summary")
    if not summary or not str(summary).strip():
        raise HTTPException(
            status_code=400,
            detail="No video loaded yet. Analyze a video (POST /youtube/analyze) first — "
                   "notes are generated from its summary.",
        )

    async def event_stream():
        try:
            async for event in run_note_writer_stream(topic=summary):
                
                if isinstance(event, dict) and event.get("type") == "final":
                    md = event.get("markdown")
                    if md:
                        try:
                            session_service.save_notes(session_id, md)
                        except Exception:
                            pass
                yield json.dumps(event, ensure_ascii=False) + "\n"
        except Exception as e:
            message = str(e)
            yield json.dumps(
                {"type": "error", "detail": message, "status": _status_for(message)},
                ensure_ascii=False,
            ) + "\n"

    return event_stream()


async def notesPdf(session_id: str, user: dict):
    """Render the session's stored notes markdown to a downloadable PDF.

    Notes live in MongoDB (``sessions.notes_markdown``); this reads that markdown
    and converts it to PDF bytes server-side (see ``services.pdf_service``).
    Returns ``(pdf_bytes, filename)`` for the route to stream back.
    """
    try:
        session = require_session(session_id, user)
        md = session.get("notes_markdown")
        if not md or not str(md).strip():
            raise HTTPException(
                status_code=400,
                detail="No notes yet. Generate notes first, then download.",
            )

        title = (session.get("title") or "notes").strip() or "notes"
        pdf_bytes = notes_markdown_to_pdf(md, title=title)

        slug = re.sub(r"[^A-Za-z0-9._-]+", "_", title).strip("_") or "notes"
        return pdf_bytes, f"{slug}.pdf"

    except HTTPException:
        raise
    except Exception as e:
        message = str(e)
        raise HTTPException(
            status_code=_status_for(message),
            detail=message,
        )
