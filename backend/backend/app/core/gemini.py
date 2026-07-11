import json
import logging

import vertexai
from vertexai.generative_models import GenerativeModel
from google.oauth2 import service_account

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_INITIALIZED = False


def _init_vertexai() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return

    credentials = None
    if settings.GOOGLE_APPLICATION_CREDENTIALS_JSON:
        info = json.loads(settings.GOOGLE_APPLICATION_CREDENTIALS_JSON)
        credentials = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )

    vertexai.init(
        project=settings.PROJECT_ID,
        location=settings.REGION,
        credentials=credentials,
    )
    _INITIALIZED = True
    logger.info(f"Vertex AI initialized — project={settings.PROJECT_ID}")


def get_gemini_model() -> GenerativeModel:
    _init_vertexai()
    return GenerativeModel(model_name=settings.GEMINI_MODEL)
