"""
Tests for authentication endpoints
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.access_token import AccessToken, TokenType
from app.security.password import verify_password
from datetime import datetime, timedelta


class TestLogin:
    """Test login endpoint"""

    @pytest.mark.asyncio
    async def test_login_success(
        self,
        client: AsyncClient,
        test_manager_user: User
    ):
        """Test successful login"""
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "manager@test.com",
                "password": "manager123"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
        assert data["user"]["email"] == "manager@test.com"
        assert data["user"]["role"] == "manager"

    @pytest.mark.asyncio
    async def test_login_invalid_email(self, client: AsyncClient):
        """Test login with invalid email"""
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@test.com",
                "password": "password123"
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Incorrect email or password"

    @pytest.mark.asyncio
    async def test_login_invalid_password(
        self,
        client: AsyncClient,
        test_manager_user: User
    ):
        """Test login with invalid password"""
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "manager@test.com",
                "password": "wrongpassword"
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Incorrect email or password"

    @pytest.mark.asyncio
    async def test_login_inactive_user(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_manager_user: User
    ):
        """Test login with inactive user"""
        # Deactivate user
        test_manager_user.is_active = False
        await db_session.commit()

        response = await client.post(
            "/api/auth/login",
            json={
                "email": "manager@test.com",
                "password": "manager123"
            }
        )

        assert response.status_code == 403
        assert "inactive" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_invalid_email_format(self, client: AsyncClient):
        """Test login with invalid email format"""
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "not-an-email",
                "password": "password123"
            }
        )

        assert response.status_code == 422  # Validation error


class TestGenerateShareLink:
    """Test share link generation"""

    @pytest.mark.asyncio
    async def test_generate_link_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_employee_user: User
    ):
        """Test successful share link generation"""
        response = await client.post(
            "/api/auth/generate-link",
            headers=auth_headers,
            json={
                "user_id": str(test_employee_user.id),
                "expiration_hours": 8
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "share_link" in data
        assert "token_id" in data
        assert "expires_at" in data
        assert data["single_use"] is True
        assert "/checkin/" in data["share_link"]

    @pytest.mark.asyncio
    async def test_generate_link_unauthorized(
        self,
        client: AsyncClient,
        test_employee_user: User
    ):
        """Test share link generation without authentication"""
        response = await client.post(
            "/api/auth/generate-link",
            json={
                "user_id": str(test_employee_user.id)
            }
        )

        assert response.status_code == 403  # No auth header

    @pytest.mark.asyncio
    async def test_generate_link_employee_forbidden(
        self,
        client: AsyncClient,
        test_employee_user: User
    ):
        """Test that employee cannot generate share links"""
        from app.security.jwt_handler import create_access_token

        # Create token for employee
        token = create_access_token({
            "sub": str(test_employee_user.id),
            "email": test_employee_user.email,
            "role": "employee"
        })

        response = await client.post(
            "/api/auth/generate-link",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "user_id": str(test_employee_user.id)
            }
        )

        assert response.status_code == 403
        assert "permission" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_generate_link_nonexistent_user(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test share link generation for nonexistent user"""
        import uuid

        response = await client.post(
            "/api/auth/generate-link",
            headers=auth_headers,
            json={
                "user_id": str(uuid.uuid4())
            }
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_generate_link_custom_expiration(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_employee_user: User
    ):
        """Test share link with custom expiration"""
        response = await client.post(
            "/api/auth/generate-link",
            headers=auth_headers,
            json={
                "user_id": str(test_employee_user.id),
                "expiration_hours": 24
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Parse expiration time
        expires_at = datetime.fromisoformat(data["expires_at"].replace('Z', '+00:00'))
        expected_expiry = datetime.utcnow() + timedelta(hours=24)

        # Allow 1 minute difference
        time_diff = abs((expires_at - expected_expiry).total_seconds())
        assert time_diff < 60


class TestVerifyToken:
    """Test token verification"""

    @pytest.mark.asyncio
    async def test_verify_valid_token(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_employee_user: User
    ):
        """Test verification of valid token"""
        import hashlib
        from app.security.jwt_handler import generate_share_link_token

        # Generate token
        token = generate_share_link_token()
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Create access token in database
        access_token = AccessToken(
            user_id=test_employee_user.id,
            token_hash=token_hash,
            token_type=TokenType.SHARE_LINK,
            expires_at=datetime.utcnow() + timedelta(hours=8)
        )
        db_session.add(access_token)
        await db_session.commit()

        # Verify token
        response = await client.post(
            "/api/auth/verify-token",
            params={"token": token}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is True
        assert data["user_id"] == str(test_employee_user.id)
        assert data["employee_name"] == test_employee_user.full_name

    @pytest.mark.asyncio
    async def test_verify_invalid_token(self, client: AsyncClient):
        """Test verification of invalid token"""
        response = await client.post(
            "/api/auth/verify-token",
            params={"token": "invalid_token_12345"}
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_expired_token(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_employee_user: User
    ):
        """Test verification of expired token"""
        import hashlib
        from app.security.jwt_handler import generate_share_link_token

        # Generate expired token
        token = generate_share_link_token()
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        access_token = AccessToken(
            user_id=test_employee_user.id,
            token_hash=token_hash,
            token_type=TokenType.SHARE_LINK,
            expires_at=datetime.utcnow() - timedelta(hours=1)  # Expired
        )
        db_session.add(access_token)
        await db_session.commit()

        response = await client.post(
            "/api/auth/verify-token",
            params={"token": token}
        )

        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_verify_revoked_token(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_employee_user: User
    ):
        """Test verification of revoked token"""
        import hashlib
        from app.security.jwt_handler import generate_share_link_token

        token = generate_share_link_token()
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        access_token = AccessToken(
            user_id=test_employee_user.id,
            token_hash=token_hash,
            token_type=TokenType.SHARE_LINK,
            expires_at=datetime.utcnow() + timedelta(hours=8),
            revoked=True  # Revoked
        )
        db_session.add(access_token)
        await db_session.commit()

        response = await client.post(
            "/api/auth/verify-token",
            params={"token": token}
        )

        assert response.status_code == 401


class TestRevokeLink:
    """Test link revocation"""

    @pytest.mark.asyncio
    async def test_revoke_link_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_employee_user: User
    ):
        """Test successful link revocation"""
        import hashlib
        from app.security.jwt_handler import generate_share_link_token

        # Create token
        token = generate_share_link_token()
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        access_token = AccessToken(
            user_id=test_employee_user.id,
            token_hash=token_hash,
            token_type=TokenType.SHARE_LINK,
            expires_at=datetime.utcnow() + timedelta(hours=8)
        )
        db_session.add(access_token)
        await db_session.commit()
        await db_session.refresh(access_token)

        # Revoke token
        response = await client.post(
            f"/api/auth/revoke-link/{access_token.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify token is revoked
        await db_session.refresh(access_token)
        assert access_token.revoked is True
        assert access_token.revoked_at is not None

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_link(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test revoking nonexistent link"""
        import uuid

        response = await client.post(
            f"/api/auth/revoke-link/{uuid.uuid4()}",
            headers=auth_headers
        )

        assert response.status_code == 404
