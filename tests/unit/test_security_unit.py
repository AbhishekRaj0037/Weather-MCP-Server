"""
Unit tests for app/auth/security.py

These are true unit tests: no database, no network, no FastAPI app.
We test the pure functions in isolation - hashing, JWT encode/decode,
and password verification logic.
"""

import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.auth.security import (
    hash_token,
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.config import settings


# ---------------------------------------------------------------------------
# hash_token
# ---------------------------------------------------------------------------


class TestHashToken:
    def test_returns_sha256_hex_digest(self):
        token = "my-refresh-token"
        expected = hashlib.sha256(token.encode()).hexdigest()
        assert hash_token(token) == expected

    def test_is_deterministic(self):
        # Same input should always produce the same hash (unlike password hashing)
        token = "same-token"
        assert hash_token(token) == hash_token(token)

    def test_different_inputs_produce_different_hashes(self):
        assert hash_token("token-a") != hash_token("token-b")

    def test_output_length_is_64_hex_chars(self):
        # sha256 hex digest is always 64 characters
        assert len(hash_token("anything")) == 64


# ---------------------------------------------------------------------------
# hash_password / verify_password
# ---------------------------------------------------------------------------


class TestPasswordHashing:
    def test_hash_password_returns_a_string_not_the_plain_password(self):
        plain = "supersecret123"
        hashed = hash_password(plain)
        assert isinstance(hashed, str)
        assert hashed != plain

    def test_hash_password_is_not_deterministic(self):
        # Argon2 uses a random salt per hash, so hashing the same
        # password twice should NOT produce the same output.
        plain = "supersecret123"
        hash1 = hash_password(plain)
        hash2 = hash_password(plain)
        assert hash1 != hash2

    def test_verify_password_succeeds_with_correct_password(self):
        plain = "supersecret123"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_password_fails_with_wrong_password(self):
        hashed = hash_password("supersecret123")
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_password_fails_with_empty_password(self):
        hashed = hash_password("supersecret123")
        assert verify_password("", hashed) is False

    def test_verify_password_does_not_raise_on_mismatch(self):
        # Confirms VerifyMismatchError is caught internally and
        # converted to a clean False, not left to bubble up.
        hashed = hash_password("supersecret123")
        try:
            result = verify_password("totally-different", hashed)
        except Exception as e:
            pytest.fail(f"verify_password raised unexpectedly: {e}")
        assert result is False


# ---------------------------------------------------------------------------
# create_access_token
# ---------------------------------------------------------------------------


class TestCreateAccessToken:
    def test_returns_a_string(self):
        token = create_access_token({"sub": "user-123"})
        assert isinstance(token, str)

    def test_token_is_decodable_and_contains_original_data(self):
        token = create_access_token({"sub": "user-123"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        assert payload["sub"] == "user-123"

    def test_token_type_is_access(self):
        token = create_access_token({"sub": "user-123"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        assert payload["type"] == "access"

    def test_token_has_expiry_in_the_future(self):
        before = datetime.now(timezone.utc)
        token = create_access_token({"sub": "user-123"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        assert exp > before

    def test_expiry_matches_configured_minutes(self):
        before = datetime.now(timezone.utc)
        token = create_access_token({"sub": "user-123"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

        expected_expiry = before + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        # allow a small tolerance for test execution time
        assert abs((exp - expected_expiry).total_seconds()) < 5

    def test_does_not_mutate_the_original_input_dict(self):
        data = {"sub": "user-123"}
        create_access_token(data)
        # original dict passed in should remain untouched
        assert data == {"sub": "user-123"}
        assert "exp" not in data
        assert "type" not in data


# ---------------------------------------------------------------------------
# create_refresh_token
# ---------------------------------------------------------------------------


class TestCreateRefreshToken:
    def test_returns_a_string(self):
        token = create_refresh_token({"sub": "user-123"})
        assert isinstance(token, str)

    def test_token_type_is_refresh(self):
        token = create_refresh_token({"sub": "user-123"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        assert payload["type"] == "refresh"

    def test_expiry_matches_configured_days(self):
        before = datetime.now(timezone.utc)
        token = create_refresh_token({"sub": "user-123"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

        expected_expiry = before + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        assert abs((exp - expected_expiry).total_seconds()) < 5

    def test_access_and_refresh_tokens_have_different_type_claims(self):
        access = create_access_token({"sub": "user-123"})
        refresh = create_refresh_token({"sub": "user-123"})

        access_payload = jwt.decode(access, settings.SECRET_KEY, algorithms=["HS256"])
        refresh_payload = jwt.decode(refresh, settings.SECRET_KEY, algorithms=["HS256"])

        assert access_payload["type"] != refresh_payload["type"]


# ---------------------------------------------------------------------------
# decode_token
# ---------------------------------------------------------------------------


class TestDecodeToken:
    def test_valid_token_decodes_successfully(self):
        token = create_access_token({"sub": "user-123"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"

    def test_garbage_token_returns_none(self):
        assert decode_token("this-is-not-a-jwt") is None

    def test_tampered_token_returns_none(self):
        token = create_access_token({"sub": "user-123"})
        # Flip a character in the middle of the token (not the last char --
        # the final base64 character can carry padding-only bits, so
        # mutating it can sometimes decode to identical bytes and not
        # actually corrupt the signature).
        mid = len(token) // 2
        flipped_char = "a" if token[mid] != "a" else "b"
        tampered = token[:mid] + flipped_char + token[mid + 1 :]
        assert decode_token(tampered) is None

    def test_token_signed_with_wrong_secret_returns_none(self):
        # Simulate a token forged with a different secret key
        bad_token = jwt.encode(
            {
                "sub": "user-123",
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            },
            "totally-wrong-secret",
            algorithm="HS256",
        )
        assert decode_token(bad_token) is None

    def test_expired_token_returns_none(self):
        # Manually build a token with an expiry in the past
        expired_payload = {
            "sub": "user-123",
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        }
        expired_token = jwt.encode(
            expired_payload, settings.SECRET_KEY, algorithm="HS256"
        )
        assert decode_token(expired_token) is None

    def test_decode_round_trips_all_original_claims(self):
        token = create_access_token({"sub": "user-123", "role": "admin"})
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["role"] == "admin"
