"""Unit tests for database engine/session utilities."""

import pytest

from qupboard_graphql.db import session as session_module


@pytest.fixture()
def patched_create_engine(monkeypatch) -> tuple[dict[str, object], object]:
    """Patch session.create_engine and expose captured call data plus sentinel engine."""
    captured: dict[str, object] = {}
    sentinel_engine = object()

    def fake_create_engine(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return sentinel_engine

    monkeypatch.setattr(session_module, "create_engine", fake_create_engine)
    return captured, sentinel_engine


def test_get_engine_sets_sqlite_connect_args(patched_create_engine):
    """SQLite engines should disable thread checks for app/test usage."""
    captured, sentinel_engine = patched_create_engine

    engine = session_module.get_engine("sqlite:///tmp.db")

    assert engine is sentinel_engine
    assert captured["url"] == "sqlite:///tmp.db"
    assert captured["kwargs"] == {"connect_args": {"check_same_thread": False}}


@pytest.mark.parametrize(
    "database_url",
    [
        "sqlite://",
        "sqlite:///tmp.db",
        "sqlite+pysqlite:///tmp.db",
    ],
)
def test_get_engine_sets_sqlite_connect_args_for_sqlite_variants(patched_create_engine, database_url: str):
    """All SQLite URL variants should receive check_same_thread=False."""
    captured, sentinel_engine = patched_create_engine

    engine = session_module.get_engine(database_url)

    assert engine is sentinel_engine
    assert captured["url"] == database_url
    assert captured["kwargs"] == {"connect_args": {"check_same_thread": False}}


def test_get_engine_uses_empty_connect_args_for_non_sqlite(patched_create_engine):
    """Non-SQLite backends should not receive SQLite-only connect args."""
    captured, sentinel_engine = patched_create_engine

    engine = session_module.get_engine("postgresql://user:pass@localhost:5432/mydb")

    assert engine is sentinel_engine
    assert captured["url"] == "postgresql://user:pass@localhost:5432/mydb"
    assert captured["kwargs"] == {"connect_args": {}}


def test_get_engine_uses_settings_database_url_by_default(monkeypatch, patched_create_engine):
    """If no URL is provided, get_engine should use settings.DATABASE_URL."""
    captured, sentinel_engine = patched_create_engine
    default_url = "sqlite:///default.db"

    monkeypatch.setattr(session_module.settings, "DATABASE_URL", default_url)

    engine = session_module.get_engine()

    assert engine is sentinel_engine
    assert captured["url"] == default_url
    assert captured["kwargs"] == {"connect_args": {"check_same_thread": False}}
