"""
Tests for security functions
"""
import pytest
from datetime import datetime, timedelta

from app.security.password import hash_password, verify_password
from app.security.jwt_handler import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_share_link_token,
    create_share_link_payload
)


class TestPasswordSecurity:
    """Test password hashing and verification"""

    def test_hash_password(self):
        """Test password hashing"""
        password = "test_password_123"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt format

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "test_password_123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "test_password_123"
        hashed = hash_password(password)

        assert verify_password("wrong_password", hashed) is False

    def test_different_hashes_for_same_password(self):
        """Test that same password produces different hashes (salt)"""
        password = "test_password_123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different due to random salt
        assert hash1 != hash2

        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTHandling:
    """Test JWT token operations"""

    def test_create_access_token(self):
        """Test access token creation"""
        data = {
            "sub": "user_123",
            "email": "test@example.com",
            "role": "employee"
        }

        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        """Test refresh token creation"""
        data = {
            "sub": "user_123",
            "type": "refresh"
        }

        token = create_refresh_token(data)

        assert token is not None
        assert isinstance(token, str)

    def test_decode_valid_token(self):
        """Test decoding valid token"""
        data = {
            "sub": "user_123",
            "email": "test@example.com"
        }

        token = create_access_token(data)
        decoded = decode_token(token)

        assert decoded is not None
        assert decoded["sub"] == "user_123"
        assert decoded["email"] == "test@example.com"
        assert "exp" in decoded
        assert "iat" in decoded

    def test_decode_invalid_token(self):
        """Test decoding invalid token"""
        invalid_token = "invalid.token.here"
        decoded = decode_token(invalid_token)

        assert decoded is None

    def test_decode_expired_token(self):
        """Test decoding expired token"""
        data = {"sub": "user_123"}

        # Create token that expires immediately
        token = create_access_token(data, timedelta(seconds=-1))
        decoded = decode_token(token)

        # Should be None because token is expired
        assert decoded is None

    def test_token_expiration_in_payload(self):
        """Test that token contains expiration time"""
        data = {"sub": "user_123"}
        token = create_access_token(data)
        decoded = decode_token(token)

        assert "exp" in decoded
        exp_time = datetime.fromtimestamp(decoded["exp"])
        now = datetime.utcnow()

        # Token should expire in the future
        assert exp_time > now

    def test_generate_share_link_token(self):
        """Test share link token generation"""
        token1 = generate_share_link_token()
        token2 = generate_share_link_token()

        # Tokens should be unique
        assert token1 != token2

        # Tokens should be URL-safe
        assert "/" not in token1
        assert "+" not in token1
        assert "=" not in token1 or token1.endswith("=")

        # Tokens should be reasonably long
        assert len(token1) > 32

    def test_create_share_link_payload(self):
        """Test share link payload creation"""
        user_id = "user_123"
        payload = create_share_link_payload(user_id)

        assert payload["sub"] == user_id
        assert payload["type"] == "share_link"
        assert "exp" in payload
        assert "iat" in payload

    def test_create_share_link_payload_with_device(self):
        """Test share link payload with device fingerprint"""
        user_id = "user_123"
        device = "device_fingerprint_abc"

        payload = create_share_link_payload(user_id, device)

        assert payload["sub"] == user_id
        assert payload["device"] == device


class TestTokenSecurity:
    """Test token security features"""

    def test_token_contains_issuer(self):
        """Test that tokens contain issuer claim"""
        from app.config import settings

        data = {"sub": "user_123"}
        token = create_access_token(data)
        decoded = decode_token(token)

        assert decoded is not None
        assert "iss" in decoded
        assert decoded["iss"] == settings.APP_NAME

    def test_token_tampering_detection(self):
        """Test that tampered tokens are rejected"""
        data = {"sub": "user_123"}
        token = create_access_token(data)

        # Tamper with token
        parts = token.split(".")
        tampered_token = parts[0] + ".tampered." + parts[2]

        decoded = decode_token(tampered_token)
        assert decoded is None

    def test_token_replay_protection_via_expiration(self):
        """Test that tokens expire to prevent replay attacks"""
        data = {"sub": "user_123"}

        # Create short-lived token
        token = create_access_token(data, timedelta(seconds=1))

        # Immediate decode should work
        decoded1 = decode_token(token)
        assert decoded1 is not None

        # Wait for expiration
        import time
        time.sleep(2)

        # Decode after expiration should fail
        decoded2 = decode_token(token)
        assert decoded2 is None


class TestPasswordStrength:
    """Test password strength requirements"""

    def test_hash_empty_password(self):
        """Test hashing empty password"""
        # Should still hash, but in production you'd want to validate first
        hashed = hash_password("")
        assert hashed is not None

    def test_hash_long_password(self):
        """Test hashing very long password"""
        long_password = "a" * 100
        hashed = hash_password(long_password)

        assert verify_password(long_password, hashed) is True

    def test_hash_special_characters(self):
        """Test hashing password with special characters"""
        password = "P@ssw0rd!#$%^&*()"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_hash_unicode_password(self):
        """Test hashing password with unicode characters"""
        password = "пароль密码🔒"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True
