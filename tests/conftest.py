"""Pytest fixtures for API tests.

This module provides two fixture groups:
- engine/session fixtures that create and wire an isolated per-test database
- object/data fixtures that load calibration payloads and create test records
"""

from pathlib import Path
import uuid
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from qupboard_graphql.api.app import get_app
from qupboard_graphql.db.database import Base
from qupboard_graphql.db import session as session_module
from qupboard_graphql.db.models import HardwareModelORM
from qupboard_graphql.schemas.hardware_model import HardwareModel

data_path = Path(__file__).parent / "data"

_JSON_HEADERS = {"Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Engine/session fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_engine() -> Iterator[Engine]:
    """Create an isolated in-memory engine per test function."""
    engine: Engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine: Engine) -> Iterator[Session]:
    """Provide a SQLAlchemy session bound to the current test engine."""
    SessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def test_client(db_engine: Engine) -> Iterator[TestClient]:
    """
    TestClient that uses the production get_db dependency while tests
    temporarily swap the session module engine to a per-test SQLite engine.
    """
    original_engine: Engine = session_module.engine
    session_module.engine = db_engine

    app = get_app()
    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            yield client
    finally:
        session_module.engine = original_engine


# ---------------------------------------------------------------------------
# Object/data fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def raw_calibration() -> str:
    """Load the raw calibration JSON once for the entire test session."""
    with open(data_path / "calibration_pydantic.json") as f:
        return f.read()


@pytest.fixture(scope="session")
def hardware_model(raw_calibration: str) -> HardwareModel:
    """Parsed and validated HardwareModel, shared across the session."""
    return HardwareModel.model_validate_json(raw_calibration)


@pytest.fixture()
def hardware_model_uuid(test_client: TestClient, raw_calibration: str, db_session: Session) -> str:
    # Create the model and capture its UUID
    post_response = test_client.post("/rest/logical-hardware", content=raw_calibration, headers=_JSON_HEADERS)
    assert post_response.status_code == 201
    model_uuid = post_response.json()

    # Verify the POST wrote the row to the current test database.
    assert HardwareModelORM.get_by_uuid(db_session, uuid.UUID(model_uuid)) is not None
    return model_uuid
