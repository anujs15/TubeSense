# AiModel/resultInhance.py

from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

from models.chatmodel import ChatResponseModel

load_dotenv()


#llm = init_chat_model("google_genai:gemini-2.5-flash-lite", timeout=30)
base_llm = init_chat_model("mistralai:mistral-medium-latest", timeout=30)

structured_llm = base_llm.with_structured_output(ChatResponseModel)


SYSTEM_PROMPT = (
    "You are given the result of a sentiment analysis of a YouTube video's "
    "comments. Based on this result, give the user feedback on whether the "
    "video is worth watching and whether it is helpful for them. "
    "If you can give feedback, keep it within 100 words. "
    "If there is not enough data to give feedback, respond with 'No feedback' "
    "in 10 words."
)


def inhanceByai(results) -> str:
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Sentiment analysis result:\n{results}"),
    ]

    # Prefer the structured output, but the model sometimes returns prose that
    # can't be coerced into ChatResponseModel (raises OUTPUT_PARSING_FAILURE).
    # Fall back to a plain-text completion so the endpoint never 500s.
    try:
        ai_message = structured_llm.invoke(messages)
        return ai_message.feedback
    except Exception:
        try:
            raw = base_llm.invoke(messages)
            text = getattr(raw, "content", str(raw)).strip()
            return text or "No feedback available."
        except Exception:
            return "No feedback available."
