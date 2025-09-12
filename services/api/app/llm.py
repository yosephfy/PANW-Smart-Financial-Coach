from __future__ import annotations

import os
from typing import Dict

from .config import get_openai_api_key, get_openai_model, is_llm_enabled

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False


def _client() -> OpenAI:
    if not OPENAI_AVAILABLE:
        raise RuntimeError("openai_not_installed")
    if not is_llm_enabled():
        raise RuntimeError("llm_disabled_in_config")
    key = get_openai_api_key()
    if not key:
        raise RuntimeError("missing_openai_api_key_in_config_or_env")
    return OpenAI(api_key=key)


SYSTEM = (
    "You are a helpful, concise financial coach. Rewrite insights to be friendly, "
    "non-judgmental, and action-oriented. Include concrete numbers from provided data."
    "format title and body separate lines."
    "no bullet points. no lists. no asterisks. no bold. no words like 'Title' and 'Body'"
)


def rewrite_insight_llm(title: str, body: str, data_json: str | None = None, tone: str | None = None) -> Dict:
    # Check if we have an API key
    api_key = get_openai_api_key()

    if not api_key:
        # Fallback: return a mock rewrite when no API key is configured
        tone = tone or "friendly"
        mock_title = f"✨ {title}" if not title.startswith("✨") else title
        mock_body = f"Here's a {tone} insight: {body} Let me know if you need help!"
        return {"title": mock_title[:80], "body": mock_body[:240]}

    client = _client()
    tone = tone or "friendly"
    user = (
        f"Tone: {tone}.\n"
        f"Original title: {title}\n"
        f"Original body: {body}\n"
        f"Data (JSON): {data_json or '{}'}\n"
        "Rewrite the title (<= 80 chars) and body (<= 240 chars). "
        "Keep it specific and cite numbers concisely."
    )
    resp = client.chat.completions.create(
        model=get_openai_model(),
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
        max_tokens=180,
    )
    text = resp.choices[0].message.content or ""
    # naive parse: expect first line title, then body
    parts = text.splitlines()
    new_title = parts[0].strip() if parts else title
    new_body = " ".join(p.strip() for p in parts[1:] if p.strip()) or text
    return {"title": new_title[:80], "body": new_body[:240]}
