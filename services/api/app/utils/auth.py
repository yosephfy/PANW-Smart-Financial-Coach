from __future__ import annotations

import hashlib
from typing import Optional
from fastapi import Request


def current_username(request: Request) -> Optional[str]:
    """Return the stateless user id from headers, or None.

    Looks for `X-User-Id` or `X-User`.
    """
    header_user = request.headers.get("x-user-id") or request.headers.get("x-user")
    if header_user:
        return header_user.strip()
    return None


def current_user(request: Request, provided: Optional[str] = None) -> Optional[str]:
    """Preferred current user resolution: header first, then provided fallback."""
    header_user = request.headers.get("x-user-id") or request.headers.get("x-user")
    if header_user:
        return header_user.strip()
    if provided:
        return provided
    return None


def hash_password(password: str, salt: bytes) -> str:
    """PBKDF2-SHA256 password hashing (120k iterations)."""
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000).hex()

