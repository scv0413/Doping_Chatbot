from pathlib import Path

from app.core.config import Settings, settings


def test_canonical_settings_are_available() -> None:
    assert isinstance(settings, Settings)


def test_legacy_chat_config_module_is_removed() -> None:
    assert not Path("app/chat/config.py").exists()
