#!/usr/bin/env python3
"""
Script para testar a conexão MCP com o servidor Supabase
"""

import json
import urllib.request
import urllib.parse
import sys

def test_mcp_connection(server_url="http://localhost:8001", api_key="mcp-test-key-2024-rardevops"):
    """Testa a conexão com o servidor MCP."""
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'User-Agent': 'MCP-Test-Client/1.0'
    }
    
    print("🔍 Testando conexão MCP com servidor Supabase...")
    print(f"   URL: {server_url}")
    print(f"   API Key: {api_key[:20]}...")
    print()
    
    # Teste 1: Health Check
    print("1️⃣ Testando Health Check...")
    try:
        req = urllib.request.Request(f"{server_url}/health", headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            print(f"   ✅ Status: {data.get('status', 'unknown')}")
            print(f"   📊 Response: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    print()
    
    # Teste 2: Server Info
    print("2️⃣ Testando Server Info...")
    try:
        req = urllib.request.Request(f"{server_url}/info", headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            print(f"   ✅ Nome: {data.get('name', 'unknown')}")
            print(f"   📦 Versão: {data.get('version', 'unknown')}")
            print(f"   📊 Response: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    print()
    
    # Teste 3: Listar Ferramentas MCP
    print("3️⃣ Testando MCP Tools...")
    try:
        req = urllib.request.Request(f"{server_url}/mcp/tools", headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if isinstance(data, list):
                print(f"   ✅ Encontradas {len(data)} ferramentas:")
                for i, tool in enumerate(data[:5], 1):  # Mostra apenas as primeiras 5
                    name = tool.get('name', 'unknown')
                    description = tool.get('description', 'No description')
                    print(f"      {i}. {name}: {description[:60]}...")
                if len(data) > 5:
                    print(f"      ... e mais {len(data) - 5} ferramentas")
            else:
                print(f"   📊 Response: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    print()
    
    # Teste 4: Executar uma ferramenta simples
    print("4️⃣ Testando execução de ferramenta...")
    try:
        test_data = {
            "tool": "get_server_info",
            "parameters": {}
        }
        req = urllib.request.Request(
            f"{server_url}/mcp/execute", 
            data=json.dumps(test_data).encode(),
            headers=headers
        )
        req.get_method = lambda: 'POST'
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            print(f"   ✅ Execução bem-sucedida!")
            print(f"   📊 Response: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    print()
    
    print("🎯 Teste de conexão MCP concluído!")
    print()
    print("📋 Para usar no Kiro IDE:")
    print("   1. Copie o arquivo configs/kiro-ide-config.json")
    print("   2. Substitua 'SEU_IP_DA_VM' pelo IP real da sua VM")
    print("   3. Configure no Kiro IDE MCP settings")

if __name__ == "__main__":
    # Permite passar URL e API key como argumentos
    server_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"
    api_key = sys.argv[2] if len(sys.argv) > 2 else "mcp-test-key-2024-rardevops"
    
    test_mcp_connection(server_url, api_key)