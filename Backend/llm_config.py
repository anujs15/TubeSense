# llm_config.py

from langchain.chat_models import init_chat_model

_ROUTER_HEADERS = {
    "User-Agent": "claude-cli/1.0.0 (external, cli)",
    "x-app": "cli",
}

DEFAULT_MODEL = "anthropic:claude-opus-4-8"


DEFAULT_TIMEOUT = 180


def make_chat_model(model: str = DEFAULT_MODEL, timeout: int = DEFAULT_TIMEOUT, **kwargs):
    """Return a ChatAnthropic wired for the agentrouter proxy."""
    return init_chat_model(
        model,
        timeout=timeout,
        default_headers=_ROUTER_HEADERS,
        **kwargs,
    )
