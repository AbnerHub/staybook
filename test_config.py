"""Quick validation script for app.core.config module."""
import os

# Set required env vars before importing
os.environ["DATABASE_URL"] = "postgresql://localhost/test"
os.environ["SECRET_KEY"] = "testsecret"

from app.core.config import Settings, settings

# Verify Settings class
assert hasattr(Settings, "model_fields"), "Settings should be a pydantic BaseSettings"

# Verify all fields
assert settings.database_url == "postgresql://localhost/test"
assert settings.secret_key == "testsecret"
assert settings.jwt_algorithm == "HS256"
assert settings.jwt_expiration_minutes == 60
assert settings.app_port == 8000
assert settings.debug is False

print("All config assertions passed!")
