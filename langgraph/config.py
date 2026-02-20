"""Azure OpenAI および各種設定."""

import os

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Azure OpenAI
# ---------------------------------------------------------------------------
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini")

LLM_TEMPERATURE = 0.7

# ---------------------------------------------------------------------------
# 外部API (スタブ)
# ---------------------------------------------------------------------------
BPAAS_API_BASE_URL = os.getenv(
    "BPAAS_API_BASE_URL",
    "https://external.rsi-bpaas-dev.rinfra.ricoh.com",
)
