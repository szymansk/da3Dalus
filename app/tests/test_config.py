"""Tests for app.core.config — covers Settings class and module-level instance."""


def test_settings_defaults():
    """Settings class should have expected default values."""
    from app.core.config import Settings

    s = Settings()
    assert s.PROJECT_NAME == "My FastAPI Project"
    assert s.VERSION == "1.0.0"
    assert s.UVICORN_HOST == "127.0.0.1"


def test_settings_module_singleton():
    """Module-level `settings` should be a Settings instance."""
    from app.core.config import Settings, settings

    assert isinstance(settings, Settings)
