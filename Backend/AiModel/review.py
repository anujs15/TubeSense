#AiModel/review.py

from __future__ import annotations

from pathlib import Path
from typing import Any
import re

import joblib

from database.database import database
from AiModel.resultInhance import inhanceByai

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "sentiment_model.pkl"
VECTORIZER_PATH = BASE_DIR / "tfidf_vectorizer.pkl"

model = None
vectorizer = None


def load_sentiment_artifacts():
    global model, vectorizer

    if model is None:
        model = joblib.load(MODEL_PATH)

    if vectorizer is None:
        vectorizer = joblib.load(VECTORIZER_PATH)

    return model, vectorizer


def set_sentiment_artifacts(sentiment_model, sentiment_vectorizer):
    global model, vectorizer

    model = sentiment_model
    vectorizer = sentiment_vectorizer


def _clean_text(text: Any) -> str:
    if text is None:
        return ""

    text = str(text)
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"[^a-zA-Z\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()


def get_youtube_comments() -> list[dict]:
    if not isinstance(database, dict):
        return []

    comments = database.get("comments", [])
    if isinstance(comments, list):
        return comments

    return []


def analyze_review(review: str) -> dict:
    load_sentiment_artifacts()

    if model is None or vectorizer is None:
        raise ValueError("Sentiment model and vectorizer must be loaded before calling analyze_review().")

    clean = _clean_text(review)
    vector = vectorizer.transform([clean])
    prediction = model.predict(vector)[0]
    sentiment = "Positive" if prediction == 1 else "Negative"

    confidence = None
    positive_probability = None
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(vector)[0]
        confidence = float(max(probabilities))
        positive_probability = float(probabilities[1]) if len(probabilities) > 1 else float(probabilities[0])

    return {
        "text": review,
        "cleaned_text": clean,
        "sentiment": sentiment,
        "prediction": int(prediction),
        "confidence": confidence,
        "positive_probability": positive_probability,
    }


def analyze_sentiments(comments: list[Any]):
    results = []
    for comment in comments:
        comment_text = comment.get("text", "") if isinstance(comment, dict) else comment
        analyzed = analyze_review(comment_text)
        results.append(
            {
                "Comment": analyzed["text"],
                "Custom Model": analyzed["sentiment"],
                "Confidence": analyzed["confidence"],
            }
        )

    try:
        import pandas as pd

        return pd.DataFrame(results)
    except Exception:
        return results


def summarize_comment_feedback() -> str:

    comments = get_youtube_comments()

    # No comments -> nothing to analyze. Return early instead of asking the LLM
    # to summarize an empty result (which makes it emit un-parseable output).
    if not comments:
        return "No feedback — this video has no comments available to analyze."

    results = analyze_sentiments(comments)

    return inhanceByai(results)

    

   