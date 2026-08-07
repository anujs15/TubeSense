import logging
import os

from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


class CommentService:

    def __init__(self):
        api_key = os.getenv("YOUTUBE_API_KEY")
        self.youtube = None

        if not api_key:
            logger.warning("YOUTUBE_API_KEY is not set; comment fetching is disabled.")
            return

        try:
            self.youtube = build(
                "youtube",
                "v3",
                developerKey=api_key,
            )
        except Exception as exc:
            logger.warning("Failed to initialize YouTube comment client: %s", exc)
            self.youtube = None

    def get_comments(
        self,
        video_id: str,
        max_results=100,
    ):

        if self.youtube is None:
            return []

        comments = []

        request = self.youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=min(max_results, 100),
            textFormat="plainText",
            order="relevance",
        )

        while request:

            response = request.execute()

            for item in response["items"]:

                snippet = item["snippet"]["topLevelComment"][
                    "snippet"
                ]

                comments.append(
                    {
                        "author": snippet["authorDisplayName"],
                        "text": snippet["textDisplay"],
                        "likes": snippet["likeCount"],
                    }
                )

            request = self.youtube.commentThreads().list_next(
                request,
                response,
            )

            if len(comments) >= max_results:
                break

        return comments[:max_results]