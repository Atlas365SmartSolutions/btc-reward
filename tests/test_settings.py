from __future__ import annotations

from config.settings.base import BASE_DIR, database_from_url


def test_sqlite_relative_database_url_resolves_under_project_root() -> None:
    config = database_from_url("sqlite:///db.sqlite3")

    assert config["ENGINE"] == "django.db.backends.sqlite3"
    assert config["NAME"] == BASE_DIR / "db.sqlite3"


def test_sqlite_memory_database_url_is_preserved() -> None:
    config = database_from_url("sqlite:///:memory:")

    assert config["NAME"] == ":memory:"


def test_sqlite_windows_absolute_database_url_is_not_prefixed_with_slash() -> None:
    config = database_from_url("sqlite:///C:/data/btc.sqlite3")

    assert config["NAME"] == "C:/data/btc.sqlite3"


def test_sqlite_unix_absolute_database_url_stays_absolute() -> None:
    config = database_from_url("sqlite:////var/lib/btc/db.sqlite3")

    assert config["NAME"] == "/var/lib/btc/db.sqlite3"


def test_postgres_database_url_preserves_sslmode_option() -> None:
    config = database_from_url("postgres://user:pass@example.com:19622/defaultdb?sslmode=require")

    assert config["ENGINE"] == "django.db.backends.postgresql"
    assert config["NAME"] == "defaultdb"
    assert config["HOST"] == "example.com"
    assert config["PORT"] == "19622"
    assert config["OPTIONS"] == {"sslmode": "require"}
