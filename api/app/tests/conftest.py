import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, MagicMock
from app.models import Base, User
from app.helpers.database import get_db
from app.helpers.auth import get_authenticated_user
from app.helpers.secrets import Secrets

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def mock_migrations():
    with patch("app.migrations.run_all.run_migrations"):
        yield


@pytest.fixture(scope="module")
def test_client():
    # Mock Config
    mock_secrets = MagicMock(spec=Secrets)
    mock_secrets.AppSecretKey = "test-secret-key"
    mock_secrets.Auth0Domain = "test.auth0.com"
    mock_secrets.Auth0Audience = "test-audience"

    mock_secrets_service = MagicMock()
    mock_secrets_service.get_secret.return_value = "test-secret"
    mock_secrets_service.get_customer_secret.return_value = "test-customer-secret"

    with patch("app.helpers.secrets.Secrets", return_value=mock_secrets), patch(
        "app.helpers.secrets_service.SecretsService",
        return_value=mock_secrets_service,
    ):
        from app.main import app

        Base.metadata.create_all(bind=engine)
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_authenticated_user] = lambda: {
            "sub": "test-user-123"
        }

        client = TestClient(app)

    # Create test user
    db = TestingSessionLocal()
    test_user = User(sub="test-user-123")
    db.add(test_user)
    db.commit()
    db.refresh(test_user)
    db.close()

    yield client

    # Tear down
    Base.metadata.drop_all(bind=engine)
