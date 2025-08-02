#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for RPA Balance Loader API
This script tests the API endpoints to ensure they work correctly.
"""

import json
import requests
import time
import sys
from typing import Dict, Any


def test_health_endpoint(base_url: str) -> bool:
    """Test the health endpoint"""
    try:
        print("Testing health endpoint...")
        response = requests.get(f"{base_url}/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            return True
        else:
            print(f"❌ Health check failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


def test_root_endpoint(base_url: str) -> bool:
    """Test the root endpoint"""
    try:
        print("Testing root endpoint...")
        response = requests.get(f"{base_url}/", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Root endpoint passed: {data['service']}")
            return True
        else:
            print(f"❌ Root endpoint failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")
        return False


def test_create_user_endpoint(base_url: str, test_username: str) -> bool:
    """Test the create user endpoint"""
    try:
        print(f"Testing create user endpoint with username: {test_username}")
        
        # Prepare test request
        test_request = {
            "conversation_id": "test_123",
            "captured_user_name": "Test User",
            "candidate_username": test_username,
            "attempt_number": 1
        }
        
        response = requests.post(
            f"{base_url}/api/create-user",
            json=test_request,
            headers={"Content-Type": "application/json"},
            timeout=30  # User creation can take longer
        )
        
        if response.status_code == 200:
            data = response.json()
            status = data.get("status")
            
            if status == "success":
                print(f"✅ User creation successful: {data.get('generated_username')}")
                print(f"   Message: {data.get('response_message')}")
                return True
            elif status == "conflict":
                print(f"⚠️  Username conflict (expected for existing users): {data.get('error_detail')}")
                return True  # This is also a valid response
            elif status == "error":
                print(f"❌ User creation error: {data.get('error_detail')}")
                return False
            else:
                print(f"❌ Unknown status: {status}")
                return False
        else:
            print(f"❌ Create user failed: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Create user error: {e}")
        return False


def main():
    """Run API tests"""
    print("=" * 60)
    print("RPA Balance Loader API Test Suite")
    print("=" * 60)
    
    # Configuration
    base_url = "http://127.0.0.1:8001"
    test_username = f"testuser{int(time.time())}"  # Unique username
    
    print(f"Base URL: {base_url}")
    print(f"Test username: {test_username}")
    print()
    
    # Check if API server is running
    try:
        response = requests.get(base_url, timeout=2)
        print(f"✅ API server is responding")
    except Exception as e:
        print(f"❌ API server is not accessible: {e}")
        print("\nPlease start the API server first:")
        print("  python run_api.py")
        print("  or")
        print("  sudo systemctl start rpa-api.service")
        sys.exit(1)
    
    print()
    
    # Run tests
    tests = [
        ("Health Endpoint", lambda: test_health_endpoint(base_url)),
        ("Root Endpoint", lambda: test_root_endpoint(base_url)),
        ("Create User Endpoint", lambda: test_create_user_endpoint(base_url, test_username)),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'-' * 40}")
        print(f"Running: {test_name}")
        print(f"{'-' * 40}")
        
        success = test_func()
        results.append((test_name, success))
        
        if success:
            print(f"✅ {test_name}: PASSED")
        else:
            print(f"❌ {test_name}: FAILED")
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "PASSED" if success else "FAILED"
        icon = "✅" if success else "❌"
        print(f"{icon} {test_name}: {status}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! API is working correctly.")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed. Check the API server configuration.")
        sys.exit(1)


if __name__ == "__main__":
    main()