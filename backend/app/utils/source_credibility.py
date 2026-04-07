"""Indian news source credibility tiers.

Curated database of 100+ Indian and international news sources mapped to
credibility tiers and political bias tendency.  Used by the trust-score
computation and the political-lean estimator.

Tier assignment methodology (documented in docs/METHODOLOGY.md §3):
  - high   → Established editorial processes, corrections policy,
              recognised by Press Council of India or international bodies
  - medium → Known outlets with occasional quality concerns or
              documented editorial slant
  - low    → Tabloid-style, known for sensationalism, frequent
              misinformation flags by IFCN-certified fact-checkers

Bias tendency follows a 7-point scale mapped to numeric values:
  far-left=-1.0  left=-0.67  center-left=-0.33  center=0.0
  center-right=0.33  right=0.67  far-right=1.0
"""

from __future__ import annotations

BIAS_NUMERIC: dict[str, float] = {
    "far-left": -1.0,
    "left": -0.67,
    "center-left": -0.33,
    "center": 0.0,
    "center-right": 0.33,
    "right": 0.67,
    "far-right": 1.0,
    "unclassified": 0.0,
}

TIER_NUMERIC: dict[str, float] = {
    "high": 0.9,
    "medium": 0.6,
    "low": 0.3,
    "unknown": 0.5,
}

# source name (lowercase) → {tier, bias, category}
SOURCE_CREDIBILITY: dict[str, dict[str, str]] = {
    # ── High credibility ── National broadsheets & wire services
    "the hindu": {"tier": "high", "bias": "center-left", "category": "national"},
    "the indian express": {"tier": "high", "bias": "center", "category": "national"},
    "indian express": {"tier": "high", "bias": "center", "category": "national"},
    "hindustan times": {"tier": "high", "bias": "center", "category": "national"},
    "ndtv": {"tier": "high", "bias": "center-left", "category": "national"},
    "the wire": {"tier": "high", "bias": "left", "category": "digital-first"},
    "scroll.in": {"tier": "high", "bias": "left", "category": "digital-first"},
    "scroll": {"tier": "high", "bias": "left", "category": "digital-first"},
    "the print": {"tier": "high", "bias": "center", "category": "digital-first"},
    "bbc news": {"tier": "high", "bias": "center", "category": "international"},
    "bbc": {"tier": "high", "bias": "center", "category": "international"},
    "reuters": {"tier": "high", "bias": "center", "category": "international"},
    "associated press": {"tier": "high", "bias": "center", "category": "international"},
    "ap": {"tier": "high", "bias": "center", "category": "international"},
    "the economic times": {"tier": "high", "bias": "center-right", "category": "business"},
    "economic times": {"tier": "high", "bias": "center-right", "category": "business"},
    "livemint": {"tier": "high", "bias": "center-right", "category": "business"},
    "mint": {"tier": "high", "bias": "center-right", "category": "business"},
    "business standard": {"tier": "high", "bias": "center", "category": "business"},
    "pti": {"tier": "high", "bias": "center", "category": "wire"},
    "press trust of india": {"tier": "high", "bias": "center", "category": "wire"},
    "ani": {"tier": "high", "bias": "center", "category": "wire"},
    "the quint": {"tier": "high", "bias": "center-left", "category": "digital-first"},
    "deccan herald": {"tier": "high", "bias": "center", "category": "regional"},
    "the telegraph": {"tier": "high", "bias": "center-left", "category": "national"},
    "the statesman": {"tier": "high", "bias": "center", "category": "national"},
    "frontline": {"tier": "high", "bias": "left", "category": "magazine"},
    "down to earth": {"tier": "high", "bias": "center-left", "category": "niche"},
    "afp": {"tier": "high", "bias": "center", "category": "international"},
    "al jazeera": {"tier": "high", "bias": "center-left", "category": "international"},
    "the guardian": {"tier": "high", "bias": "center-left", "category": "international"},
    "new york times": {"tier": "high", "bias": "center-left", "category": "international"},
    "washington post": {"tier": "high", "bias": "center-left", "category": "international"},
    "the diplomat": {"tier": "high", "bias": "center", "category": "international"},
    "south china morning post": {"tier": "high", "bias": "center", "category": "international"},
    "bloomberg": {"tier": "high", "bias": "center", "category": "business"},
    "financial times": {"tier": "high", "bias": "center", "category": "business"},
    "the lancet": {"tier": "high", "bias": "center", "category": "niche"},
    "nature": {"tier": "high", "bias": "center", "category": "niche"},
    "caravan magazine": {"tier": "high", "bias": "center-left", "category": "magazine"},
    "the caravan": {"tier": "high", "bias": "center-left", "category": "magazine"},
    "article 14": {"tier": "high", "bias": "center-left", "category": "digital-first"},
    # ── Medium credibility ── Mainstream with editorial concerns
    "times of india": {"tier": "medium", "bias": "center-right", "category": "national"},
    "india today": {"tier": "medium", "bias": "center", "category": "national"},
    "news18": {"tier": "medium", "bias": "center-right", "category": "national"},
    "firstpost": {"tier": "medium", "bias": "center-right", "category": "digital-first"},
    "outlook india": {"tier": "medium", "bias": "center-left", "category": "magazine"},
    "outlook": {"tier": "medium", "bias": "center-left", "category": "magazine"},
    "the free press journal": {"tier": "medium", "bias": "center", "category": "regional"},
    "dna india": {"tier": "medium", "bias": "center-right", "category": "national"},
    "dna": {"tier": "medium", "bias": "center-right", "category": "national"},
    "zee news": {"tier": "medium", "bias": "right", "category": "national"},
    "cnbc-tv18": {"tier": "medium", "bias": "center-right", "category": "business"},
    "cnbctv18": {"tier": "medium", "bias": "center-right", "category": "business"},
    "moneycontrol": {"tier": "medium", "bias": "center", "category": "business"},
    "wion": {"tier": "medium", "bias": "center-right", "category": "national"},
    "the new indian express": {"tier": "medium", "bias": "center", "category": "regional"},
    "new indian express": {"tier": "medium", "bias": "center", "category": "regional"},
    "mid-day": {"tier": "medium", "bias": "center", "category": "regional"},
    "deccan chronicle": {"tier": "medium", "bias": "center", "category": "regional"},
    "the pioneer": {"tier": "medium", "bias": "right", "category": "national"},
    "daily pioneer": {"tier": "medium", "bias": "right", "category": "national"},
    "asian age": {"tier": "medium", "bias": "center", "category": "national"},
    "business today": {"tier": "medium", "bias": "center", "category": "business"},
    "news minute": {"tier": "medium", "bias": "center-left", "category": "digital-first"},
    "the news minute": {"tier": "medium", "bias": "center-left", "category": "digital-first"},
    "newslaundry": {"tier": "medium", "bias": "center-left", "category": "digital-first"},
    "the morning context": {"tier": "medium", "bias": "center", "category": "digital-first"},
    "the ken": {"tier": "medium", "bias": "center", "category": "business"},
    "aaj tak": {"tier": "medium", "bias": "center-right", "category": "national"},
    "india tv": {"tier": "medium", "bias": "center-right", "category": "national"},
    "abp news": {"tier": "medium", "bias": "center", "category": "national"},
    "ndtv profit": {"tier": "medium", "bias": "center", "category": "business"},
    "the lallantop": {"tier": "medium", "bias": "center", "category": "digital-first"},
    "news9": {"tier": "medium", "bias": "center-right", "category": "national"},
    "mirror now": {"tier": "medium", "bias": "center", "category": "national"},
    "times now": {"tier": "medium", "bias": "center-right", "category": "national"},
    "et now": {"tier": "medium", "bias": "center", "category": "business"},
    "theprint": {"tier": "medium", "bias": "center", "category": "digital-first"},
    "inshorts": {"tier": "medium", "bias": "center", "category": "aggregator"},
    "dailyhunt": {"tier": "medium", "bias": "center", "category": "aggregator"},
    # ── Business / Finance outlets ────────────
    "moneycontrol.com": {"tier": "medium", "bias": "center", "category": "business"},
    "cnbc tv18": {"tier": "medium", "bias": "center-right", "category": "business"},
    "finology": {"tier": "medium", "bias": "center", "category": "business"},
    "stocktwits": {"tier": "medium", "bias": "center", "category": "business"},
    "investing.com": {"tier": "medium", "bias": "center", "category": "business"},
    "marketwatch": {"tier": "medium", "bias": "center", "category": "business"},
    "yahoo finance": {"tier": "medium", "bias": "center", "category": "business"},
    "fortune": {"tier": "medium", "bias": "center", "category": "business"},
    "forbes": {"tier": "medium", "bias": "center-right", "category": "business"},
    "forbes india": {"tier": "medium", "bias": "center-right", "category": "business"},
    "cnbc": {"tier": "medium", "bias": "center", "category": "business"},
    "benzinga": {"tier": "medium", "bias": "center", "category": "business"},
    "techcrunch": {"tier": "medium", "bias": "center-left", "category": "tech"},
    "the verge": {"tier": "medium", "bias": "center-left", "category": "tech"},
    "wired": {"tier": "medium", "bias": "center-left", "category": "tech"},
    "gadgets 360": {"tier": "medium", "bias": "center", "category": "tech"},
    "gadgets360": {"tier": "medium", "bias": "center", "category": "tech"},
    "inc42": {"tier": "medium", "bias": "center", "category": "tech"},
    "entrackr": {"tier": "medium", "bias": "center", "category": "tech"},
    "yourstory": {"tier": "medium", "bias": "center", "category": "tech"},
    "espncricinfo": {"tier": "medium", "bias": "center", "category": "sports"},
    "cricbuzz": {"tier": "medium", "bias": "center", "category": "sports"},
    "sportskeeda": {"tier": "medium", "bias": "center", "category": "sports"},
    "sportstar": {"tier": "medium", "bias": "center", "category": "sports"},
    "the indian premier league": {"tier": "medium", "bias": "center", "category": "sports"},
    "espn": {"tier": "medium", "bias": "center", "category": "sports"},
    # ── Entertainment / lifestyle ─────────────
    "bollywood hungama": {"tier": "medium", "bias": "center", "category": "entertainment"},
    "filmfare": {"tier": "medium", "bias": "center", "category": "entertainment"},
    "pinkvilla": {"tier": "medium", "bias": "center", "category": "entertainment"},
    "koimoi": {"tier": "low", "bias": "center", "category": "entertainment"},
    # ── Auto ──────────────────────────────────
    "autocar india": {"tier": "medium", "bias": "center", "category": "auto"},
    "overdrive": {"tier": "medium", "bias": "center", "category": "auto"},
    "zigwheels": {"tier": "medium", "bias": "center", "category": "auto"},
    "carandbike": {"tier": "medium", "bias": "center", "category": "auto"},
    # ── Science / health ──────────────────────
    "science daily": {"tier": "medium", "bias": "center", "category": "science"},
    "the conversation": {"tier": "high", "bias": "center", "category": "science"},
    "who": {"tier": "high", "bias": "center", "category": "health"},
    "world health organization": {"tier": "high", "bias": "center", "category": "health"},
    # ── Low credibility ── Known for sensationalism / misinformation
    "republic world": {"tier": "low", "bias": "right", "category": "national"},
    "republic tv": {"tier": "low", "bias": "right", "category": "national"},
    "opindia": {"tier": "low", "bias": "far-right", "category": "digital-first"},
    "swarajya": {"tier": "low", "bias": "right", "category": "digital-first"},
    "the logical indian": {"tier": "low", "bias": "left", "category": "digital-first"},
    "national herald": {"tier": "low", "bias": "left", "category": "national"},
    "pgurus": {"tier": "low", "bias": "far-right", "category": "digital-first"},
    "postcard news": {"tier": "low", "bias": "far-right", "category": "digital-first"},
    "kreately": {"tier": "low", "bias": "far-right", "category": "digital-first"},
    "the quint opinion": {"tier": "low", "bias": "left", "category": "digital-first"},
    "newsclick": {"tier": "low", "bias": "far-left", "category": "digital-first"},
    "true scoop": {"tier": "low", "bias": "center", "category": "digital-first"},
    "one india": {"tier": "low", "bias": "center-right", "category": "digital-first"},
    "india.com": {"tier": "low", "bias": "center", "category": "digital-first"},
    "jagran josh": {"tier": "low", "bias": "center-right", "category": "digital-first"},
    "zee hindustan": {"tier": "low", "bias": "right", "category": "national"},
    "sudarshan news": {"tier": "low", "bias": "far-right", "category": "national"},
}


def get_source_credibility(source_name: str) -> dict[str, str]:
    """Look up credibility tier, bias tendency, and category for a source.

    Args:
        source_name: The news source name (case-insensitive).

    Returns:
        Dict with 'tier', 'bias', and 'category' keys.
    """
    if not source_name:
        return {"tier": "unknown", "bias": "unclassified", "category": "unknown"}

    key = source_name.strip().lower()

    if key in SOURCE_CREDIBILITY:
        return SOURCE_CREDIBILITY[key]

    for known_source, data in SOURCE_CREDIBILITY.items():
        if known_source in key or key in known_source:
            return data

    return {"tier": "unknown", "bias": "unclassified", "category": "unknown"}


def get_source_bias_numeric(source_name: str) -> float:
    """Return numeric bias score for a source on [-1, 1] scale.

    -1 = far-left, 0 = center, +1 = far-right.
    """
    info = get_source_credibility(source_name)
    return BIAS_NUMERIC.get(info["bias"], 0.0)


def get_source_tier_numeric(source_name: str) -> float:
    """Return numeric credibility score for a source on [0, 1] scale."""
    info = get_source_credibility(source_name)
    return TIER_NUMERIC.get(info["tier"], 0.5)
