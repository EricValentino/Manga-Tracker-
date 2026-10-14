import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import main
from database import get_session


@pytest.fixture
def engine():
    # One shared in-memory database per test; StaticPool keeps the same connection
    # so every request in the test sees the same tables.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def client(engine, monkeypatch):
    def override_session():
        with Session(engine) as session:
            yield session

    # Keep the app's startup hook from creating a manga.db file during tests.
    monkeypatch.setattr(main, "create_db_and_tables", lambda: None)
    main.app.dependency_overrides[get_session] = override_session
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()


@pytest.fixture
def saved_manga(client):
    response = client.post("/manga", json={"title": "Vagabond", "genre": "Action, Drama"})
    assert response.status_code == 201
    return response.json()
