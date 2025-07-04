#!/usr/bin/env python3
"""Test the complete authentication workflow for CC Executor Docker deployment."""

import requests
import json
import sys

API_URL = "http://localhost:8001"

def test_auth_workflow():
    """Test the complete authentication workflow."""
    print("CC Executor Docker Authentication Workflow Test")
    print("=" * 60)
    
    # Step 1: Check health
    print("\n1. Checking API health...")
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            print("   ✅ API is healthy")
        else:
            print(f"   ❌ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Cannot connect to API: {e}")
        print("   Make sure Docker containers are running: docker compose up -d")
        return False
    
    # Step 2: Check authentication status
    print("\n2. Checking authentication status...")
    try:
        response = requests.get(f"{API_URL}/auth/status")
        auth_data = response.json()
        
        if auth_data['status'] == 'authenticated':
            print("   ✅ Claude Code is authenticated")
            print(f"   Message: {auth_data['message']}")
        else:
            print("   ⚠️  Claude Code is not authenticated")
            print(f"   Message: {auth_data['message']}")
            print("\n   Instructions for authentication:")
            for step in auth_data['instructions']['steps']:
                if step:  # Skip empty lines
                    print(f"   {step}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error checking auth status: {e}")
        return False
    
    # Step 3: Test deprecated endpoint
    print("\n3. Testing deprecated /auth/claude endpoint...")
    try:
        response = requests.post(f"{API_URL}/auth/claude")
        if response.status_code == 200:
            dep_data = response.json()
            if dep_data['status'] == 'deprecated':
                print("   ✅ Deprecated endpoint returns correct warning")
                print(f"   Alternative: {dep_data['alternative']}")
            else:
                print(f"   ⚠️  Unexpected response: {dep_data}")
        else:
            print(f"   ❌ Unexpected status code: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error testing deprecated endpoint: {e}")
    
    # Step 4: Test actual Claude execution
    print("\n4. Testing Claude command execution...")
    try:
        request_data = {
            "tasks": ["What is the capital of France?"],
            "timeout_per_task": 30
        }
        
        response = requests.post(f"{API_URL}/execute", json=request_data)
        if response.status_code == 200:
            result = response.json()
            if result['failed_tasks'] == 0:
                print("   ✅ Claude command executed successfully")
                task_result = result['results'][0]
                output = task_result['stdout'].strip()
                print(f"   Claude's answer: {output}")
                
                # Verify it's a reasonable answer
                if "Paris" in output:
                    print("   ✅ Answer is correct!")
                else:
                    print(f"   ⚠️  Unexpected answer: {output}")
            else:
                print("   ❌ Claude command failed")
                print(f"   Error: {result['results'][0].get('stderr', 'Unknown error')}")
                return False
        else:
            print(f"   ❌ Execute request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error executing Claude command: {e}")
        return False
    
    return True

def main():
    """Run the authentication workflow test."""
    success = test_auth_workflow()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ All authentication tests passed!")
        print("\nDocker deployment is working correctly with:")
        print("- API health endpoint: GET /health")
        print("- Auth status endpoint: GET /auth/status")
        print("- Claude execution: POST /execute")
        print("- Deprecated auth endpoint: POST /auth/claude")
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("❌ Authentication workflow test failed!")
        print("\nTroubleshooting:")
        print("1. Ensure Docker containers are running: docker compose ps")
        print("2. Check logs: docker compose logs -f")
        print("3. Verify host authentication: ls -la ~/.claude/.credentials.json")
        print("4. Restart containers: docker compose down && docker compose up -d")
        sys.exit(1)

if __name__ == "__main__":
    main()