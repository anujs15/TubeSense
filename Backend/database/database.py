#database/database.py

import logging
import os
from functools import lru_cache

from pymongo import ASCENDING, MongoClient

logger = logging.getLogger(__name__)

_DEFAULT_URI = "mongodb://localhost:27017"
_DEFAULT_DB = "tubeai"


def _uri() -> str:
    return os.getenv("MONGODB_URI", _DEFAULT_URI)


def get_db_name() -> str:
    return os.getenv("MONGODB_DB", _DEFAULT_DB)


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    """Return the process-wide MongoClient (created once, then cached)."""
    return MongoClient(_uri(), serverSelectionTimeoutMS=8000, tz_aware=True)


def get_db():
    return get_client()[get_db_name()]


def users_col():
    return get_db()["users"]


def sessions_col():
    return get_db()["sessions"]


def ensure_indexes() -> None:
    """Create the indexes the app relies on. Fail-soft: if the cluster is not
    reachable yet (URI still a placeholder), log a warning and let the app boot
    anyway — indexes get created on the next start once the real URI is set."""
    try:
        users_col().create_index([("email", ASCENDING)], unique=True, name="uniq_email")
        sessions_col().create_index([("user_id", ASCENDING)], name="by_user")
        sessions_col().create_index([("user_id", ASCENDING), ("updated_at", -1)], name="by_user_recent")
        logger.info("MongoDB indexes ensured on '%s'.", get_db_name())
    except Exception as exc: 
        logger.warning(
            "Could not create MongoDB indexes (is MONGODB_URI set to a real cluster?): %s",
            exc,
        )
