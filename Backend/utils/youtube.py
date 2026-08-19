# utils/youtube.py

import re
from urllib.parse import urlparse, parse_qs


_VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")


def extract_video_id(url: str) -> str:
    """
    Extract a YouTube video ID from a raw ID or any common URL shape.

    Handles canonical/mobile/music `watch` URLs, `youtu.be` short links,
    `/shorts/`, `/embed/`, `/live/`, `/v/` paths, a bare paste with no scheme
    (e.g. "youtube.com/watch?v=..."), surrounding whitespace, and a raw 11-char
    video id. Raises ValueError with an actionable message when the input isn't a
    recognizable YouTube video (the caller maps this to a 400, not a 500).
    """
    candidate = (url or "").strip()
    if not candidate:
        raise ValueError("No YouTube URL provided.")

    if _VIDEO_ID.fullmatch(candidate):
        return candidate

    if "://" not in candidate:
        candidate = "https://" + candidate

    parsed = urlparse(candidate)
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]

    if host == "youtu.be":
        vid = parsed.path.lstrip("/").split("/", 1)[0]
        if _VIDEO_ID.fullmatch(vid):
            return vid

    elif host in {"youtube.com", "m.youtube.com", "music.youtube.com"}:
        if parsed.path == "/watch":
            values = parse_qs(parsed.query).get("v") or []
            if values and _VIDEO_ID.fullmatch(values[0]):
                return values[0]
        else:
            for prefix in ("/shorts/", "/embed/", "/live/", "/v/"):
                if parsed.path.startswith(prefix):
                    vid = parsed.path[len(prefix):].split("/", 1)[0]
                    if _VIDEO_ID.fullmatch(vid):
                        return vid

    raise ValueError(
        "Couldn't recognize that as a YouTube video link. Paste a URL like "
        "https://www.youtube.com/watch?v=VIDEO_ID or https://youtu.be/VIDEO_ID."
    )