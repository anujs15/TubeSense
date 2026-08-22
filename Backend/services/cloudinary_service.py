# services/cloudinary_service.py

import hashlib
import os
import re
from functools import lru_cache

import cloudinary
import cloudinary.uploader

_FOLDER = "tubeai/notes"


@lru_cache(maxsize=1)
def _ensure_configured() -> None:
    """Apply Cloudinary config once. Accepts either the three separate
    CLOUDINARY_CLOUD_NAME / CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET variables or
    a single CLOUDINARY_URL. Raises if neither is present."""
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")

    if cloud_name and api_key and api_secret:
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True,  # force https URLs
        )
    elif os.getenv("CLOUDINARY_URL"):
        cloudinary.config(secure=True)
    else:
        raise RuntimeError(
            "Cloudinary is not configured. Set CLOUDINARY_CLOUD_NAME, "
            "CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET (or a single CLOUDINARY_URL) "
            "in Backend/.env — copy them from your Cloudinary dashboard."
        )


def _public_id(filename: str, prompt: str) -> str:
    """Deterministic public_id (filename slug + short prompt hash) so regenerating
    the same note overwrites its asset instead of piling up duplicates."""
    slug = re.sub(r"[^a-z0-9]+", "_", (filename or "image").lower()).strip("_") or "image"
    digest = hashlib.sha1((prompt or filename or "").encode("utf-8")).hexdigest()[:10]
    return f"{slug}_{digest}"


def upload_image_bytes(img_bytes: bytes, filename: str, prompt: str = "") -> str:
    """Upload raw image bytes to Cloudinary and return the secure (https) URL.

    ``filename`` and ``prompt`` only shape a stable public_id; ``img_bytes`` is the
    payload. Raises on failure — the caller wraps it into a graceful fallback.
    """
    _ensure_configured()
    result = cloudinary.uploader.upload(
        img_bytes,
        folder=_FOLDER,
        public_id=_public_id(filename, prompt),
        overwrite=True,
        resource_type="image",
    )
    url = result.get("secure_url")
    if not url:
        raise RuntimeError(f"Cloudinary upload returned no secure_url: {result!r}")
    return url
