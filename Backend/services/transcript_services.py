import html
import json
import logging
import re
from typing import Any
from xml.etree import ElementTree as ET

import requests
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

from utils.youtube import extract_video_id as extract_video_id_from_url

logger = logging.getLogger(__name__)

LANGUAGE_PRIORITY = ["en", "en-US", "en-GB", "hi"]


def extract_video_id(video_id_or_url: str) -> str:
    """Accept either a raw video id or a full YouTube URL and return a video id."""
    candidate = (video_id_or_url or "").strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
        return candidate
    return extract_video_id_from_url(candidate)


def _is_blocked_or_html_response(text: str) -> bool:
    sample = (text or "").strip().lower()
    return (
        sample.startswith("<html")
        or "<title>sorry" in sample
        or "automated queries" in sample
        or "google help" in sample
    )


def _normalize_language_key(lang: str) -> str:
    return (lang or "").replace("_", "-").strip().lower()


def _collect_subtitles(info: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    merged: dict[str, list[dict[str, Any]]] = {}
    for source_key in ("subtitles", "automatic_captions"):
        source = info.get(source_key) or {}
        for lang, tracks in source.items():
            merged.setdefault(lang, [])
            merged[lang].extend(tracks or [])
    return merged


def _choose_language(available_languages: list[str]) -> str:
    if not available_languages:
        raise ValueError("No subtitles available")

    normalized_to_original = {
        _normalize_language_key(lang): lang for lang in available_languages
    }

    for preferred in LANGUAGE_PRIORITY:
        if _normalize_language_key(preferred) in normalized_to_original:
            return normalized_to_original[_normalize_language_key(preferred)]

    return available_languages[0]


def _detect_subtitle_format(raw_text: str, hinted_ext: str | None, subtitle_url: str) -> str:
    hint = (hinted_ext or "").strip().lower()
    url_lower = (subtitle_url or "").lower()
    sample = (raw_text or "").lstrip()

    if hint in {"json3", "vtt", "srv3", "ttml", "xml"}:
        return hint

    if "fmt=json3" in url_lower or sample.startswith("{"):
        return "json3"

    if "webvtt" in sample.lower() or ".vtt" in url_lower:
        return "vtt"

    if "<timedtext" in sample.lower() or "<transcript" in sample.lower() or ".srv3" in url_lower:
        return "srv3"

    if sample.startswith("<"):
        return "xml"

    return "vtt"


def download_subtitle(subtitle_url: str, timeout: int = 20) -> str:
    response = requests.get(subtitle_url, timeout=timeout)
    response.raise_for_status()
    return response.text


def clean_text(lines: list[str]) -> str:
    cleaned_lines: list[str] = []
    previous = ""

    for raw_line in lines:
        line = html.unescape((raw_line or "").replace("\xa0", " "))
        line = re.sub(r"\s+", " ", line).strip()

        if not line:
            continue

        if line == previous:
            continue

        cleaned_lines.append(line)
        previous = line

    return " ".join(cleaned_lines).strip()


def parse_json3(raw_text: str) -> str:
    """JSON3 subtitles contain segment arrays; we join segment text into caption lines."""
    payload = json.loads(raw_text)
    events = payload.get("events", [])
    lines: list[str] = []

    for event in events:
        segs = event.get("segs") or []
        if not segs:
            continue
        line = "".join((seg.get("utf8") or "") for seg in segs)
        lines.append(line)

    return clean_text(lines)


def parse_vtt(raw_text: str) -> str:
    """VTT subtitles include timing and cue metadata that must be stripped to plain dialogue."""
    lines: list[str] = []
    in_note_block = False

    for raw_line in raw_text.splitlines():
        line = raw_line.strip("\ufeff").strip()

        if not line:
            in_note_block = False
            continue

        if line.startswith("NOTE"):
            in_note_block = True
            continue

        if in_note_block:
            continue

        if line.upper() == "WEBVTT":
            continue

        if "-->" in line:
            continue

        if re.fullmatch(r"\d+", line):
            continue

        line = re.sub(r"<[^>]+>", "", line)
        lines.append(line)

    return clean_text(lines)


def parse_ttml(raw_text: str) -> str:
    """TTML/XML/SRV3 subtitles are XML-based; we extract text nodes from cue elements."""
    root = ET.fromstring(raw_text)
    lines: list[str] = []

    for element in root.iter():
        tag = element.tag.split("}")[-1].lower()
        if tag not in {"p", "text"}:
            continue

        line = "".join(element.itertext())
        if line:
            lines.append(line)

    return clean_text(lines)


def _parse_subtitle(raw_text: str, subtitle_format: str) -> str:
    fmt = subtitle_format.lower()
    if fmt == "json3":
        return parse_json3(raw_text)
    if fmt == "vtt":
        return parse_vtt(raw_text)
    if fmt in {"srv3", "ttml", "xml"}:
        return parse_ttml(raw_text)
    return parse_vtt(raw_text)


def _get_primary_transcript(video_id: str) -> dict[str, Any]:
    api = YouTubeTranscriptApi()
    fetched = api.fetch(video_id, languages=LANGUAGE_PRIORITY)
    transcript_text = clean_text([snippet.text for snippet in fetched])
    if not transcript_text:
        raise ValueError("Primary transcript provider returned empty transcript")

    return {
        "success": True,
        "provider": "youtube_transcript_api",
        "language": fetched.language_code,
        "transcript": transcript_text,
    }


def _best_track_for_language(tracks: list[dict[str, Any]]) -> dict[str, Any]:
    if not tracks:
        raise ValueError("No subtitle tracks available for selected language")

    for track in tracks:
        if (track.get("ext") or "").lower() == "json3":
            return track
    for track in tracks:
        if (track.get("ext") or "").lower() == "vtt":
            return track
    return tracks[0]


def _get_fallback_transcript(video_id: str) -> dict[str, Any]:
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    subtitles = _collect_subtitles(info)
    available_languages = list(subtitles.keys())
    logger.info("Available subtitle languages for %s: %s", video_id, available_languages)

    if not available_languages:
        raise ValueError("No subtitles found")

    language = _choose_language(available_languages)
    track = _best_track_for_language(subtitles[language])
    subtitle_url = track.get("url")

    if not subtitle_url:
        raise ValueError("Selected subtitle track is missing URL")

    raw_text = download_subtitle(subtitle_url)

    if _is_blocked_or_html_response(raw_text):
        raise ValueError("Transcript fetch blocked by Google")

    subtitle_format = _detect_subtitle_format(raw_text, track.get("ext"), subtitle_url)
    transcript_text = _parse_subtitle(raw_text, subtitle_format)

    if not transcript_text:
        raise ValueError("Parsed subtitle transcript is empty")

    return {
        "success": True,
        "provider": "yt-dlp",
        "language": language,
        "transcript": transcript_text,
    }


def get_transcript(video_id: str) -> dict[str, Any]:
    resolved_video_id = extract_video_id(video_id)

    try:
        logger.info("Fetching transcript from youtube_transcript_api for video %s", resolved_video_id)
        return _get_primary_transcript(resolved_video_id)
    except Exception as primary_error:
        logger.warning(
            "Primary transcript provider failed for video %s: %s",
            resolved_video_id,
            primary_error,
        )

    try:
        logger.info("Falling back to yt-dlp for video %s", resolved_video_id)
        return _get_fallback_transcript(resolved_video_id)
    except requests.exceptions.RequestException as request_error:
        logger.exception("yt-dlp subtitle download failed for %s", resolved_video_id)
        return {
            "success": False,
            "provider": None,
            "message": "Transcript unavailable",
        }
    except Exception as fallback_error:
        logger.exception("yt-dlp fallback failed for %s", resolved_video_id)
        return {
            "success": False,
            "provider": None,
            "message": "Transcript unavailable",
        }