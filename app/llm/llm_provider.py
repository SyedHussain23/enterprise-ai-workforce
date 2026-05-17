# app/llm/llm_provider.py
from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.core.config import settings

llm = ChatOpenAI(
    model=settings.OPENAI_MODEL,
    temperature=0.3,
    api_key=settings.OPENAI_API_KEY,
)
