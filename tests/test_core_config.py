from app.core.config import settings as legacy_settings
from app.core.config import settings


def test_legacy_config_reexports_canonical_settings() -> None:
    assert legacy_settings is settings
