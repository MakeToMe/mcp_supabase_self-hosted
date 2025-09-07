"""Configuration management for the Supabase MCP Server."""

from functools import lru_cache
from typing import Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Supabase Configuration
    supabase_url: str = Field(..., description="Supabase instance URL")
    supabase_anon_key: str = Field(..., description="Supabase anonymous key")
    supabase_service_role_key: str = Field(..., description="Supabase service role key")
    
    # Database Configuration
    database_url: str = Field(..., description="PostgreSQL connection URL")
    database_pool_size: int = Field(10, description="Database connection pool size")
    database_max_overflow: int = Field(20, description="Database connection pool max overflow")
    database_timeout: int = Field(30, description="Database connection timeout in seconds")
    
    # Server Configuration
    server_host: str = Field("0.0.0.0", description="Server host")
    server_port: int = Field(8000, description="Server port")
    log_level: str = Field("INFO", description="Logging level")
    debug: bool = Field(False, description="Enable debug mode")
    enable_cors: bool = Field(True, description="Enable CORS")
    
    # Security Configuration
    mcp_api_key: str = Field(..., description="API key for MCP authentication")
    rate_limit_per_minute: int = Field(100, description="Rate limit per minute per IP")
    enable_query_validation: bool = Field(True, description="Enable SQL query validation")
    max_query_execution_time: int = Field(30, description="Maximum query execution time in seconds")
    
    # Redis Configuration (optional)
    redis_url: Optional[str] = Field(None, description="Redis connection URL")
    redis_password: Optional[str] = Field(None, description="Redis password")
    
    # SSL Configuration
    ssl_cert_path: Optional[str] = Field(None, description="SSL certificate path")
    ssl_key_path: Optional[str] = Field(None, description="SSL private key path")
    
    # Monitoring Configuration
    enable_metrics: bool = Field(True, description="Enable Prometheus metrics")
    metrics_port: int = Field(9090, description="Metrics server port")
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v.upper()
    
    @validator("database_url")
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL."""
        if not v.startswith("postgresql://"):
            raise ValueError("Database URL must start with 'postgresql://'")
        return v
    
    @validator("supabase_url")
    def validate_supabase_url(cls, v: str) -> str:
        """Validate Supabase URL."""
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("Supabase URL must start with 'http://' or 'https://'")
        return v.rstrip("/")


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()