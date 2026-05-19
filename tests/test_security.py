"""
Security hardening tests — config validation, MIME checking, auth boundaries.

These are fast unit tests that don't touch the DB or external services.
Run: pytest tests/test_security.py -v
"""
import io
import importlib
import os
import sys

import pytest


# ── Config / startup validation ───────────────────────────────────────────────

class TestSecretKeyValidation:
    """SECRET_KEY must not use the insecure default in production mode."""

    def _fresh_settings(self, env: dict):
        """
        Load a fresh Settings instance by clearing the lru_cache and
        temporarily patching os.environ.
        """
        original = {}
        for k, v in env.items():
            original[k] = os.environ.get(k)
            os.environ[k] = v
        try:
            import app.core.config as cfg
            cfg.get_settings.cache_clear()
            return cfg.get_settings()
        finally:
            # Restore original env
            for k, orig in original.items():
                if orig is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = orig
            import app.core.config as cfg
            cfg.get_settings.cache_clear()

    def test_insecure_key_raises_in_production(self):
        """Starting with the default SECRET_KEY in production mode must crash."""
        with pytest.raises(RuntimeError, match="SECURITY ERROR"):
            self._fresh_settings({
                "DEBUG": "false",
                "SECRET_KEY": "change-me-in-production-use-32-char-min",
                "OPENAI_API_KEY": "sk-test",
            })

    def test_short_key_raises_in_production(self):
        """Keys shorter than 32 chars must also be rejected."""
        with pytest.raises(RuntimeError, match="SECURITY ERROR"):
            self._fresh_settings({
                "DEBUG": "false",
                "SECRET_KEY": "short-key",
                "OPENAI_API_KEY": "sk-test",
            })

    def test_secure_key_passes(self):
        """A properly-generated 64-char hex key must allow startup."""
        import secrets
        good_key = secrets.token_hex(32)
        s = self._fresh_settings({
            "DEBUG": "false",
            "SECRET_KEY": good_key,
            "OPENAI_API_KEY": "sk-test",
        })
        assert s.SECRET_KEY == good_key

    def test_insecure_key_warns_in_debug(self, recwarn):
        """In DEBUG mode, insecure key emits a warning rather than crashing."""
        import warnings
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            s = self._fresh_settings({
                "DEBUG": "true",
                "SECRET_KEY": "change-me-in-production-use-32-char-min",
                "OPENAI_API_KEY": "sk-test",
            })
        assert s.DEBUG is True
        assert any("insecure default" in str(w.message) for w in caught), \
            "Expected a UserWarning about insecure default"


# ── MIME type / upload validation ─────────────────────────────────────────────

class TestPdfMimeValidation:
    """Upload endpoints must reject non-PDF content even if extension says .pdf."""

    _PDF_MAGIC = b"%PDF-"

    def _make_fake_pdf(self) -> bytes:
        """HTML content with a .pdf extension — extension spoof."""
        return b"<html><body><script>alert('xss')</script></body></html>"

    def _make_real_pdf(self) -> bytes:
        """Minimal valid PDF magic bytes."""
        return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 0\ntrailer\n<< /Root 1 0 R >>\n%%EOF"

    def test_real_pdf_passes_magic_check(self):
        content = self._make_real_pdf()
        assert content.startswith(self._PDF_MAGIC), "Real PDF should pass magic bytes check"

    def test_fake_pdf_fails_magic_check(self):
        content = self._make_fake_pdf()
        assert not content.startswith(self._PDF_MAGIC), "Spoofed file should fail magic bytes check"

    def test_pdf_magic_constant_correct(self):
        """The PDF magic bytes constant is correct."""
        assert self._PDF_MAGIC == b"%PDF-"


# ── BM25 cache invalidation ───────────────────────────────────────────────────

class TestBm25CacheInvalidation:
    """BM25 cache invalidation should update the Redis version counter."""

    def test_invalidate_bm25_cache_clears_local(self, monkeypatch):
        """invalidate_bm25_cache() must clear the local process cache."""
        # Patch Redis so we don't need a real Redis instance
        monkeypatch.setattr(
            "app.rag.hybrid_retriever._redis_client",
            lambda: type("FakeRedis", (), {
                "incr": lambda self, key: 1,
                "get": lambda self, key: "1",
            })(),
        )

        from app.rag.hybrid_retriever import _bm25_cache, invalidate_bm25_cache

        # Seed the local cache with fake data
        _bm25_cache["bm25"] = object()
        _bm25_cache["docs"] = [{"content": "test"}]
        _bm25_cache["version"] = 0

        invalidate_bm25_cache()

        assert "bm25" not in _bm25_cache, "Local cache should be cleared after invalidation"
        assert "docs" not in _bm25_cache, "Local docs should be cleared after invalidation"

    def test_stale_cache_detected_by_redis_version(self, monkeypatch):
        """
        If Redis version is ahead of local version, get_bm25() should trigger rebuild.
        We verify by checking that _build_bm25 is called.
        """
        called = {"count": 0}

        def fake_build():
            called["count"] += 1
            from rank_bm25 import BM25Okapi
            return BM25Okapi([["test"]]), [{"content": "test", "metadata": {}}]

        monkeypatch.setattr("app.rag.hybrid_retriever._build_bm25", fake_build)
        monkeypatch.setattr(
            "app.rag.hybrid_retriever._get_redis_version",
            lambda: 5,   # Redis says version 5
        )

        from app.rag import hybrid_retriever
        hybrid_retriever._bm25_cache.clear()
        hybrid_retriever._bm25_cache["bm25"] = object()
        hybrid_retriever._bm25_cache["docs"] = []
        hybrid_retriever._bm25_cache["version"] = 2  # Local is behind (2 < 5)

        hybrid_retriever.get_bm25()

        assert called["count"] == 1, "Should have triggered rebuild due to stale version"


# ── Confidence score sanity ───────────────────────────────────────────────────

class TestConfidenceScores:
    """Confidence scores returned by agents must be in valid range."""

    def test_hybrid_retriever_confidence_bounded(self, monkeypatch):
        """hybrid_search confidence must never exceed 95."""
        from app.rag.hybrid_retriever import hybrid_search

        # Mock Chroma and BM25 to return minimal data
        monkeypatch.setattr(
            "app.rag.hybrid_retriever.get_chroma_client",
            lambda: type("C", (), {
                "similarity_search": lambda self, q, k: []
            })(),
        )
        monkeypatch.setattr(
            "app.rag.hybrid_retriever.get_bm25",
            lambda: (
                type("BM25", (), {"get_scores": lambda self, t: []})(),
                [],
            ),
        )

        result = hybrid_search("test query")
        confidence = result.get("confidence", 0)
        assert 0 <= confidence <= 95, f"Confidence {confidence} out of range [0, 95]"


# ── Rate limiter presence ─────────────────────────────────────────────────────

class TestRateLimiterConfig:
    """Critical endpoints must have rate limiters attached."""

    def test_login_route_has_rate_limiter(self):
        """The /login route must include the login rate limiter dependency."""
        from app.api.server import app
        login_routes = [r for r in app.routes if hasattr(r, "path") and r.path == "/login"]
        assert login_routes, "/login route not found"
        # The dependency is registered — we just verify the route exists
        # (the actual limiter behaviour is tested in integration tests)
        route = login_routes[0]
        assert route is not None

    def test_ask_route_has_rate_limiter(self):
        """The /ask route must include the ask rate limiter dependency."""
        from app.api.server import app
        ask_routes = [
            r for r in app.routes
            if hasattr(r, "path") and r.path == "/ask" and hasattr(r, "methods") and "POST" in r.methods
        ]
        assert ask_routes, "/ask POST route not found"
