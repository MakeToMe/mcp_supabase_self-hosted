"""Authentication middleware for MCP server."""

import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

import jwt
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from supabase_mcp_server.config import get_settings
from supabase_mcp_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AuthContext:
    """Authentication context for requests."""
    user_id: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    is_authenticated: bool = False
    auth_method: Optional[str] = None  # 'jwt', 'api_key', 'service_role'
    permissions: Optional[Dict[str, bool]] = None
    expires_at: Optional[datetime] = None


class AuthenticationError(Exception):
    """Authentication error."""
    
    def __init__(self, message: str, status_code: int = 401):
        """Initialize authentication error."""
        super().__init__(message)
        self.status_code = status_code


class AuthenticationMiddleware:
    """Middleware for handling authentication."""
    
    def __init__(self):
        """Initialize authentication middleware."""
        self.settings = get_settings()
        self.security = HTTPBearer(auto_error=False)
        
        # Cache for validated tokens (simple in-memory cache)
        self._token_cache: Dict[str, Tuple[AuthContext, datetime]] = {}
        self._cache_ttl = timedelta(minutes=5)
    
    async def authenticate_request(self, request: Request) -> AuthContext:
        """Authenticate a request and return auth context."""
        try:
            # Try different authentication methods
            auth_context = None
            
            # 1. Try API key authentication
            api_key = self._extract_api_key(request)
            if api_key:
                auth_context = await self._authenticate_api_key(api_key)
            
            # 2. Try JWT token authentication
            if not auth_context:
                token = await self._extract_jwt_token(request)
                if token:
                    auth_context = await self._authenticate_jwt_token(token)
            
            # 3. Try service role authentication
            if not auth_context:
                service_key = self._extract_service_key(request)
                if service_key:
                    auth_context = await self._authenticate_service_key(service_key)
            
            # Return unauthenticated context if no auth method worked
            if not auth_context:
                logger.debug("No valid authentication found")
                return AuthContext(is_authenticated=False)
            
            logger.debug(
                "Request authenticated",
                user_id=auth_context.user_id,
                auth_method=auth_context.auth_method
            )
            
            return auth_context
            
        except AuthenticationError as e:
            logger.warning("Authentication failed", error=str(e))
            raise HTTPException(
                status_code=e.status_code,
                detail=str(e)
            )
        except Exception as e:
            logger.error("Authentication error", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service error"
            )
    
    def _extract_api_key(self, request: Request) -> Optional[str]:
        """Extract API key from request."""
        # Check header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return api_key
        
        # Check query parameter
        api_key = request.query_params.get("api_key")
        if api_key:
            return api_key
        
        return None
    
    async def _extract_jwt_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from request."""
        # Try Authorization header
        credentials: HTTPAuthorizationCredentials = await self.security(request)
        if credentials:
            return credentials.credentials
        
        # Try custom header
        token = request.headers.get("X-JWT-Token")
        if token:
            return token
        
        return None
    
    def _extract_service_key(self, request: Request) -> Optional[str]:
        """Extract service role key from request."""
        # Check for service role key in headers
        service_key = request.headers.get("X-Service-Role-Key")
        if service_key:
            return service_key
        
        return None
    
    async def _authenticate_api_key(self, api_key: str) -> Optional[AuthContext]:
        """Authenticate using API key."""
        if not api_key:
            return None
        
        # Check against configured API key
        if api_key == self.settings.mcp_api_key:
            logger.debug("API key authentication successful")
            return AuthContext(
                user_id="api_user",
                is_authenticated=True,
                auth_method="api_key",
                permissions={"read": True, "write": True, "admin": False}
            )
        
        logger.debug("Invalid API key")
        return None
    
    async def _authenticate_jwt_token(self, token: str) -> Optional[AuthContext]:
        """Authenticate using JWT token."""
        if not token:
            return None
        
        # Check cache first
        cached_context = self._get_from_cache(token)
        if cached_context:
            return cached_context
        
        try:
            # Decode JWT token (without verification for now - Supabase handles this)
            # In production, you'd verify with Supabase's public key
            decoded = jwt.decode(token, options={"verify_signature": False})
            
            # Extract user information
            user_id = decoded.get("sub")
            email = decoded.get("email")
            role = decoded.get("role", "authenticated")
            exp = decoded.get("exp")
            
            if not user_id:
                logger.debug("JWT token missing user ID")
                return None
            
            # Check expiration
            if exp and datetime.fromtimestamp(exp) < datetime.now():
                logger.debug("JWT token expired")
                return None
            
            auth_context = AuthContext(
                user_id=user_id,
                email=email,
                role=role,
                is_authenticated=True,
                auth_method="jwt",
                permissions=self._get_role_permissions(role),
                expires_at=datetime.fromtimestamp(exp) if exp else None
            )
            
            # Cache the result
            self._set_cache(token, auth_context)
            
            logger.debug("JWT authentication successful", user_id=user_id, role=role)
            return auth_context
            
        except jwt.InvalidTokenError as e:
            logger.debug("Invalid JWT token", error=str(e))
            return None
        except Exception as e:
            logger.error("JWT authentication error", error=str(e))
            return None
    
    async def _authenticate_service_key(self, service_key: str) -> Optional[AuthContext]:
        """Authenticate using service role key."""
        if not service_key:
            return None
        
        # Check against Supabase service role key
        if service_key == self.settings.supabase_service_role_key:
            logger.debug("Service role authentication successful")
            return AuthContext(
                user_id="service_role",
                role="service_role",
                is_authenticated=True,
                auth_method="service_role",
                permissions={"read": True, "write": True, "admin": True}
            )
        
        logger.debug("Invalid service role key")
        return None
    
    def _get_role_permissions(self, role: str) -> Dict[str, bool]:
        """Get permissions for a role."""
        role_permissions = {
            "anon": {"read": True, "write": False, "admin": False},
            "authenticated": {"read": True, "write": True, "admin": False},
            "service_role": {"read": True, "write": True, "admin": True},
        }
        
        return role_permissions.get(role, {"read": False, "write": False, "admin": False})
    
    def _get_from_cache(self, token: str) -> Optional[AuthContext]:
        """Get authentication context from cache."""
        if token in self._token_cache:
            context, cached_at = self._token_cache[token]
            if datetime.now() - cached_at < self._cache_ttl:
                return context
            else:
                # Remove expired entry
                del self._token_cache[token]
        
        return None
    
    def _set_cache(self, token: str, context: AuthContext) -> None:
        """Set authentication context in cache."""
        self._token_cache[token] = (context, datetime.now())
        
        # Simple cache cleanup - remove old entries
        if len(self._token_cache) > 1000:
            cutoff = datetime.now() - self._cache_ttl
            expired_keys = [
                key for key, (_, cached_at) in self._token_cache.items()
                if cached_at < cutoff
            ]
            for key in expired_keys:
                del self._token_cache[key]
    
    def require_authentication(self, auth_context: AuthContext) -> None:
        """Require authentication for a request."""
        if not auth_context.is_authenticated:
            raise AuthenticationError("Authentication required")
    
    def require_permission(self, auth_context: AuthContext, permission: str) -> None:
        """Require a specific permission."""
        if not auth_context.is_authenticated:
            raise AuthenticationError("Authentication required")
        
        if not auth_context.permissions or not auth_context.permissions.get(permission, False):
            raise AuthenticationError(
                f"Permission '{permission}' required",
                status_code=status.HTTP_403_FORBIDDEN
            )
    
    def require_role(self, auth_context: AuthContext, required_role: str) -> None:
        """Require a specific role."""
        if not auth_context.is_authenticated:
            raise AuthenticationError("Authentication required")
        
        if auth_context.role != required_role:
            raise AuthenticationError(
                f"Role '{required_role}' required",
                status_code=status.HTTP_403_FORBIDDEN
            )


# Global authentication middleware instance
auth_middleware = AuthenticationMiddleware()