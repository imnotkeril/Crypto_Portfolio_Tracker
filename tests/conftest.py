import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils import database  # noqa: E402


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Throwaway SQLite DB; the real data/portfolio.db is never touched."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))
    database.init_database()
    return database
