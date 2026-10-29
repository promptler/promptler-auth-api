"""
Test settings. Set before `app` is imported: `app.config.settings` reads the
environment once at import. No database is needed; routes get a fake session.
"""
import os

os.environ.update({
    "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
    "SYNC_DATABASE_URL": "postgresql+psycopg2://test:test@localhost:5432/test",
    "API_SECRET_KEY": "test-secret",
    "API_KEYS": "app-key-old,app-key-new",
    "ADMIN_API_KEYS": "admin-key",
    "APPLE_BUNDLE_ID": "com.promptler.ios.PromptlerV27",
    "APPLE_TEAM_ID": "TEAMID",
    "RATE_LIMIT_PER_MINUTE": "1000",
    "APP_ENV": "test",
})

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db_session
from app.main import app


class _EmptyResult:
    def scalar_one_or_none(self):
        return None

    def scalars(self):
        return self

    def all(self):
        return []


class FakeSession:
    """Answers every lookup with "no such user"; records whether the route touched the DB."""

    def __init__(self):
        self.queried = False

    async def execute(self, *args, **kwargs):
        self.queried = True
        return _EmptyResult()

    def add(self, obj):
        pass

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass

    async def rollback(self):
        pass


@pytest.fixture
def db():
    return FakeSession()


@pytest.fixture
def client(db):
    async def _session():
        yield db

    app.dependency_overrides[get_db_session] = _session
    yield TestClient(app)
    app.dependency_overrides.clear()
