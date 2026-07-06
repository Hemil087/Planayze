import google.generativeai as genai
from app.core.config import get_settings

settings = get_settings()

# Configure once at import time
genai.configure(api_key=settings.GEMINI_API_KEY)


def get_gemini_model(model_name: str = "gemini-2.5-flash") -> genai.GenerativeModel:
    """
    Return a configured Gemini GenerativeModel instance.
    Called by the extractor and summary writer.
    """
    return genai.GenerativeModel(model_name)