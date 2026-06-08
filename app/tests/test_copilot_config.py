"""Tests for COPILOT_* settings in app.core.config (gh-916)."""

import importlib
import sys

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fresh_settings(**env_overrides):
    """
    Import (or re-import) app.core.config with the given env vars injected,
    returning a *new* Settings() instance (not the module-level singleton).

    We reload the module so pydantic-settings picks up the patched env.
    """
    import app.core.config as mod

    # Reload so any previous module-level singleton does not pollute state.
    importlib.reload(mod)
    return mod.Settings(**env_overrides)


# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------

class TestCopilotDefaults:
    def test_api_key_default_is_none(self):
        from app.core.config import Settings

        s = Settings()
        assert s.COPILOT_API_KEY is None

    def test_base_url_default_is_none(self):
        from app.core.config import Settings

        s = Settings()
        assert s.COPILOT_BASE_URL is None

    def test_model_default(self):
        from app.core.config import Settings

        s = Settings()
        assert s.COPILOT_MODEL == "claude-sonnet-4-6"

    def test_embedding_model_default(self):
        from app.core.config import Settings

        s = Settings()
        assert s.COPILOT_EMBEDDING_MODEL == "text-embedding-3-large"


# ---------------------------------------------------------------------------
# Values loaded from environment variables
# ---------------------------------------------------------------------------

class TestCopilotFromEnv:
    def test_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("COPILOT_API_KEY", "sk-test-1234")
        from app.core.config import Settings

        s = Settings()
        assert s.COPILOT_API_KEY is not None
        assert s.COPILOT_API_KEY.get_secret_value() == "sk-test-1234"

    def test_base_url_from_env(self, monkeypatch):
        monkeypatch.setenv("COPILOT_BASE_URL", "https://hub.example.com/v1")
        from app.core.config import Settings

        s = Settings()
        assert s.COPILOT_BASE_URL == "https://hub.example.com/v1"

    def test_model_override_from_env(self, monkeypatch):
        monkeypatch.setenv("COPILOT_MODEL", "claude-opus-4-5")
        from app.core.config import Settings

        s = Settings()
        assert s.COPILOT_MODEL == "claude-opus-4-5"

    def test_embedding_model_override_from_env(self, monkeypatch):
        monkeypatch.setenv("COPILOT_EMBEDDING_MODEL", "text-embedding-ada-002")
        from app.core.config import Settings

        s = Settings()
        assert s.COPILOT_EMBEDDING_MODEL == "text-embedding-ada-002"


# ---------------------------------------------------------------------------
# SecretStr masking
# ---------------------------------------------------------------------------

class TestSecretStrMasking:
    def test_api_key_masked_in_str(self, monkeypatch):
        monkeypatch.setenv("COPILOT_API_KEY", "sk-supersecret")
        from app.core.config import Settings

        s = Settings()
        # The raw key must NOT appear in the default string representation.
        assert "sk-supersecret" not in str(s)
        assert "sk-supersecret" not in repr(s)

    def test_api_key_masked_in_repr(self, monkeypatch):
        monkeypatch.setenv("COPILOT_API_KEY", "sk-supersecret")
        from app.core.config import Settings

        s = Settings()
        # pydantic-settings renders SecretStr as '**********' in repr.
        assert "**" in repr(s)

    def test_api_key_accessible_via_get_secret_value(self, monkeypatch):
        monkeypatch.setenv("COPILOT_API_KEY", "sk-supersecret")
        from app.core.config import Settings

        s = Settings()
        assert s.COPILOT_API_KEY.get_secret_value() == "sk-supersecret"  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Existing fields still work (non-regression)
# ---------------------------------------------------------------------------

class TestExistingFields:
    def test_project_name(self):
        from app.core.config import Settings

        s = Settings()
        assert s.PROJECT_NAME == "My FastAPI Project"

    def test_version(self):
        from app.core.config import Settings

        s = Settings()
        assert s.VERSION == "1.0.0"

    def test_uvicorn_host(self):
        from app.core.config import Settings

        s = Settings()
        assert s.UVICORN_HOST == "127.0.0.1"

    def test_artifacts_base_dir_is_path(self):
        from pathlib import Path

        from app.core.config import Settings

        s = Settings()
        assert isinstance(s.ARTIFACTS_BASE_DIR, Path)

    def test_module_level_singleton(self):
        from app.core.config import Settings, settings

        assert isinstance(settings, Settings)

    def test_module_constants(self):
        from pathlib import Path

        from app.core.config import AIRFOILS_DIR, REPO_ROOT

        assert isinstance(REPO_ROOT, Path)
        assert isinstance(AIRFOILS_DIR, Path)
        assert AIRFOILS_DIR == REPO_ROOT / "components" / "airfoils"
