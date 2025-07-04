#!/usr/bin/env python3
"""Test Claude authentication in CC Executor."""

import requests
import json
import time

API_URL = "http://localhost:8001"

def test_auth():
    """Test Claude authentication."""
    print("Testing Claude authentication...")
    
    response = requests.post(f"{API_URL}/auth/claude")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nAuthentication Status: {result['status']}")
        print(f"Message: {result['message']}")
        
        if result.get('auth_url'):
            print(f"\n🔗 Authentication URL: {result['auth_url']}")
            print("\nInstructions:")
            for i, instruction in enumerate(result.get('instructions', []), 1):
                print(f"  {i}. {instruction}")
        
        if result.get('raw_output'):
            print(f"\nRaw output:\n{result['raw_output']}")
        
        if result.get('error'):
            print(f"\nError details: {result['error']}")
            
        return result
    else:
        print(f"Error: {response.text}")
        return None

def main():
    """Run authentication test."""
    print("CC Executor Claude Authentication Test")
    print("=" * 50)
    
    # First check health
    try:
        health_response = requests.get(f"{API_URL}/health")
        print(f"Health check: {health_response.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")
        return
    
    # Test authentication
    print("\n" + "=" * 50)
    auth_result = test_auth()
    
    if auth_result and auth_result['status'] == 'authentication_required':
        print("\n⚠️  Please complete the authentication process and then run your tests.")
    elif auth_result and auth_result['status'] == 'ready':
        print("\n✅ Claude Code is authenticated and ready to use!")
    else:
        print("\n❌ Authentication failed.")

if __name__ == "__main__":
    main()