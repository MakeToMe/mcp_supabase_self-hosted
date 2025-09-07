"""Tests for storage service."""

import base64
from unittest.mock import MagicMock, patch

import pytest

from supabase_mcp_server.services.storage import (
    StorageFile,
    StorageResult,
    StorageService,
)


class TestStorageFile:
    """Test StorageFile class."""
    
    def test_storage_file_creation(self):
        """Test StorageFile creation."""
        file_info = StorageFile(
            name="test.txt",
            id="123",
            size=1024,
            mime_type="text/plain",
            created_at="2024-01-01T00:00:00Z"
        )
        
        assert file_info.name == "test.txt"
        assert file_info.id == "123"
        assert file_info.size == 1024
        assert file_info.mime_type == "text/plain"
        assert file_info.created_at == "2024-01-01T00:00:00Z"


class TestStorageResult:
    """Test StorageResult class."""
    
    def test_storage_result_success(self):
        """Test successful storage result."""
        result = StorageResult(
            success=True,
            data=["file1.txt", "file2.txt"],
            message="Files listed successfully"
        )
        
        assert result.success is True
        assert result.data == ["file1.txt", "file2.txt"]
        assert result.message == "Files listed successfully"
        assert result.error is None
    
    def test_storage_result_error(self):
        """Test error storage result."""
        result = StorageResult(
            success=False,
            error="Bucket not found"
        )
        
        assert result.success is False
        assert result.error == "Bucket not found"
        assert result.data is None


class TestStorageService:
    """Test StorageService class."""
    
    @pytest.fixture
    def storage_service(self, override_settings):
        """Create a storage service instance."""
        return StorageService()
    
    def test_storage_service_creation(self, storage_service):
        """Test storage service creation."""
        assert storage_service.settings is not None
    
    @patch('supabase_mcp_server.services.storage.supabase_api_service')
    async def test_list_buckets_success(self, mock_api_service, storage_service):
        """Test successful bucket listing."""
        # Mock client and response
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.id = "bucket1"
        mock_bucket.name = "test-bucket"
        mock_bucket.public = True
        mock_bucket.created_at = "2024-01-01T00:00:00Z"
        mock_bucket.updated_at = "2024-01-01T00:00:00Z"
        
        mock_client.storage.list_buckets.return_value = [mock_bucket]
        mock_api_service.get_client.return_value = mock_client
        
        result = await storage_service.list_buckets()
        
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]["name"] == "test-bucket"
        assert result.data[0]["public"] is True
    
    @patch('supabase_mcp_server.services.storage.supabase_api_service')
    async def test_list_buckets_no_client(self, mock_api_service, storage_service):
        """Test bucket listing without client."""
        mock_api_service.get_client.return_value = None
        
        result = await storage_service.list_buckets()
        
        assert result.success is False
        assert "not initialized" in result.error
    
    @patch('supabase_mcp_server.services.storage.supabase_api_service')
    async def test_list_files_success(self, mock_api_service, storage_service):
        """Test successful file listing."""
        # Mock client and response
        mock_client = MagicMock()
        mock_storage = MagicMock()
        mock_bucket = MagicMock()
        
        mock_file_info = {
            "name": "test.txt",
            "id": "123",
            "metadata": {
                "size": 1024,
                "mimetype": "text/plain"
            },
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
        
        mock_bucket.list.return_value = [mock_file_info]
        mock_storage.from_.return_value = mock_bucket
        mock_client.storage = mock_storage
        mock_api_service.get_client.return_value = mock_client
        
        result = await storage_service.list_files("test-bucket", "folder/")
        
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0].name == "test.txt"
        assert result.data[0].size == 1024
        assert result.data[0].mime_type == "text/plain"
    
    @patch('supabase_mcp_server.services.storage.supabase_api_service')
    async def test_upload_file_success(self, mock_api_service, storage_service):
        """Test successful file upload."""
        # Mock client and response
        mock_client = MagicMock()
        mock_storage = MagicMock()
        mock_bucket = MagicMock()
        
        mock_bucket.upload.return_value = {"path": "test.txt"}
        mock_storage.from_.return_value = mock_bucket
        mock_client.storage = mock_storage
        mock_api_service.get_client.return_value = mock_client
        
        # Test with text content
        result = await storage_service.upload_file(
            "test-bucket",
            "test.txt",
            "Hello, world!",
            "text/plain"
        )
        
        assert result.success is True
        assert result.data == {"path": "test.txt"}
        mock_bucket.upload.assert_called_once()
    
    @patch('supabase_mcp_server.services.storage.supabase_api_service')
    async def test_upload_file_base64(self, mock_api_service, storage_service):
        """Test file upload with base64 content."""
        # Mock client and response
        mock_client = MagicMock()
        mock_storage = MagicMock()
        mock_bucket = MagicMock()
        
        mock_bucket.upload.return_value = {"path": "test.txt"}
        mock_storage.from_.return_value = mock_bucket
        mock_client.storage = mock_storage
        mock_api_service.get_client.return_value = mock_client
        
        # Test with base64 content
        content = base64.b64encode(b"Hello, world!").decode('utf-8')
        result = await storage_service.upload_file(
            "test-bucket",
            "test.txt",
            content
        )
        
        assert result.success is True
        mock_bucket.upload.assert_called_once()
    
    @patch('supabase_mcp_server.services.storage.supabase_api_service')
    async def test_download_file_success(self, mock_api_service, storage_service):
        """Test successful file download."""
        # Mock client and response
        mock_client = MagicMock()
        mock_storage = MagicMock()
        mock_bucket = MagicMock()
        
        file_content = b"Hello, world!"
        mock_bucket.download.return_value = file_content
        mock_storage.from_.return_value = mock_bucket
        mock_client.storage = mock_storage
        mock_api_service.get_client.return_value = mock_client
        
        # Test download as base64
        result = await storage_service.download_file("test-bucket", "test.txt", as_base64=True)
        
        assert result.success is True
        assert result.data == base64.b64encode(file_content).decode('utf-8')
        
        # Test download as bytes
        result = await storage_service.download_file("test-bucket", "test.txt", as_base64=False)
        
        assert result.success is True
        assert result.data == file_content
    
    @patch('supabase_mcp_server.services.storage.supabase_api_service')
    async def test_delete_file_success(self, mock_api_service, storage_service):
        """Test successful file deletion."""
        # Mock client and response
        mock_client = MagicMock()
        mock_storage = MagicMock()
        mock_bucket = MagicMock()
        
        mock_bucket.remove.return_value = {"message": "Files deleted"}
        mock_storage.from_.return_value = mock_bucket
        mock_client.storage = mock_storage
        mock_api_service.get_client.return_value = mock_client
        
        # Test single file deletion
        result = await storage_service.delete_file("test-bucket", "test.txt")
        
        assert result.success is True
        mock_bucket.remove.assert_called_once_with(["test.txt"])
        
        # Test multiple file deletion
        result = await storage_service.delete_file("test-bucket", ["file1.txt", "file2.txt"])
        
        assert result.success is True
        mock_bucket.remove.assert_called_with(["file1.txt", "file2.txt"])
    
    @patch('supabase_mcp_server.services.storage.supabase_api_service')
    async def test_move_file_success(self, mock_api_service, storage_service):
        """Test successful file move."""
        # Mock client and response
        mock_client = MagicMock()
        mock_storage = MagicMock()
        mock_bucket = MagicMock()
        
        mock_bucket.move.return_value = {"message": "File moved"}
        mock_storage.from_.return_value = mock_bucket
        mock_client.storage = mock_storage
        mock_api_service.get_client.return_value = mock_client
        
        result = await storage_service.move_file("test-bucket", "old.txt", "new.txt")
        
        assert result.success is True
        mock_bucket.move.assert_called_once_with("old.txt", "new.txt")
    
    @patch('supabase_mcp_server.services.storage.supabase_api_service')
    async def test_copy_file_success(self, mock_api_service, storage_service):
        """Test successful file copy."""
        # Mock client and response
        mock_client = MagicMock()
        mock_storage = MagicMock()
        mock_bucket = MagicMock()
        
        mock_bucket.copy.return_value = {"message": "File copied"}
        mock_storage.from_.return_value = mock_bucket
        mock_client.storage = mock_storage
        mock_api_service.get_client.return_value = mock_client
        
        result = await storage_service.copy_file("test-bucket", "source.txt", "copy.txt")
        
        assert result.success is True
        mock_bucket.copy.assert_called_once_with("source.txt", "copy.txt")
    
    @patch('supabase_mcp_server.services.storage.supabase_api_service')
    async def test_get_public_url_success(self, mock_api_service, storage_service):
        """Test successful public URL generation."""
        # Mock client and response
        mock_client = MagicMock()
        mock_storage = MagicMock()
        mock_bucket = MagicMock()
        
        public_url = "https://example.com/bucket/file.txt"
        mock_bucket.get_public_url.return_value = public_url
        mock_storage.from_.return_value = mock_bucket
        mock_client.storage = mock_storage
        mock_api_service.get_client.return_value = mock_client
        
        result = await storage_service.get_public_url("test-bucket", "file.txt")
        
        assert result.success is True
        assert result.data == public_url
        mock_bucket.get_public_url.assert_called_once_with("file.txt")
    
    @patch('supabase_mcp_server.services.storage.supabase_api_service')
    async def test_create_signed_url_success(self, mock_api_service, storage_service):
        """Test successful signed URL creation."""
        # Mock client and response
        mock_client = MagicMock()
        mock_storage = MagicMock()
        mock_bucket = MagicMock()
        
        signed_url = "https://example.com/bucket/file.txt?token=abc123"
        mock_bucket.create_signed_url.return_value = signed_url
        mock_storage.from_.return_value = mock_bucket
        mock_client.storage = mock_storage
        mock_api_service.get_client.return_value = mock_client
        
        result = await storage_service.create_signed_url("test-bucket", "file.txt", 7200)
        
        assert result.success is True
        assert result.data == signed_url
        mock_bucket.create_signed_url.assert_called_once_with("file.txt", 7200)
    
    @patch('supabase_mcp_server.services.storage.supabase_api_service')
    async def test_operation_failure(self, mock_api_service, storage_service):
        """Test operation failure handling."""
        # Mock client that raises exception
        mock_client = MagicMock()
        mock_storage = MagicMock()
        mock_bucket = MagicMock()
        
        mock_bucket.list.side_effect = Exception("Storage error")
        mock_storage.from_.return_value = mock_bucket
        mock_client.storage = mock_storage
        mock_api_service.get_client.return_value = mock_client
        
        result = await storage_service.list_files("test-bucket")
        
        assert result.success is False
        assert "Storage error" in result.error