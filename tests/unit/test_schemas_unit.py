"""
Unit tests for pydantic schema validation.

These tests do NOT touch the database, network, or the FastAPI app —
they instantiate the schemas directly and check validation behavior.
"""

import pytest
from uuid import uuid4
from datetime import datetime
from pydantic import ValidationError

from app.auth.schemas import (
    UserCreate,
    UserLogin,
    TokenResponse,
    TokenRefresh,
    UserResponse,
)


# ---------------------------------------------------------------------------
# UserCreate
# ---------------------------------------------------------------------------


class TestUserCreate:
    def test_valid_payload_accepted(self):
        user = UserCreate(
            email="alice@example.com",
            password="strongpassword123",
        )
        assert user.email == "alice@example.com"
        assert user.password == "strongpassword123"
        # defaults
        assert user.phone_number is None
        assert user.timezone == "UTC"

    def test_valid_payload_with_optional_fields(self):
        user = UserCreate(
            email="bob@example.com",
            password="strongpassword123",
            phone_number="+919876543210",
            timezone="Asia/Kolkata",
        )
        assert user.phone_number == "+919876543210"
        assert user.timezone == "Asia/Kolkata"

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(email="not-an-email", password="strongpassword123")
        assert "email" in str(exc_info.value).lower()

    def test_password_too_short_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(email="alice@example.com", password="short")
        assert "password" in str(exc_info.value).lower()

    def test_password_exact_min_length_accepted(self):
        # min_length=8 -> boundary case, exactly 8 chars should pass
        user = UserCreate(email="alice@example.com", password="12345678")
        assert user.password == "12345678"

    def test_missing_email_rejected(self):
        with pytest.raises(ValidationError):
            UserCreate(password="strongpassword123")

    def test_missing_password_rejected(self):
        with pytest.raises(ValidationError):
            UserCreate(email="alice@example.com")

    def test_phone_number_optional_defaults_to_none(self):
        user = UserCreate(email="alice@example.com", password="strongpassword123")
        assert user.phone_number is None


# ---------------------------------------------------------------------------
# UserLogin
# ---------------------------------------------------------------------------


class TestUserLogin:
    def test_valid_login_accepted(self):
        login = UserLogin(email="alice@example.com", password="whatever")
        assert login.email == "alice@example.com"
        assert login.password == "whatever"

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            UserLogin(email="not-an-email", password="whatever")

    def test_missing_password_rejected(self):
        with pytest.raises(ValidationError):
            UserLogin(email="alice@example.com")

    def test_login_has_no_min_length_on_password(self):
        # Unlike UserCreate, UserLogin doesn't enforce min_length —
        # this documents that intentional asymmetry (existing user's
        # legacy password could be shorter than the current policy).
        login = UserLogin(email="alice@example.com", password="1")
        assert login.password == "1"


# ---------------------------------------------------------------------------
# TokenResponse
# ---------------------------------------------------------------------------


class TestTokenResponse:
    def test_valid_token_response(self):
        token = TokenResponse(
            access_token="access.jwt.token",
            refresh_token="refresh.jwt.token",
        )
        assert token.token_type == "bearer"  # default applied

    def test_token_type_can_be_overridden(self):
        token = TokenResponse(
            access_token="a",
            refresh_token="r",
            token_type="custom",
        )
        assert token.token_type == "custom"

    def test_missing_access_token_rejected(self):
        with pytest.raises(ValidationError):
            TokenResponse(refresh_token="r")

    def test_missing_refresh_token_rejected(self):
        with pytest.raises(ValidationError):
            TokenResponse(access_token="a")


# ---------------------------------------------------------------------------
# TokenRefresh
# ---------------------------------------------------------------------------


class TestTokenRefresh:
    def test_valid_refresh_token(self):
        payload = TokenRefresh(refresh_token="some.jwt.token")
        assert payload.refresh_token == "some.jwt.token"

    def test_missing_refresh_token_rejected(self):
        with pytest.raises(ValidationError):
            TokenRefresh()


# ---------------------------------------------------------------------------
# UserResponse
# ---------------------------------------------------------------------------


class TestUserResponse:
    def test_valid_user_response(self):
        response = UserResponse(
            id=uuid4(),
            email="alice@example.com",
            role="user",
            phone_number=None,
            email_verified=True,
            phone_verified=False,
            timezone="UTC",
            created_at=datetime.utcnow(),
        )
        assert response.role == "user"
        assert response.email_verified is True
        assert response.phone_verified is False

    def test_from_attributes_works_with_orm_like_object(self):
        # Simulates an ORM model instance (e.g. SQLAlchemy User row)
        # since model_config has from_attributes=True
        class FakeORMUser:
            def __init__(self):
                self.id = uuid4()
                self.email = "alice@example.com"
                self.role = "admin"
                self.phone_number = "+919876543210"
                self.email_verified = True
                self.phone_verified = True
                self.timezone = "Asia/Kolkata"
                self.created_at = datetime.utcnow()

        orm_user = FakeORMUser()
        response = UserResponse.model_validate(orm_user)

        assert response.email == "alice@example.com"
        assert response.role == "admin"
        assert response.phone_number == "+919876543210"

    def test_missing_required_field_rejected(self):
        with pytest.raises(ValidationError):
            UserResponse(
                id=uuid4(),
                email="alice@example.com",
                role="user",
                phone_number=None,
                email_verified=True,
                phone_verified=False,
                timezone="UTC",
                # created_at intentionally omitted
            )

    def test_invalid_uuid_rejected(self):
        with pytest.raises(ValidationError):
            UserResponse(
                id="not-a-uuid",
                email="alice@example.com",
                role="user",
                phone_number=None,
                email_verified=True,
                phone_verified=False,
                timezone="UTC",
                created_at=datetime.utcnow(),
            )
