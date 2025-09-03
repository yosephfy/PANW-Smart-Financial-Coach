from __future__ import annotations

import os
from typing import Dict

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False


def _client() -> OpenAI:
    if not OPENAI_AVAILABLE:
        raise RuntimeError("openai_not_installed")
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("missing_OPENAI_API_KEY")
    return OpenAI(api_key=key)


SYSTEM = (
    "You are a helpful, concise financial coach. Rewrite insights to be friendly, "
    "non-judgmental, and action-oriented. Include concrete numbers from provided data."
)


def rewrite_insight_llm(title: str, body: str, data_json: str | None = None, tone: str | None = None) -> Dict:
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
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
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

