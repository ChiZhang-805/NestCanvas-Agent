import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
API_ROOT = Path(__file__).resolve().parents[1]
TEST_DB = Path("/tmp/nestcanvas_agent_test.db")
TEST_STORAGE = Path("/tmp/nestcanvas_agent_storage")

sys.path.insert(0, str(API_ROOT))

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["STORAGE_DIR"] = str(TEST_STORAGE)
os.environ["SYNC_JOBS"] = "true"
os.environ.pop("OPENAI_API_KEY", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def clean_database_and_storage():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    if TEST_STORAGE.exists():
        shutil.rmtree(TEST_STORAGE)
    TEST_STORAGE.mkdir(parents=True, exist_ok=True)
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def fixture_dir() -> Path:
    return ROOT / "tests" / "fixtures"
