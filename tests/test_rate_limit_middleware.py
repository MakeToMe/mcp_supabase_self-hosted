"""Tests for rate limiting and security middleware."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request

from supabase_mcp_server.middleware.rate_limit import (
    RateLimitExceeded,
    RateLimitInfo,
    SecurityEvent,
    SecurityMiddleware,
)


class TestRateLimitInfo:
    """Test RateLimitInfo class."""
    
    def test_rate_limit_info_creation(self):
        """Test RateLimitInfo creation."""
        info = RateLimitInfo()
        
        assert len(info.requests) == 0
        assert info.blocked_until is None
        assert info.total_requests == 0
        assert info.blocked_requests == 0
        assert info.first_request is None
        assert info.last_request is None


class TestSecurityEvent:
    """Test SecurityEvent class."""
    
    def test_security_event_creation(self):
        """Test SecurityEvent creation."""
        now = datetime.now()
        event = SecurityEvent(
            timestamp=now,
            client_ip="192.168.1.1",
            event_type="rate_limit_exceeded",
            details="Too many requests",
            severity="medium"
        )
        
        assert event.timestamp == now
        assert event.client_ip == "192.168.1.1"
        assert event.event_type == "rate_limit_exceeded"
        assert event.details == "Too many requests"
        assert event.severity == "medium"


class TestSecurityMiddleware:
    """Test SecurityMiddleware class."""
    
    @pytest.fixture
    def security_middleware(self, override_settings):
        """Create security middleware instance."""
        middleware = SecurityMiddleware()
        # Cancel the cleanup task to avoid interference
        middleware._cleanup_task.cancel()
        return middleware
    
    def test_middleware_creation(self, security_middleware):
        """Test middleware creation."""
        assert security_middleware.settings is not None
        assert security_middleware.max_requests_per_window > 0
        assert len(security_middleware.trusted_networks) > 0
        assert len(security_middleware.suspicious_user_agents) > 0
    
    def test_get_client_ip_direct(self, security_middleware):
        """Test getting client IP directly."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client.host = "192.168.1.1"
        
        ip = security_middleware._get_client_ip(request)
        
        assert ip == "192.168.1.1"
    
    def test_get_client_ip_forwarded(self, security_middleware):
        """Test getting client IP from forwarded header."""
        request = MagicMock(spec=Request)
        request.headers = {"x-forwarded-for": "203.0.113.1, 192.168.1.1"}
        request.client.host = "192.168.1.1"
        
        ip = security_middleware._get_client_ip(request)
        
        assert ip == "203.0.113.1"
    
    def test_get_client_ip_real_ip(self, security_middleware):
        """Test getting client IP from real IP header."""
        request = MagicMock(spec=Request)
        request.headers = {"x-real-ip": "203.0.113.1"}
        request.client.host = "192.168.1.1"
        
        ip = security_middleware._get_client_ip(request)
        
        assert ip == "203.0.113.1"
    
    def test_is_trusted_ip_localhost(self, security_middleware):
        """Test trusted IP detection for localhost."""
        assert security_middleware._is_trusted_ip("127.0.0.1") is True
        assert security_middleware._is_trusted_ip("127.0.0.100") is True
    
    def test_is_trusted_ip_private(self, security_middleware):
        """Test trusted IP detection for private networks."""
        assert security_middleware._is_trusted_ip("192.168.1.1") is True
        assert security_middleware._is_trusted_ip("10.0.0.1") is True
        assert security_middleware._is_trusted_ip("172.16.0.1") is True
    
    def test_is_trusted_ip_public(self, security_middleware):
        """Test trusted IP detection for public IPs."""
        assert security_middleware._is_trusted_ip("203.0.113.1") is False
        assert security_middleware._is_trusted_ip("8.8.8.8") is False
    
    def test_is_trusted_ip_invalid(self, security_middleware):
        """Test trusted IP detection for invalid IPs."""
        assert security_middleware._is_trusted_ip("invalid-ip") is False
        assert security_middleware._is_trusted_ip("999.999.999.999") is False
    
    async def test_check_rate_limit_trusted_ip(self, security_middleware):
        """Test rate limit check for trusted IP."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client.host = "127.0.0.1"  # Localhost
        
        # Should not raise exception
        await security_middleware.check_rate_limit(request)
    
    async def test_check_rate_limit_normal_usage(self, security_middleware):
        """Test rate limit check for normal usage."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client.host = "203.0.113.1"  # Public IP
        
        # Should allow requests within limit
        for i in range(security_middleware.max_requests_per_window - 1):
            await security_middleware.check_rate_limit(request)
    
    async def test_check_rate_limit_exceeded(self, security_middleware):
        """Test rate limit exceeded."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client.host = "203.0.113.1"  # Public IP
        request.url.path = "/test"
        
        # Fill up the rate limit
        for i in range(security_middleware.max_requests_per_window):
            await security_middleware.check_rate_limit(request)
        
        # Next request should be rate limited
        with pytest.raises(RateLimitExceeded):
            await security_middleware.check_rate_limit(request)
    
    async def test_check_rate_limit_blocked_ip(self, security_middleware):
        """Test rate limit check for blocked IP."""
        client_ip = "203.0.113.1"
        security_middleware._blocked_ips.add(client_ip)
        
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client.host = client_ip
        request.url.path = "/test"
        
        with pytest.raises(Exception):  # Should raise HTTPException
            await security_middleware.check_rate_limit(request)
    
    async def test_check_security_threats_suspicious_user_agent(self, security_middleware):
        """Test security threat detection for suspicious user agent."""
        request = MagicMock(spec=Request)
        request.headers = {"user-agent": "sqlmap/1.0"}
        request.client.host = "203.0.113.1"
        request.url.path = "/test"
        request.url.query = ""
        
        # Should not raise exception but log event
        await security_middleware.check_security_threats(request)
        
        # Check that event was logged
        assert len(security_middleware._security_events) > 0
        event = security_middleware._security_events[-1]
        assert event.event_type == "suspicious_user_agent"
        assert event.severity == "medium"
    
    async def test_check_security_threats_sql_injection(self, security_middleware):
        """Test security threat detection for SQL injection."""
        request = MagicMock(spec=Request)
        request.headers = {"user-agent": "Mozilla/5.0"}
        request.client.host = "203.0.113.1"
        request.url.path = "/test"
        request.url.query = "id=1 UNION SELECT * FROM users"
        
        await security_middleware.check_security_threats(request)
        
        # Check that SQL injection event was logged
        events = [e for e in security_middleware._security_events if e.event_type == "sql_injection_attempt"]
        assert len(events) > 0
        assert events[0].severity == "high"
    
    async def test_check_security_threats_xss(self, security_middleware):
        """Test security threat detection for XSS."""
        request = MagicMock(spec=Request)
        request.headers = {"user-agent": "Mozilla/5.0"}
        request.client.host = "203.0.113.1"
        request.url.path = "/test"
        request.url.query = "name=<script>alert('xss')</script>"
        
        await security_middleware.check_security_threats(request)
        
        # Check that XSS event was logged
        events = [e for e in security_middleware._security_events if e.event_type == "xss_attempt"]
        assert len(events) > 0
        assert events[0].severity == "high"
    
    async def test_check_security_threats_path_traversal(self, security_middleware):
        """Test security threat detection for path traversal."""
        request = MagicMock(spec=Request)
        request.headers = {"user-agent": "Mozilla/5.0"}
        request.client.host = "203.0.113.1"
        request.url.path = "/test/../../../etc/passwd"
        request.url.query = ""
        
        await security_middleware.check_security_threats(request)
        
        # Check that path traversal event was logged
        events = [e for e in security_middleware._security_events if e.event_type == "path_traversal_attempt"]
        assert len(events) > 0
        assert events[0].severity == "high"
    
    async def test_check_suspicious_headers(self, security_middleware):
        """Test suspicious header detection."""
        request = MagicMock(spec=Request)
        request.headers = {
            "user-agent": "Mozilla/5.0",
            "x-forwarded-for": "1.1.1.1, 2.2.2.2, 3.3.3.3, 4.4.4.4, 5.5.5.5"  # Too many IPs
        }
        request.client.host = "203.0.113.1"
        request.url.path = "/test"
        request.url.query = ""
        
        await security_middleware.check_security_threats(request)
        
        # Check that suspicious header event was logged
        events = [e for e in security_middleware._security_events if "potential_proxy_abuse" in e.event_type]
        assert len(events) > 0
    
    def test_get_security_stats(self, security_middleware):
        """Test getting security statistics."""
        # Add some test data
        security_middleware._rate_limits["192.168.1.1"] = RateLimitInfo()
        security_middleware._blocked_ips.add("203.0.113.1")
        
        stats = security_middleware.get_security_stats()
        
        assert "active_rate_limits" in stats
        assert "blocked_ips" in stats
        assert "security_events" in stats
        assert "events_by_severity" in stats
        assert "events_by_type" in stats
        assert "rate_limit_config" in stats
        
        assert stats["active_rate_limits"] >= 1
        assert stats["blocked_ips"] >= 1
    
    def test_get_client_stats_existing(self, security_middleware):
        """Test getting client statistics for existing client."""
        client_ip = "192.168.1.1"
        rate_info = RateLimitInfo()
        rate_info.total_requests = 10
        rate_info.blocked_requests = 2
        rate_info.first_request = datetime.now()
        rate_info.last_request = datetime.now()
        
        security_middleware._rate_limits[client_ip] = rate_info
        
        stats = security_middleware.get_client_stats(client_ip)
        
        assert stats is not None
        assert stats["client_ip"] == client_ip
        assert stats["total_requests"] == 10
        assert stats["blocked_requests"] == 2
        assert stats["is_trusted"] is True  # 192.168.x.x is trusted
    
    def test_get_client_stats_nonexistent(self, security_middleware):
        """Test getting client statistics for non-existent client."""
        stats = security_middleware.get_client_stats("203.0.113.1")
        
        assert stats is None
    
    async def test_cleanup_old_data(self, security_middleware):
        """Test cleanup of old data."""
        # Add old data
        old_time = datetime.now() - timedelta(hours=2)
        client_ip = "203.0.113.1"
        
        rate_info = RateLimitInfo()
        rate_info.last_request = old_time
        rate_info.blocked_until = old_time
        security_middleware._rate_limits[client_ip] = rate_info
        security_middleware._blocked_ips.add(client_ip)
        
        # Run cleanup
        await security_middleware._cleanup_old_data()
        
        # Check that old data was cleaned up
        assert client_ip not in security_middleware._rate_limits
        assert client_ip not in security_middleware._blocked_ips


class TestRateLimitExceeded:
    """Test RateLimitExceeded exception."""
    
    def test_rate_limit_exceeded_creation(self):
        """Test RateLimitExceeded creation."""
        exception = RateLimitExceeded("Rate limit exceeded", 60)
        
        assert str(exception) == "Rate limit exceeded"
        assert exception.retry_after == 60