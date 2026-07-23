from pathlib import Path


def test_documentation_uses_top_level_categories() -> None:
    assert not list(Path("app/chat/docs").glob("*.md"))

    for category in ("architecture", "operations", "evaluation"):
        assert Path("docs", category).is_dir()


def test_local_archive_is_ignored_from_git() -> None:
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "local_archive/" in gitignore
