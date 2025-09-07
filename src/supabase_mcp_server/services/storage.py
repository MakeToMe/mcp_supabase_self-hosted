"""Supabase Storage management service."""

import base64
import mimetypes
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from supabase_mcp_server.config import get_settings
from supabase_mcp_server.core.logging import get_logger
from supabase_mcp_server.services.supabase_api import supabase_api_service

logger = get_logger(__name__)


@dataclass
class StorageFile:
    """Information about a storage file."""
    name: str
    id: Optional[str] = None
    size: Optional[int] = None
    mime_type: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_accessed_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class StorageResult:
    """Result of a storage operation."""
    success: bool
    data: Optional[Union[List[StorageFile], StorageFile, str, bytes]] = None
    error: Optional[str] = None
    message: Optional[str] = None


class StorageService:
    """Service for Supabase Storage operations."""
    
    def __init__(self):
        """Initialize the storage service."""
        self.settings = get_settings()
    
    async def list_buckets(self) -> StorageResult:
        """List all storage buckets."""
        try:
            client = supabase_api_service.get_client()
            if not client:
                return StorageResult(
                    success=False,
                    error="Supabase client not initialized"
                )
            
            logger.debug("Listing storage buckets")
            
            # Get buckets
            response = client.storage.list_buckets()
            
            buckets = []
            for bucket in response:
                buckets.append({
                    "id": bucket.id,
                    "name": bucket.name,
                    "public": bucket.public,
                    "created_at": bucket.created_at,
                    "updated_at": bucket.updated_at
                })
            
            logger.info("Listed storage buckets", count=len(buckets))
            
            return StorageResult(
                success=True,
                data=buckets,
                message=f"Found {len(buckets)} buckets"
            )
            
        except Exception as e:
            logger.error("Failed to list buckets", error=str(e))
            return StorageResult(
                success=False,
                error=f"Failed to list buckets: {str(e)}"
            )
    
    async def list_files(
        self,
        bucket: str,
        path: str = "",
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> StorageResult:
        """List files in a storage bucket."""
        try:
            client = supabase_api_service.get_client()
            if not client:
                return StorageResult(
                    success=False,
                    error="Supabase client not initialized"
                )
            
            logger.debug("Listing files", bucket=bucket, path=path)
            
            # List files
            options = {}
            if limit:
                options["limit"] = limit
            if offset:
                options["offset"] = offset
            
            response = client.storage.from_(bucket).list(path, options)
            
            files = []
            for file_info in response:
                files.append(StorageFile(
                    name=file_info.get("name", ""),
                    id=file_info.get("id"),
                    size=file_info.get("metadata", {}).get("size"),
                    mime_type=file_info.get("metadata", {}).get("mimetype"),
                    created_at=file_info.get("created_at"),
                    updated_at=file_info.get("updated_at"),
                    last_accessed_at=file_info.get("last_accessed_at"),
                    metadata=file_info.get("metadata", {})
                ))
            
            logger.info("Listed files", bucket=bucket, path=path, count=len(files))
            
            return StorageResult(
                success=True,
                data=files,
                message=f"Found {len(files)} files in {bucket}/{path}"
            )
            
        except Exception as e:
            logger.error("Failed to list files", bucket=bucket, path=path, error=str(e))
            return StorageResult(
                success=False,
                error=f"Failed to list files: {str(e)}"
            )
    
    async def upload_file(
        self,
        bucket: str,
        path: str,
        content: Union[str, bytes],
        content_type: Optional[str] = None,
        upsert: bool = False
    ) -> StorageResult:
        """Upload a file to storage."""
        try:
            client = supabase_api_service.get_client()
            if not client:
                return StorageResult(
                    success=False,
                    error="Supabase client not initialized"
                )
            
            logger.debug("Uploading file", bucket=bucket, path=path, size=len(content))
            
            # Handle content encoding
            if isinstance(content, str):
                try:
                    # Try to decode as base64 first
                    file_content = base64.b64decode(content)
                except Exception:
                    # If not base64, treat as text
                    file_content = content.encode('utf-8')
            else:
                file_content = content
            
            # Determine content type
            if not content_type:
                content_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
            
            # Upload options
            options = {
                "content_type": content_type,
                "upsert": upsert
            }
            
            # Upload file
            response = client.storage.from_(bucket).upload(path, file_content, options)
            
            logger.info("File uploaded successfully", bucket=bucket, path=path)
            
            return StorageResult(
                success=True,
                data=response,
                message=f"File uploaded to {bucket}/{path}"
            )
            
        except Exception as e:
            logger.error("Failed to upload file", bucket=bucket, path=path, error=str(e))
            return StorageResult(
                success=False,
                error=f"Failed to upload file: {str(e)}"
            )
    
    async def download_file(
        self,
        bucket: str,
        path: str,
        as_base64: bool = False
    ) -> StorageResult:
        """Download a file from storage."""
        try:
            client = supabase_api_service.get_client()
            if not client:
                return StorageResult(
                    success=False,
                    error="Supabase client not initialized"
                )
            
            logger.debug("Downloading file", bucket=bucket, path=path)
            
            # Download file
            response = client.storage.from_(bucket).download(path)
            
            if as_base64:
                # Encode as base64 for text transmission
                content = base64.b64encode(response).decode('utf-8')
            else:
                content = response
            
            logger.info("File downloaded successfully", bucket=bucket, path=path, size=len(response))
            
            return StorageResult(
                success=True,
                data=content,
                message=f"File downloaded from {bucket}/{path}"
            )
            
        except Exception as e:
            logger.error("Failed to download file", bucket=bucket, path=path, error=str(e))
            return StorageResult(
                success=False,
                error=f"Failed to download file: {str(e)}"
            )
    
    async def delete_file(
        self,
        bucket: str,
        paths: Union[str, List[str]]
    ) -> StorageResult:
        """Delete file(s) from storage."""
        try:
            client = supabase_api_service.get_client()
            if not client:
                return StorageResult(
                    success=False,
                    error="Supabase client not initialized"
                )
            
            # Ensure paths is a list
            if isinstance(paths, str):
                paths = [paths]
            
            logger.debug("Deleting files", bucket=bucket, paths=paths)
            
            # Delete files
            response = client.storage.from_(bucket).remove(paths)
            
            logger.info("Files deleted successfully", bucket=bucket, count=len(paths))
            
            return StorageResult(
                success=True,
                data=response,
                message=f"Deleted {len(paths)} file(s) from {bucket}"
            )
            
        except Exception as e:
            logger.error("Failed to delete files", bucket=bucket, paths=paths, error=str(e))
            return StorageResult(
                success=False,
                error=f"Failed to delete files: {str(e)}"
            )
    
    async def move_file(
        self,
        bucket: str,
        from_path: str,
        to_path: str
    ) -> StorageResult:
        """Move/rename a file in storage."""
        try:
            client = supabase_api_service.get_client()
            if not client:
                return StorageResult(
                    success=False,
                    error="Supabase client not initialized"
                )
            
            logger.debug("Moving file", bucket=bucket, from_path=from_path, to_path=to_path)
            
            # Move file
            response = client.storage.from_(bucket).move(from_path, to_path)
            
            logger.info("File moved successfully", bucket=bucket, from_path=from_path, to_path=to_path)
            
            return StorageResult(
                success=True,
                data=response,
                message=f"File moved from {from_path} to {to_path} in {bucket}"
            )
            
        except Exception as e:
            logger.error("Failed to move file", bucket=bucket, from_path=from_path, to_path=to_path, error=str(e))
            return StorageResult(
                success=False,
                error=f"Failed to move file: {str(e)}"
            )
    
    async def copy_file(
        self,
        bucket: str,
        from_path: str,
        to_path: str
    ) -> StorageResult:
        """Copy a file in storage."""
        try:
            client = supabase_api_service.get_client()
            if not client:
                return StorageResult(
                    success=False,
                    error="Supabase client not initialized"
                )
            
            logger.debug("Copying file", bucket=bucket, from_path=from_path, to_path=to_path)
            
            # Copy file
            response = client.storage.from_(bucket).copy(from_path, to_path)
            
            logger.info("File copied successfully", bucket=bucket, from_path=from_path, to_path=to_path)
            
            return StorageResult(
                success=True,
                data=response,
                message=f"File copied from {from_path} to {to_path} in {bucket}"
            )
            
        except Exception as e:
            logger.error("Failed to copy file", bucket=bucket, from_path=from_path, to_path=to_path, error=str(e))
            return StorageResult(
                success=False,
                error=f"Failed to copy file: {str(e)}"
            )
    
    async def get_public_url(
        self,
        bucket: str,
        path: str
    ) -> StorageResult:
        """Get public URL for a file."""
        try:
            client = supabase_api_service.get_client()
            if not client:
                return StorageResult(
                    success=False,
                    error="Supabase client not initialized"
                )
            
            logger.debug("Getting public URL", bucket=bucket, path=path)
            
            # Get public URL
            response = client.storage.from_(bucket).get_public_url(path)
            
            logger.info("Got public URL", bucket=bucket, path=path)
            
            return StorageResult(
                success=True,
                data=response,
                message=f"Public URL for {bucket}/{path}"
            )
            
        except Exception as e:
            logger.error("Failed to get public URL", bucket=bucket, path=path, error=str(e))
            return StorageResult(
                success=False,
                error=f"Failed to get public URL: {str(e)}"
            )
    
    async def create_signed_url(
        self,
        bucket: str,
        path: str,
        expires_in: int = 3600
    ) -> StorageResult:
        """Create a signed URL for temporary access."""
        try:
            client = supabase_api_service.get_client()
            if not client:
                return StorageResult(
                    success=False,
                    error="Supabase client not initialized"
                )
            
            logger.debug("Creating signed URL", bucket=bucket, path=path, expires_in=expires_in)
            
            # Create signed URL
            response = client.storage.from_(bucket).create_signed_url(path, expires_in)
            
            logger.info("Created signed URL", bucket=bucket, path=path, expires_in=expires_in)
            
            return StorageResult(
                success=True,
                data=response,
                message=f"Signed URL for {bucket}/{path} (expires in {expires_in}s)"
            )
            
        except Exception as e:
            logger.error("Failed to create signed URL", bucket=bucket, path=path, error=str(e))
            return StorageResult(
                success=False,
                error=f"Failed to create signed URL: {str(e)}"
            )


# Global storage service instance
storage_service = StorageService()