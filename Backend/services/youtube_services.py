# services/youtube_service.py

import logging

from fastapi import HTTPException

from services import session_service
from services.comment_services import CommentService
from services.transcript_services import get_transcript
from utils.youtube import extract_video_id
from services.make_summary import summarize_transcript
logger = logging.getLogger(__name__)


class YouTubeService:

    def __init__(self):
        self._comment_service = None

    def _get_comment_service(self):
        if self._comment_service is None:
            self._comment_service = CommentService()

        return self._comment_service

    def VideoDataLoaded(self, url: str, lang: str, session_id: str):

        try:
            video_id = extract_video_id(url)
        except ValueError as exc:

            raise HTTPException(status_code=400, detail=str(exc))

        transcript = get_transcript(video_id)

        comments = []
        try:
            comments = self._get_comment_service().get_comments(
                video_id,
                max_results=200,
            )
        except Exception as exc:
            logger.warning("Comment fetch failed for %s: %s", video_id, exc)

        content= {
            "video_id": video_id,
            "transcript_provider": transcript["provider"],
            "transcript_language": transcript.get("language"),
            "transcript_success": transcript["success"],
            "transcript_message": transcript.get("message"),
            "comments": comments,
        }

        fetched_transcript = transcript.get("transcript")
        if not fetched_transcript or not str(fetched_transcript).strip():

            raise HTTPException(
                status_code=422,
                detail="This video has no captions/subtitles, so a transcript couldn't be "
                       "extracted. Try a video that has captions.",
            )
        content["transcript"] = fetched_transcript

        summary = summarize_transcript(content["transcript"])
        content["summary"] = summary

        # Persist into this user's session (was: a shared global dict). The
        # retriever cache is keyed by session, so re-analyzing a *new* video
        # under a fresh session id never collides with an existing one.
        session_service.save_video(session_id, content, title=video_id)

        return { "message": "transcript and Comment of video is loaded", "content":content }

    


