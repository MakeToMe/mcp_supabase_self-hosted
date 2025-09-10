#!/usr/bin/env python3
"""
MCP Client for Supabase Self-Hosted Server
Connects Kiro IDE to the Supabase MCP Server via HTTP
"""

import json
import sys
import urllib.request
import urllib.parse
import os
from typing import Dict, Any, Optional

class SupabaseMCPClient:
    def __init__(self):
        self.server_url = os.getenv('MCP_SERVER_URL', 'http://localhost:8001')
        self.api_key = os.getenv('MCP_API_KEY', 'mcp-test-key-2024-rardevops')
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'Kiro-MCP-Client/1.0'
        }
    
    def make_request(self, path: str, method: str = 'GET', data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make HTTP request to MCP server."""
        try:
            url = f"{self.server_url.rstrip('/')}{path}"
            req = urllib.request.Request(url, headers=self.headers)
            req.get_method = lambda: method
            
            if data:
                req.data = json.dumps(data).encode('utf-8')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                response_data = response.read().decode('utf-8')
                return json.loads(response_data)
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else str(e)
            return {
                'error': f'HTTP {e.code}: {error_body}',
                'code': e.code
            }
        except urllib.error.URLError as e:
            return {
                'error': f'Connection error: {str(e)}',
                'code': 'CONNECTION_ERROR'
            }
        except json.JSONDecodeError as e:
            return {
                'error': f'Invalid JSON response: {str(e)}',
                'code': 'JSON_ERROR'
            }
        except Exception as e:
            return {
                'error': f'Unexpected error: {str(e)}',
                'code': 'UNKNOWN_ERROR'
            }
    
    def handle_tools_list(self) -> Dict[str, Any]:
        """Handle tools/list request."""
        return self.make_request('/mcp/tools')
    
    def handle_tools_call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        return self.make_request('/mcp/execute', 'POST', {
            'tool': name,
            'parameters': arguments
        })
    
    def handle_health_check(self) -> Dict[str, Any]:
        """Handle health check."""
        return self.make_request('/health')
    
    def handle_server_info(self) -> Dict[str, Any]:
        """Handle server info request."""
        return self.make_request('/info')
    
    def handle_mcp_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP request from Kiro IDE."""
        method = request.get('method', '')
        params = request.get('params', {})
        
        if method == 'tools/list':
            return self.handle_tools_list()
        elif method == 'tools/call':
            name = params.get('name', '')
            arguments = params.get('arguments', {})
            return self.handle_tools_call(name, arguments)
        elif method == 'health':
            return self.handle_health_check()
        elif method == 'info':
            return self.handle_server_info()
        else:
            return {
                'error': f'Unknown method: {method}',
                'available_methods': ['tools/list', 'tools/call', 'health', 'info']
            }
    
    def run(self):
        """Main loop to handle MCP requests."""
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    request = json.loads(line)
                    response = self.handle_mcp_request(request)
                    print(json.dumps(response), flush=True)
                except json.JSONDecodeError as e:
                    error_response = {
                        'error': f'Invalid JSON request: {str(e)}',
                        'code': 'INVALID_JSON'
                    }
                    print(json.dumps(error_response), flush=True)
                except Exception as e:
                    error_response = {
                        'error': f'Request processing error: {str(e)}',
                        'code': 'PROCESSING_ERROR'
                    }
                    print(json.dumps(error_response), flush=True)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            error_response = {
                'error': f'Client error: {str(e)}',
                'code': 'CLIENT_ERROR'
            }
            print(json.dumps(error_response), flush=True)

if __name__ == '__main__':
    client = SupabaseMCPClient()
    client.run()