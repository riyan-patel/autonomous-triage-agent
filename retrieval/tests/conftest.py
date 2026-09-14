import sys
from pathlib import Path

import pytest
from sqlalchemy import text

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from retrieval.db import get_engine, get_session_factory  # noqa: E402

TEST_DATABASE_URL = "postgresql+psycopg://triage:triage@localhost:5432/triage_agent"


@pytest.fixture(scope="session")
def engine():
    eng = get_engine(TEST_DATABASE_URL)
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1 FROM issues LIMIT 1"))
    except Exception as exc:  # noqa: BLE001 - any connectivity/schema issue means "skip"
        pytest.skip(f"Postgres with the 0001_init.sql schema isn't reachable at {TEST_DATABASE_URL}: {exc}")
    return eng


@pytest.fixture
def db_session(engine):
    """Fresh session per test; rolled back (never committed) so tests never
    need to hand-clean rows and can't pollute each other."""
    session = get_session_factory(engine)()
    yield session
    session.rollback()
    session.close()
