#!/usr/bin/env python3
"""
Test script for secure Docker deployment of CC Executor.

This script verifies that the secure deployment is working correctly
by testing various security features and execution scenarios.
"""

import asyncio
import httpx
import json
import sys
from datetime import datetime
from typing import Dict, Any


class SecureDeploymentTester:
    """Test harness for secure deployment."""
    
    def __init__(self, api_url: str = "http://localhost:8001"):
        self.api_url = api_url
        self.results = []
        
    async def test_health_check(self) -> bool:
        """Test that services are healthy."""
        print("🏥 Testing health check...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_url}/health")
                if response.status_code == 200:
                    print("✅ API is healthy")
                    return True
                else:
                    print(f"❌ API health check failed: {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ Cannot connect to API: {e}")
            return False
            
    async def test_basic_execution(self) -> bool:
        """Test basic command execution."""
        print("\n🚀 Testing basic execution...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/execute",
                    json={
                        "tasks": ["echo 'Hello from secure container'"],
                        "timeout_per_task": 10
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("results") and result["results"][0]["exit_code"] == 0:
                        print("✅ Basic execution successful")
                        print(f"   Output: {result['results'][0]['stdout'].strip()}")
                        return True
                    else:
                        print(f"❌ Execution failed: {result}")
                        return False
                else:
                    print(f"❌ API request failed: {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ Execution test failed: {e}")
            return False
            
    async def test_resource_limits(self) -> bool:
        """Test that resource limits are enforced."""
        print("\n🛡️ Testing resource limits...")
        
        # Test memory limit (this should fail gracefully)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/execute",
                    json={
                        "tasks": [
                            "python3 -c 'data = \"x\" * (2 * 1024 * 1024 * 1024)'"  # Try to allocate 2GB
                        ],
                        "timeout_per_task": 5
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # Should fail due to memory limit
                    if result["results"][0]["exit_code"] != 0:
                        print("✅ Memory limit enforced")
                        return True
                    else:
                        print("⚠️ Memory limit may not be enforced")
                        return False
                        
        except Exception as e:
            print(f"❌ Resource limit test failed: {e}")
            return False
            
    async def test_filesystem_isolation(self) -> bool:
        """Test filesystem isolation."""
        print("\n🗂️ Testing filesystem isolation...")
        
        tests = [
            # Test 1: Cannot write to root
            {
                "name": "Root filesystem read-only",
                "command": "touch /test_file",
                "should_fail": True
            },
            # Test 2: Can write to workspace
            {
                "name": "Workspace writable",
                "command": "echo 'test' > test.txt && cat test.txt",
                "should_fail": False
            },
            # Test 3: Workspace is cleaned between executions
            {
                "name": "Workspace isolation",
                "command": "ls test.txt",
                "should_fail": True  # Should not see file from previous test
            }
        ]
        
        all_passed = True
        
        for test in tests:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.api_url}/execute",
                        json={
                            "tasks": [test["command"]],
                            "timeout_per_task": 5
                        }
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        exit_code = result["results"][0]["exit_code"]
                        
                        if test["should_fail"] and exit_code != 0:
                            print(f"✅ {test['name']}: Correctly failed")
                        elif not test["should_fail"] and exit_code == 0:
                            print(f"✅ {test['name']}: Correctly succeeded")
                        else:
                            print(f"❌ {test['name']}: Unexpected result (exit_code={exit_code})")
                            all_passed = False
                            
            except Exception as e:
                print(f"❌ {test['name']}: Exception: {e}")
                all_passed = False
                
        return all_passed
        
    async def test_network_isolation(self) -> bool:
        """Test network isolation of worker."""
        print("\n🌐 Testing network isolation...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/execute",
                    json={
                        "tasks": [
                            "curl -s --max-time 5 https://www.google.com || echo 'Network access blocked'"
                        ],
                        "timeout_per_task": 10
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    output = result["results"][0]["stdout"].strip()
                    
                    if "Network access blocked" in output or result["results"][0]["exit_code"] != 0:
                        print("✅ Network isolation working")
                        return True
                    else:
                        print("⚠️ Worker may have network access")
                        return False
                        
        except Exception as e:
            print(f"❌ Network isolation test failed: {e}")
            return False
            
    async def test_timeout_enforcement(self) -> bool:
        """Test that timeouts are enforced."""
        print("\n⏱️ Testing timeout enforcement...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/execute",
                    json={
                        "tasks": ["sleep 30"],
                        "timeout_per_task": 2  # 2 second timeout
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result["results"][0]["exit_code"] == -1:  # Timeout exit code
                        print("✅ Timeout correctly enforced")
                        return True
                    else:
                        print("❌ Timeout not enforced")
                        return False
                        
        except Exception as e:
            print(f"❌ Timeout test failed: {e}")
            return False
            
    async def run_all_tests(self):
        """Run all security tests."""
        print("=" * 60)
        print("🔒 CC Executor Secure Deployment Test Suite")
        print("=" * 60)
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Basic Execution", self.test_basic_execution),
            ("Resource Limits", self.test_resource_limits),
            ("Filesystem Isolation", self.test_filesystem_isolation),
            ("Network Isolation", self.test_network_isolation),
            ("Timeout Enforcement", self.test_timeout_enforcement),
        ]
        
        results = []
        
        for test_name, test_func in tests:
            try:
                passed = await test_func()
                results.append((test_name, passed))
            except Exception as e:
                print(f"❌ {test_name}: Unexpected error: {e}")
                results.append((test_name, False))
                
        # Summary
        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print("=" * 60)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name:.<40} {status}")
            
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 All security tests passed!")
            return 0
        else:
            print(f"\n⚠️ {total - passed} tests failed")
            return 1


async def main():
    """Run the test suite."""
    tester = SecureDeploymentTester()
    return await tester.run_all_tests()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)