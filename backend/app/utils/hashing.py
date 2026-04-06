"""SHA-256 hashing for article deduplication."""

from __future__ import annotations

import hashlib


def compute_content_hash(title: str, published_at: str | None = None) -> str:
    """Generate a SHA-256 hash of title + published_at for dedup.

    Args:
        title: Article title.
        published_at: Published timestamp as string (ISO format or any).

    Returns:
        64-char hex digest SHA-256 hash.
    """
    payload = f"{title.strip().lower()}|{published_at or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
