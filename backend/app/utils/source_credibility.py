"""Indian news source credibility tiers.

Pre-built static dictionary mapping known Indian news sources
to credibility tiers for the trust score computation.

Tiers:
  - high: Established, editorial-process-driven outlets
  - medium: Known outlets with occasional quality concerns
  - low: Tabloid / known for sensationalism
  - unknown: Unrecognized source
"""

from __future__ import annotations

# Source name (lowercase) → credibility tier + optional bias tendency
SOURCE_CREDIBILITY: dict[str, dict[str, str]] = {
    # ── High credibility ──────────────────────────
    "the hindu": {"tier": "high", "bias": "center-left"},
    "the indian express": {"tier": "high", "bias": "center"},
    "hindustan times": {"tier": "high", "bias": "center"},
    "ndtv": {"tier": "high", "bias": "center-left"},
    "the wire": {"tier": "high", "bias": "left"},
    "scroll.in": {"tier": "high", "bias": "left"},
    "the print": {"tier": "high", "bias": "center"},
    "bbc news": {"tier": "high", "bias": "center"},
    "bbc": {"tier": "high", "bias": "center"},
    "reuters": {"tier": "high", "bias": "center"},
    "associated press": {"tier": "high", "bias": "center"},
    "the economic times": {"tier": "high", "bias": "center-right"},
    "livemint": {"tier": "high", "bias": "center-right"},
    "business standard": {"tier": "high", "bias": "center"},
    "mint": {"tier": "high", "bias": "center-right"},
    "pti": {"tier": "high", "bias": "center"},
    "press trust of india": {"tier": "high", "bias": "center"},
    "ani": {"tier": "high", "bias": "center"},
    "the quint": {"tier": "high", "bias": "center-left"},
    "deccan herald": {"tier": "high", "bias": "center"},
    "the telegraph": {"tier": "high", "bias": "center-left"},
    "the statesman": {"tier": "high", "bias": "center"},
    "frontline": {"tier": "high", "bias": "left"},
    "down to earth": {"tier": "high", "bias": "center-left"},
    "indian express": {"tier": "high", "bias": "center"},
    # ── Medium credibility ────────────────────────
    "times of india": {"tier": "medium", "bias": "center-right"},
    "india today": {"tier": "medium", "bias": "center"},
    "news18": {"tier": "medium", "bias": "center-right"},
    "firstpost": {"tier": "medium", "bias": "center-right"},
    "outlook india": {"tier": "medium", "bias": "center-left"},
    "the free press journal": {"tier": "medium", "bias": "center"},
    "dna india": {"tier": "medium", "bias": "center-right"},
    "zee news": {"tier": "medium", "bias": "right"},
    "cnbc-tv18": {"tier": "medium", "bias": "center-right"},
    "moneycontrol": {"tier": "medium", "bias": "center"},
    "wion": {"tier": "medium", "bias": "center-right"},
    "the new indian express": {"tier": "medium", "bias": "center"},
    "mid-day": {"tier": "medium", "bias": "center"},
    "deccan chronicle": {"tier": "medium", "bias": "center"},
    "the pioneer": {"tier": "medium", "bias": "right"},
    "daily pioneer": {"tier": "medium", "bias": "right"},
    "asian age": {"tier": "medium", "bias": "center"},
    "business today": {"tier": "medium", "bias": "center"},
    # ── Low credibility ───────────────────────────
    "republic world": {"tier": "low", "bias": "right"},
    "republic tv": {"tier": "low", "bias": "right"},
    "opindia": {"tier": "low", "bias": "right"},
    "swarajya": {"tier": "low", "bias": "right"},
    "the logical indian": {"tier": "low", "bias": "left"},
    "news minute": {"tier": "medium", "bias": "center-left"},
    "national herald": {"tier": "low", "bias": "left"},
    "pgurus": {"tier": "low", "bias": "right"},
    "newslaundry": {"tier": "medium", "bias": "center-left"},
}


def get_source_credibility(source_name: str) -> dict[str, str]:
    """Look up credibility tier and bias tendency for a source.

    Args:
        source_name: The news source name (case-insensitive).

    Returns:
        Dict with 'tier' and 'bias' keys.
    """
    if not source_name:
        return {"tier": "unknown", "bias": "unclassified"}

    key = source_name.strip().lower()

    # Direct match
    if key in SOURCE_CREDIBILITY:
        return SOURCE_CREDIBILITY[key]

    # Partial match — check if source name contains a known key
    for known_source, data in SOURCE_CREDIBILITY.items():
        if known_source in key or key in known_source:
            return data

    return {"tier": "unknown", "bias": "unclassified"}
