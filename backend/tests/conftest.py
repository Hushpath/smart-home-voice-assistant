import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.init_db import seed_initial_data
from app.db.session import Base, get_db
from app.main import app
from app.services import home_actions


@pytest.fixture(autouse=True)
def disable_real_weather_requests(monkeypatch, tmp_path):
    monkeypatch.setenv("ASR_CONFIG_PATH", str(tmp_path / "asr_config.json"))
    home_actions.clear_weather_cache()

    def offline_weather(city_name):
        raise ValueError(f"real weather disabled in tests: {city_name}")

    monkeypatch.setattr(home_actions, "_fetch_open_meteo_weather", offline_weather)
    yield
    home_actions.clear_weather_cache()


@pytest.fixture()
def testing_session_factory(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = session_factory()
    try:
        seed_initial_data(db)
    finally:
        db.close()

    yield session_factory

    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(testing_session_factory):
    def override_get_db():
        db = testing_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "test123456"},
    )
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
