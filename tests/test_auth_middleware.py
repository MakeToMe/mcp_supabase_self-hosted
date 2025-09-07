"""Tests for authentication middleware."""

import jwt
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, Request

from supabase_mcp_server.middleware.auth import (
    AuthContext,
    AuthenticationError,
    AuthenticationMiddleware,
)


class TestAuthContext:
    """Test AuthContext class."""
    
    def test_auth_context_creation(self):
        """Test AuthContext creation."""
        context = AuthContext(
            user_id="123",
            email="test@example.com",
            role="authenticated",
            is_authenticated=True,
            auth_method="jwt",
            permissions={"read": True, "write": True}
        )
        
        assert context.user_id == "123"
        assert context.email == "test@example.com"
        assert context.role == "authenticated"
        assert context.is_authenticated is True
        assert context.auth_method == "jwt"
        assert context.permissions["read"] is True
    
    def test_auth_context_defaults(self):
        """Test AuthContext default values."""
        context = AuthContext()
        
        assert context.user_id is None
        assert context.email is None
        assert context.role is None
        assert context.is_authenticated is False
        assert context.auth_method is None
        assert context.permissions is None


class TestAuthenticationMiddleware:
    """Test AuthenticationMiddleware class."""
    
    @pytest.fixture
    def auth_middleware(self, override_settings):
        """Create authentication middleware instance."""
        return AuthenticationMiddleware()
    
    def test_middleware_creation(self, auth_middleware):
        """Test middleware creation."""
        assert auth_middleware.settings is not None
        assert auth_middleware.security is not None
        assert auth_middleware._token_cache == {}
    
    def test_extract_api_key_from_header(self, auth_middleware):
        """Test API key extraction from header."""
        request = MagicMock(spec=Request)
        request.headers.get.return_value = "test-api-key"
        request.query_params.get.return_value = None
        
        api_key = auth_middleware._extract_api_key(request)
        
        assert api_key == "test-api-key"
        request.headers.get.assert_called_with("X-API-Key")
    
    def test_extract_api_key_from_query(self, auth_middleware):
        """Test API key extraction from query parameter."""
        request = MagicMock(spec=Request)
        request.headers.get.return_value = None
        request.query_params.get.return_value = "test-api-key"
        
        api_key = auth_middleware._extract_api_key(request)
        
        assert api_key == "test-api-key"
        request.query_params.get.assert_called_with("api_key")
    
    def test_extract_api_key_none(self, auth_middleware):
        """Test API key extraction when none present."""
        request = MagicMock(spec=Request)
        request.headers.get.return_value = None
        request.query_params.get.return_value = None
        
        api_key = auth_middleware._extract_api_key(request)
        
        assert api_key is None
    
    async def test_authenticate_api_key_valid(self, auth_middleware):
        """Test valid API key authentication."""
        context = await auth_middleware._authenticate_api_key(auth_middleware.settings.mcp_api_key)
        
        assert context is not None
        assert context.is_authenticated is True
        assert context.auth_method == "api_key"
        assert context.user_id == "api_user"
        assert context.permissions["read"] is True
        assert context.permissions["write"] is True
    
    async def test_authenticate_api_key_invalid(self, auth_middleware):
        """Test invalid API key authentication."""
        context = await auth_middleware._authenticate_api_key("invalid-key")
        
        assert context is None
    
    async def test_authenticate_jwt_token_valid(self, auth_middleware):
        """Test valid JWT token authentication."""
        # Create a test JWT token
        payload = {
            "sub": "user123",
            "email": "test@example.com",
            "role": "authenticated",
            "exp": int((datetime.now() + timedelta(hours=1)).timestamp())
        }
        token = jwt.encode(payload, "secret", algorithm="HS256")
        
        context = await auth_middleware._authenticate_jwt_token(token)
        
        assert context is not None
        assert context.is_authenticated is True
        assert context.auth_method == "jwt"
        assert context.user_id == "user123"
        assert context.email == "test@example.com"
        assert context.role == "authenticated"
    
    async def test_authenticate_jwt_token_expired(self, auth_middleware):
        """Test expired JWT token authentication."""
        # Create an expired JWT token
        payload = {
            "sub": "user123",
            "email": "test@example.com",
            "role": "authenticated",
            "exp": int((datetime.now() - timedelta(hours=1)).timestamp())
        }
        token = jwt.encode(payload, "secret", algorithm="HS256")
        
        context = await auth_middleware._authenticate_jwt_token(token)
        
        assert context is None
    
    async def test_authenticate_jwt_token_invalid(self, auth_middleware):
        """Test invalid JWT token authentication."""
        context = await auth_middleware._authenticate_jwt_token("invalid-token")
        
        assert context is None
    
    async def test_authenticate_service_key_valid(self, auth_middleware):
        """Test valid service key authentication."""
        context = await auth_middleware._authenticate_service_key(
            auth_middleware.settings.supabase_service_role_key
        )
        
        assert context is not None
        assert context.is_authenticated is True
        assert context.auth_method == "service_role"
        assert context.user_id == "service_role"
        assert context.role == "service_role"
        assert context.permissions["admin"] is True
    
    async def test_authenticate_service_key_invalid(self, auth_middleware):
        """Test invalid service key authentication."""
        context = await auth_middleware._authenticate_service_key("invalid-key")
        
        assert context is None
    
    def test_get_role_permissions(self, auth_middleware):
        """Test role permissions mapping."""
        anon_perms = auth_middleware._get_role_permissions("anon")
        assert anon_perms["read"] is True
        assert anon_perms["write"] is False
        assert anon_perms["admin"] is False
        
        auth_perms = auth_middleware._get_role_permissions("authenticated")
        assert auth_perms["read"] is True
        assert auth_perms["write"] is True
        assert auth_perms["admin"] is False
        
        service_perms = auth_middleware._get_role_permissions("service_role")
        assert service_perms["read"] is True
        assert service_perms["write"] is True
        assert service_perms["admin"] is True
        
        unknown_perms = auth_middleware._get_role_permissions("unknown")
        assert unknown_perms["read"] is False
        assert unknown_perms["write"] is False
        assert unknown_perms["admin"] is False
    
    def test_cache_operations(self, auth_middleware):
        """Test token caching operations."""
        context = AuthContext(user_id="123", is_authenticated=True)
        token = "test-token"
        
        # Test cache miss
        cached = auth_middleware._get_from_cache(token)
        assert cached is None
        
        # Test cache set and hit
        auth_middleware._set_cache(token, context)
        cached = auth_middleware._get_from_cache(token)
        assert cached is not None
        assert cached.user_id == "123"
    
    def test_require_authentication_success(self, auth_middleware):
        """Test successful authentication requirement."""
        context = AuthContext(is_authenticated=True)
        
        # Should not raise exception
        auth_middleware.require_authentication(context)
    
    def test_require_authentication_failure(self, auth_middleware):
        """Test failed authentication requirement."""
        context = AuthContext(is_authenticated=False)
        
        with pytest.raises(AuthenticationError, match="Authentication required"):
            auth_middleware.require_authentication(context)
    
    def test_require_permission_success(self, auth_middleware):
        """Test successful permission requirement."""
        context = AuthContext(
            is_authenticated=True,
            permissions={"read": True, "write": False}
        )
        
        # Should not raise exception
        auth_middleware.require_permission(context, "read")
    
    def test_require_permission_failure(self, auth_middleware):
        """Test failed permission requirement."""
        context = AuthContext(
            is_authenticated=True,
            permissions={"read": True, "write": False}
        )
        
        with pytest.raises(AuthenticationError, match="Permission 'write' required"):
            auth_middleware.require_permission(context, "write")
    
    def test_require_permission_unauthenticated(self, auth_middleware):
        """Test permission requirement with unauthenticated user."""
        context = AuthContext(is_authenticated=False)
        
        with pytest.raises(AuthenticationError, match="Authentication required"):
            auth_middleware.require_permission(context, "read")
    
    def test_require_role_success(self, auth_middleware):
        """Test successful role requirement."""
        context = AuthContext(is_authenticated=True, role="admin")
        
        # Should not raise exception
        auth_middleware.require_role(context, "admin")
    
    def test_require_role_failure(self, auth_middleware):
        """Test failed role requirement."""
        context = AuthContext(is_authenticated=True, role="user")
        
        with pytest.raises(AuthenticationError, match="Role 'admin' required"):
            auth_middleware.require_role(context, "admin")
    
    async def test_authenticate_request_api_key(self, auth_middleware):
        """Test request authentication with API key."""
        request = MagicMock(spec=Request)
        request.headers.get.side_effect = lambda key: {
            "X-API-Key": auth_middleware.settings.mcp_api_key
        }.get(key)
        request.query_params.get.return_value = None
        
        # Mock security to return None (no bearer token)
        with patch.object(auth_middleware.security, '__call__', return_value=None):
            context = await auth_middleware.authenticate_request(request)
        
        assert context.is_authenticated is True
        assert context.auth_method == "api_key"
    
    async def test_authenticate_request_no_auth(self, auth_middleware):
        """Test request authentication with no credentials."""
        request = MagicMock(spec=Request)
        request.headers.get.return_value = None
        request.query_params.get.return_value = None
        
        # Mock security to return None (no bearer token)
        with patch.object(auth_middleware.security, '__call__', return_value=None):
            context = await auth_middleware.authenticate_request(request)
        
        assert context.is_authenticated is False
    
    async def test_authenticate_request_exception(self, auth_middleware):
        """Test request authentication with exception."""
        request = MagicMock(spec=Request)
        request.headers.get.side_effect = Exception("Request error")
        
        with pytest.raises(HTTPException):
            await auth_middleware.authenticate_request(request)


class TestAuthenticationError:
    """Test AuthenticationError class."""
    
    def test_authentication_error_creation(self):
        """Test AuthenticationError creation."""
        error = AuthenticationError("Test error", 403)
        
        assert str(error) == "Test error"
        assert error.status_code == 403
    
    def test_authentication_error_default_status(self):
        """Test AuthenticationError with default status code."""
        error = AuthenticationError("Test error")
        
        assert str(error) == "Test error"
        assert error.status_code == 401