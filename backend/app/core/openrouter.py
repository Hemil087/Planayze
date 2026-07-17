import httpx
import logging
from openai import OpenAI
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_client: OpenAI | None = None


def get_openrouter_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            http_client=httpx.Client(verify=False),
        )
        logger.info(f"OpenRouter client initialised — model={settings.OPENROUTER_MODEL}")
    return _client