"""Rate limiting and security controls middleware."""

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, Set, Tuple
from ipaddress import ip_address, ip_network

from fastapi import HTTPException, Request, status

from supabase_mcp_server.config import get_settings
from supabase_mcp_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitInfo:
    """Information about rate limiting for a client."""
    requests: deque = field(default_factory=deque)
    blocked_until: Optional[datetime] = None
    total_requests: int = 0
    blocked_requests: int = 0
    first_request: Optional[datetime] = None
    last_request: Optional[datetime] = None


@dataclass
class SecurityEvent:
    """Security event information."""
    timestamp: datetime
    client_ip: str
    event_type: str
    details: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    user_agent: Optional[str] = None
    endpoint: Optional[str] = None


class RateLimitExceeded(Exception):
    """Rate limit exceeded exception."""
    
    def __init__(self, message: str, retry_after: int):
        """Initialize rate limit exception."""
        super().__init__(message)
        self.retry_after = retry_after


class SecurityMiddleware:
    """Middleware for rate limiting and security controls."""
    
    def __init__(self):
        """Initialize security middleware."""
        self.settings = get_settings()
        
        # Rate limiting storage
        self._rate_limits: Dict[str, RateLimitInfo] = defaultdict(RateLimitInfo)
        self._blocked_ips: Set[str] = set()
        self._security_events: deque = deque(maxlen=1000)  # Keep last 1000 events
        
        # Security configuration
        self.rate_limit_window = timedelta(minutes=1)
        self.max_requests_per_window = self.settings.rate_limit_per_minute
        self.block_duration = timedelta(minutes=15)
        self.max_violations_before_block = 5
        
        # Trusted IP ranges (can be configured)
        self.trusted_networks = [
            ip_network("127.0.0.0/8"),    # Localhost
            ip_network("10.0.0.0/8"),     # Private network
            ip_network("172.16.0.0/12"),  # Private network
            ip_network("192.168.0.0/16"), # Private network
        ]
        
        # Suspicious patterns
        self.suspicious_user_agents = [
            "sqlmap", "nikto", "nmap", "masscan", "zap", "burp",
            "bot", "crawler", "spider", "scraper"
        ]
        
        # Cleanup task will be started when needed
        self._cleanup_task = None
    
    async def initialize(self) -> None:
        """Initialize the middleware with async components."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def check_rate_limit(self, request: Request) -> None:
        """Check if request should be rate limited."""
        client_ip = self._get_client_ip(request)
        
        # Skip rate limiting for trusted IPs
        if self._is_trusted_ip(client_ip):
            logger.debug("Skipping rate limit for trusted IP", client_ip=client_ip)
            return
        
        # Check if IP is blocked
        if client_ip in self._blocked_ips:
            await self._log_security_event(
                client_ip=client_ip,
                event_type="blocked_request",
                details="Request from blocked IP",
                severity="medium",
                request=request
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="IP address is temporarily blocked",
                headers={"Retry-After": str(int(self.block_duration.total_seconds()))}
            )
        
        # Get rate limit info for this IP
        rate_info = self._rate_limits[client_ip]
        now = datetime.now()
        
        # Check if still blocked from previous violations
        if rate_info.blocked_until and now < rate_info.blocked_until:
            remaining_seconds = int((rate_info.blocked_until - now).total_seconds())
            await self._log_security_event(
                client_ip=client_ip,
                event_type="rate_limit_blocked",
                details=f"Request blocked, {remaining_seconds}s remaining",
                severity="low",
                request=request
            )
            raise RateLimitExceeded(
                f"Rate limit exceeded. Try again in {remaining_seconds} seconds.",
                remaining_seconds
            )
        
        # Clean old requests outside the window
        cutoff_time = now - self.rate_limit_window
        while rate_info.requests and rate_info.requests[0] < cutoff_time:
            rate_info.requests.popleft()
        
        # Check if rate limit is exceeded
        if len(rate_info.requests) >= self.max_requests_per_window:
            # Rate limit exceeded
            rate_info.blocked_requests += 1
            
            # Check if should block IP
            if rate_info.blocked_requests >= self.max_violations_before_block:
                rate_info.blocked_until = now + self.block_duration
                self._blocked_ips.add(client_ip)
                
                await self._log_security_event(
                    client_ip=client_ip,
                    event_type="ip_blocked",
                    details=f"IP blocked for {self.block_duration.total_seconds()}s due to repeated violations",
                    severity="high",
                    request=request
                )
                
                logger.warning(
                    "IP blocked due to rate limit violations",
                    client_ip=client_ip,
                    violations=rate_info.blocked_requests,
                    block_duration=self.block_duration.total_seconds()
                )
            
            retry_after = int(self.rate_limit_window.total_seconds())
            await self._log_security_event(
                client_ip=client_ip,
                event_type="rate_limit_exceeded",
                details=f"Rate limit exceeded: {len(rate_info.requests)}/{self.max_requests_per_window}",
                severity="medium",
                request=request
            )
            
            raise RateLimitExceeded(
                f"Rate limit exceeded. Maximum {self.max_requests_per_window} requests per minute.",
                retry_after
            )
        
        # Add current request to the window
        rate_info.requests.append(now)
        rate_info.total_requests += 1
        rate_info.last_request = now
        
        if not rate_info.first_request:
            rate_info.first_request = now
        
        logger.debug(
            "Rate limit check passed",
            client_ip=client_ip,
            requests_in_window=len(rate_info.requests),
            max_requests=self.max_requests_per_window
        )
    
    async def check_security_threats(self, request: Request) -> None:
        """Check for security threats in the request."""
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "").lower()
        
        # Check for suspicious user agents
        for suspicious_ua in self.suspicious_user_agents:
            if suspicious_ua in user_agent:
                await self._log_security_event(
                    client_ip=client_ip,
                    event_type="suspicious_user_agent",
                    details=f"Suspicious user agent detected: {user_agent}",
                    severity="medium",
                    request=request
                )
                break
        
        # Check for suspicious headers
        await self._check_suspicious_headers(request, client_ip)
        
        # Check for potential attack patterns in URL
        await self._check_suspicious_url(request, client_ip)
    
    async def _check_suspicious_headers(self, request: Request, client_ip: str) -> None:
        """Check for suspicious headers."""
        suspicious_headers = {
            "x-forwarded-for": "potential_proxy_abuse",
            "x-real-ip": "potential_ip_spoofing",
            "x-originating-ip": "potential_ip_spoofing",
            "x-remote-ip": "potential_ip_spoofing",
            "x-cluster-client-ip": "potential_ip_spoofing",
        }
        
        for header, threat_type in suspicious_headers.items():
            if header in request.headers:
                header_value = request.headers[header]
                # Check for multiple IPs (potential proxy chain abuse)
                if "," in header_value and len(header_value.split(",")) > 3:
                    await self._log_security_event(
                        client_ip=client_ip,
                        event_type=threat_type,
                        details=f"Suspicious header {header}: {header_value}",
                        severity="low",
                        request=request
                    )
    
    async def _check_suspicious_url(self, request: Request, client_ip: str) -> None:
        """Check for suspicious URL patterns."""
        url_path = str(request.url.path).lower()
        query_string = str(request.url.query).lower()
        
        # SQL injection patterns
        sql_patterns = [
            "union select", "drop table", "insert into", "delete from",
            "update set", "exec(", "execute(", "sp_", "xp_", "0x",
            "char(", "ascii(", "substring(", "waitfor delay"
        ]
        
        # XSS patterns
        xss_patterns = [
            "<script", "javascript:", "onload=", "onerror=", "onclick=",
            "eval(", "alert(", "document.cookie", "window.location"
        ]
        
        # Path traversal patterns
        traversal_patterns = [
            "../", "..\\", "%2e%2e%2f", "%2e%2e%5c", "....//", "....\\\\",
            "/etc/passwd", "/etc/shadow", "c:\\windows", "c:/windows"
        ]
        
        full_url = url_path + " " + query_string
        
        # Check for SQL injection
        for pattern in sql_patterns:
            if pattern in full_url:
                await self._log_security_event(
                    client_ip=client_ip,
                    event_type="sql_injection_attempt",
                    details=f"SQL injection pattern detected: {pattern}",
                    severity="high",
                    request=request
                )
                break
        
        # Check for XSS
        for pattern in xss_patterns:
            if pattern in full_url:
                await self._log_security_event(
                    client_ip=client_ip,
                    event_type="xss_attempt",
                    details=f"XSS pattern detected: {pattern}",
                    severity="high",
                    request=request
                )
                break
        
        # Check for path traversal
        for pattern in traversal_patterns:
            if pattern in full_url:
                await self._log_security_event(
                    client_ip=client_ip,
                    event_type="path_traversal_attempt",
                    details=f"Path traversal pattern detected: {pattern}",
                    severity="high",
                    request=request
                )
                break
    
    def _get_client_ip(self, request: Request) -> str:
        """Get the real client IP address."""
        # Check various headers for the real IP
        headers_to_check = [
            "x-forwarded-for",
            "x-real-ip",
            "x-forwarded",
            "x-cluster-client-ip",
            "forwarded-for",
            "forwarded"
        ]
        
        for header in headers_to_check:
            if header in request.headers:
                # Take the first IP if there are multiple
                ip = request.headers[header].split(",")[0].strip()
                try:
                    # Validate IP address
                    ip_address(ip)
                    return ip
                except ValueError:
                    continue
        
        # Fallback to client host
        return request.client.host if request.client else "unknown"
    
    def _is_trusted_ip(self, ip: str) -> bool:
        """Check if IP is in trusted networks."""
        try:
            client_ip = ip_address(ip)
            for network in self.trusted_networks:
                if client_ip in network:
                    return True
        except ValueError:
            pass
        
        return False
    
    async def _log_security_event(
        self,
        client_ip: str,
        event_type: str,
        details: str,
        severity: str,
        request: Request
    ) -> None:
        """Log a security event."""
        event = SecurityEvent(
            timestamp=datetime.now(),
            client_ip=client_ip,
            event_type=event_type,
            details=details,
            severity=severity,
            user_agent=request.headers.get("user-agent"),
            endpoint=str(request.url.path)
        )
        
        self._security_events.append(event)
        
        logger.warning(
            "Security event",
            client_ip=client_ip,
            event_type=event_type,
            details=details,
            severity=severity,
            endpoint=str(request.url.path),
            user_agent=request.headers.get("user-agent")
        )
    
    async def _cleanup_loop(self) -> None:
        """Background task to clean up old data."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                await self._cleanup_old_data()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in cleanup loop", error=str(e))
    
    async def _cleanup_old_data(self) -> None:
        """Clean up old rate limiting and security data."""
        now = datetime.now()
        cutoff_time = now - timedelta(hours=1)  # Keep data for 1 hour
        
        # Clean up rate limit data
        expired_ips = []
        for ip, rate_info in self._rate_limits.items():
            # Remove old requests
            while rate_info.requests and rate_info.requests[0] < cutoff_time:
                rate_info.requests.popleft()
            
            # Remove entries with no recent activity
            if (not rate_info.requests and 
                rate_info.last_request and 
                rate_info.last_request < cutoff_time):
                expired_ips.append(ip)
        
        for ip in expired_ips:
            del self._rate_limits[ip]
        
        # Clean up blocked IPs
        unblocked_ips = []
        for ip in self._blocked_ips:
            rate_info = self._rate_limits.get(ip)
            if rate_info and rate_info.blocked_until and now > rate_info.blocked_until:
                unblocked_ips.append(ip)
        
        for ip in unblocked_ips:
            self._blocked_ips.discard(ip)
            if ip in self._rate_limits:
                self._rate_limits[ip].blocked_until = None
                self._rate_limits[ip].blocked_requests = 0
        
        if expired_ips or unblocked_ips:
            logger.debug(
                "Cleaned up security data",
                expired_rate_limits=len(expired_ips),
                unblocked_ips=len(unblocked_ips)
            )
    
    def get_security_stats(self) -> Dict:
        """Get security statistics."""
        now = datetime.now()
        last_hour = now - timedelta(hours=1)
        last_day = now - timedelta(days=1)
        
        # Count events by type and time
        events_last_hour = [e for e in self._security_events if e.timestamp > last_hour]
        events_last_day = [e for e in self._security_events if e.timestamp > last_day]
        
        # Count by severity
        severity_counts = defaultdict(int)
        for event in events_last_day:
            severity_counts[event.severity] += 1
        
        # Count by event type
        event_type_counts = defaultdict(int)
        for event in events_last_day:
            event_type_counts[event.event_type] += 1
        
        return {
            "active_rate_limits": len(self._rate_limits),
            "blocked_ips": len(self._blocked_ips),
            "security_events": {
                "last_hour": len(events_last_hour),
                "last_day": len(events_last_day),
                "total": len(self._security_events)
            },
            "events_by_severity": dict(severity_counts),
            "events_by_type": dict(event_type_counts),
            "rate_limit_config": {
                "max_requests_per_minute": self.max_requests_per_window,
                "block_duration_minutes": int(self.block_duration.total_seconds() / 60),
                "max_violations_before_block": self.max_violations_before_block
            }
        }
    
    def get_client_stats(self, client_ip: str) -> Optional[Dict]:
        """Get statistics for a specific client IP."""
        if client_ip not in self._rate_limits:
            return None
        
        rate_info = self._rate_limits[client_ip]
        
        return {
            "client_ip": client_ip,
            "total_requests": rate_info.total_requests,
            "blocked_requests": rate_info.blocked_requests,
            "current_window_requests": len(rate_info.requests),
            "first_request": rate_info.first_request.isoformat() if rate_info.first_request else None,
            "last_request": rate_info.last_request.isoformat() if rate_info.last_request else None,
            "blocked_until": rate_info.blocked_until.isoformat() if rate_info.blocked_until else None,
            "is_blocked": client_ip in self._blocked_ips,
            "is_trusted": self._is_trusted_ip(client_ip)
        }


# Global security middleware instance (will be initialized later)
security_middleware = None

def get_security_middleware() -> SecurityMiddleware:
    """Get or create the security middleware instance."""
    global security_middleware
    if security_middleware is None:
        security_middleware = SecurityMiddleware()
    return security_middleware