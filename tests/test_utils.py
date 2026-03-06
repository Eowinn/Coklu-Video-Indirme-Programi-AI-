"""Utils modülü testleri."""

import pytest
from src.utils import truncate_text


class TestTruncateText:
    """truncate_text fonksiyonu testleri."""

    def test_short_text_unchanged(self):
        """Kısa metin değiştirilmemeli."""
        assert truncate_text("hello", 10) == "hello"

    def test_exact_length_unchanged(self):
        """Tam uzunluktaki metin değiştirilmemeli."""
        assert truncate_text("hello", 5) == "hello"

    def test_long_text_truncated(self):
        """Uzun metin kesilmeli."""
        result = truncate_text("hello world", 5)
        assert result == "hello…"
        assert len(result) == 6  # 5 karakter + …

    def test_default_length(self):
        """Varsayılan uzunluk 60 olmalı."""
        short = "a" * 60
        long = "a" * 61
        assert truncate_text(short) == short
        assert truncate_text(long) == "a" * 60 + "…"
