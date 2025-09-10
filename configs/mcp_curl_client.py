#!/usr/bin/env python3
"""
Simple MCP Client using curl for HTTP requests
More reliable than urllib for network requests
"""

import json
import sys
import subprocess
import os
import logging

# Configure logging
logging.basicConfig(level=logging.ERROR, stream=sys.stderr)
logger = logging.getLogger(__name__)

class CurlMCPClient:
    def __init__(self):
        self.server_url = os.getenv('MCP_SERVER_URL', 'http://localhost:8001')
        self.api_key = os.getenv('MCP_API_KEY', 'mcp-test-key-2024-rardevops')
    
    def curl_request(self, path: str, method: str = 'GET', data: dict = None) -> dict:
        """Make HTTP request using curl."""
        try:
            url = f"{self.server_url.rstrip('/')}{path}"
            cmd = [
                'curl', '-s', '-X', method,
                '-H', f'Authorization: Bearer {self.api_key}',
                '-H', 'Content-Type: application/json',
                '--connect-timeout', '10',
                '--max-time', '30'
            ]
            
            if data:
                cmd.extend(['-d', json.dumps(data)])
            
            cmd.append(url)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
            
            if result.returncode != 0:
                return {
                    'error': {
                        'code': -32603,
                        'message': f'Curl error: {result.stderr}'
                    }
                }
            
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {
                    'error': {
                        'code': -32603,
                        'message': f'Invalid JSON response: {result.stdout[:200]}'
                    }
                }
                
        except subprocess.TimeoutExpired:
            return {
                'error': {
                    'code': -32603,
                    'message': 'Request timeout'
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
                'name': 'supabase-mcp-curl-client',
                'version': '1.0.0'
            }
        }
    
    def handle_tools_list(self, params: dict) -> dict:
        """Handle tools/list."""
        response = self.curl_request('/mcp/tools')
        if 'error' in response:
            return response
        
        tools = response if isinstance(response, list) else []
        return {'tools': tools}
    
    def handle_tools_call(self, params: dict) -> dict:
        """Handle tools/call."""
        name = params.get('name', '')
        arguments = params.get('arguments', {})
        
        response = self.curl_request('/mcp/execute', 'POST', {
            'tool': name,
            'parameters': arguments
        })
        
        if 'error' in response:
            return response
        
        return {
            'content': [
                {
                    'type': 'text',
                    'text': json.dumps(response, indent=2)
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
            logger.error(f"Error: {e}")
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
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    request = json.loads(line)
                    response = self.handle_request(request)
                    print(json.dumps(response), flush=True)
                except json.JSONDecodeError:
                    error_response = {
                        'jsonrpc': '2.0',
                        'id': None,
                        'error': {
                            'code': -32700,
                            'message': 'Parse error'
                        }
                    }
                    print(json.dumps(error_response), flush=True)
        except KeyboardInterrupt:
            pass

if __name__ == '__main__':
    client = CurlMCPClient()
    client.run()