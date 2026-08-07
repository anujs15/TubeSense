# services/youtube_service.py

import logging

from database.database import database
from services.comment_services import CommentService
from services.transcript_services import get_transcript
from utils.youtube import extract_video_id

logger = logging.getLogger(__name__)


class YouTubeService:

    def __init__(self):
        self._comment_service = None

    def _get_comment_service(self):
        if self._comment_service is None:
            self._comment_service = CommentService()

        return self._comment_service

    def VideoDataLoaded(self, url: str, lang:str):

        video_id = extract_video_id(url)

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

        # Only overwrite the stored transcript when the fetch actually returned one.
        # A failed fetch (rate-limited / blocked / unavailable) returns no transcript,
        # and we must not wipe a transcript that was already stored in the database.
        fetched_transcript = transcript.get("transcript")
        if fetched_transcript and str(fetched_transcript).strip():
            content["transcript"] = fetched_transcript

        database.update(content)

        return { "message": "transcript and Comment of video is loaded", "content":content }

    



