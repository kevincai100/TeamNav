from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.db import create_database, init_models
from app.main import create_app


@pytest.fixture
async def client(tmp_path) -> AsyncIterator[AsyncClient]:
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        app_url="http://test-web",
        secret_key="test-secret-key-with-at-least-32-characters",
        cookie_secure=False,
    )
    database = create_database(settings.database_url)
    await init_models(database.engine)
    app = create_app(settings=settings, database=database)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http
    await database.engine.dispose()
