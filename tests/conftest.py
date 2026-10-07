import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    certificate_dir = Path("storage/certificates")
    if certificate_dir.exists():
        shutil.rmtree(certificate_dir)
    certificate_dir.mkdir(parents=True)
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
