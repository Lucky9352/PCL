"""Unit tests for utility modules."""

from app.utils.hashing import compute_content_hash
from app.utils.source_credibility import get_source_credibility


class TestContentHash:
    """Tests for SHA-256 content hashing."""

    def test_deterministic(self):
        """Same input → same hash."""
        h1 = compute_content_hash("Test Title", "2024-01-01")
        h2 = compute_content_hash("Test Title", "2024-01-01")
        assert h1 == h2

    def test_case_insensitive(self):
        """Hash should be case-insensitive for title."""
        h1 = compute_content_hash("Test Title", "2024-01-01")
        h2 = compute_content_hash("test title", "2024-01-01")
        assert h1 == h2

    def test_different_titles(self):
        """Different titles → different hashes."""
        h1 = compute_content_hash("Title A", "2024-01-01")
        h2 = compute_content_hash("Title B", "2024-01-01")
        assert h1 != h2

    def test_hash_length(self):
        """SHA-256 hex digest is 64 chars."""
        h = compute_content_hash("Test", None)
        assert len(h) == 64

    def test_none_timestamp(self):
        """Handles None published_at gracefully."""
        h = compute_content_hash("Test Title", None)
        assert isinstance(h, str)
        assert len(h) == 64


class TestSourceCredibility:
    """Tests for source credibility lookup."""

    def test_known_high_source(self):
        """Known high-credibility source."""
        result = get_source_credibility("The Hindu")
        assert result["tier"] == "high"

    def test_known_low_source(self):
        """Known low-credibility source."""
        result = get_source_credibility("Republic World")
        assert result["tier"] == "low"

    def test_unknown_source(self):
        """Unknown source returns 'unknown' tier."""
        result = get_source_credibility("Random Blog XYZ")
        assert result["tier"] == "unknown"

    def test_case_insensitive(self):
        """Lookup should be case-insensitive."""
        result = get_source_credibility("THE HINDU")
        assert result["tier"] == "high"

    def test_empty_source(self):
        """Empty string returns unknown."""
        result = get_source_credibility("")
        assert result["tier"] == "unknown"

    def test_partial_match(self):
        """Partial name matching."""
        result = get_source_credibility("NDTV News")
        assert result["tier"] == "high"
