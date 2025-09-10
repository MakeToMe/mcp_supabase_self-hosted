#!/usr/bin/env python
"""
Windows-compatible MCP Client for Supabase Self-Hosted Server
Uses urllib instead of curl for Windows compatibility
"""

import json
import sys
import urllib.request
import urllib.parse
import os
import logging

# Configure logging to stderr
logging.basicConfig(level=logging.ERROR, stream=sys.stderr)
logger = logging.getLogger(__name__)

class WindowsMCPClient:
    def __init__(self):
        self.server_url = os.getenv('MCP_SERVER_URL', 'http://localhost:8001')
        self.api_key = os.getenv('MCP_API_KEY', 'mcp-test-key-2024-rardevops')
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'Kiro-MCP-Windows-Client/1.0'
        }
    
    def make_request(self, path: str, method: str = 'GET', data: dict = None) -> dict:
        """Make HTTP request using urllib."""
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
            error_body = e.read().decode('utf-8') if hasattr(e, 'read') else str(e)
            return {
                'error': {
                    'code': -32603,
                    'message': f'HTTP {e.code}: {error_body}'
                }
            }
        except urllib.error.URLError as e:
            return {
                'error': {
                    'code': -32603,
                    'message': f'Connection error: {str(e)}'
                }
            }
        except Exception as e:
            return {
                'error': {
                    'code': -32603,
                    'message': f'Request failed: {str(e)}'
                }
            }
    
    def handle_initialize(self, params: dict) -> dict:
        """Handle MCP initialize."""
        return {
            'protocolVersion': '2024-11-05',
            'capabilities': {
                'tools': {}
            },
            'serverInfo': {
                'name': 'supabase-mcp-windows-client',
                'version': '1.0.0'
            }
        }
    
    def handle_tools_list(self, params: dict) -> dict:
        """Handle tools/list."""
        response = self.make_request('/mcp/tools')
        if 'error' in response:
            return response
        
        # Extract tools from response
        if isinstance(response, dict) and 'tools' in response:
            tools = response['tools']
        elif isinstance(response, list):
            tools = response
        else:
            tools = []
        
        return {'tools': tools}
    
    def handle_tools_call(self, params: dict) -> dict:
        """Handle tools/call."""
        name = params.get('name', '')
        arguments = params.get('arguments', {})
        
        response = self.make_request('/mcp/execute', 'POST', {
            'tool': name,
            'parameters': arguments
        })
        
        if 'error' in response:
            return response
        
        # Format response as MCP content
        content_text = json.dumps(response, indent=2) if response else "No response"
        
        return {
            'content': [
                {
                    'type': 'text',
                    'text': content_text
                }
            ]
        }
    
    def handle_request(self, request: dict) -> dict:
        """Handle JSON-RPC request."""
        method = request.get('method', '')
        params = request.get('params', {})
        request_id = request.get('id')
        
        try:
            if method == 'initialize':
                result = self.handle_initialize(params)
            elif method == 'tools/list':
                result = self.handle_tools_list(params)
            elif method == 'tools/call':
                result = self.handle_tools_call(params)
            else:
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'error': {
                        'code': -32601,
                        'message': f'Method not found: {method}'
                    }
                }
            
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Error handling {method}: {e}")
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'error': {
                    'code': -32603,
                    'message': str(e)
                }
            }
    
    def run(self):
        """Main loop."""
        logger.info(f"Starting Windows MCP client for {self.server_url}")
        
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    request = json.loads(line)
                    logger.info(f"Processing: {request.get('method', 'unknown')}")
                    
                    response = self.handle_request(request)
                    print(json.dumps(response), flush=True)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                    error_response = {
                        'jsonrpc': '2.0',
                        'id': None,
                        'error': {
                            'code': -32700,
                            'message': 'Parse error'
                        }
                    }
                    print(json.dumps(error_response), flush=True)
                    
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                    error_response = {
                        'jsonrpc': '2.0',
                        'id': None,
                        'error': {
                            'code': -32603,
                            'message': f'Internal error: {str(e)}'
                        }
                    }
                    print(json.dumps(error_response), flush=True)
                    
        except KeyboardInterrupt:
            logger.info("Client stopped")
        except Exception as e:
            logger.error(f"Fatal error: {e}")

if __name__ == '__main__':
    client = WindowsMCPClient()
    client.run()