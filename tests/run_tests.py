#!/usr/bin/env python3
"""
Simple test runner script for the Camera Control API.
Can be run without pytest for basic testing.
"""

import requests
import json
import time
import sys

# Configuration
API_BASE = "http://localhost:5055"
API_KEY = "dev-secret"

def test_server_health():
    """Test if server is running and healthy"""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("ok") is True
    except:
        pass
    return False

def test_authentication():
    """Test API authentication"""
    # Test without API key
    response = requests.post(f"{API_BASE}/camera/test", json={})
    if response.status_code != 401:
        return False
    
    # Test with wrong API key
    headers = {"x-api-key": "wrong-key", "Content-Type": "application/json"}
    response = requests.post(f"{API_BASE}/camera/test", json={}, headers=headers)
    if response.status_code != 401:
        return False
    
    return True

def test_scan_surroundings():
    """Test scan surroundings endpoint"""
    headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}
    data = {"count": 1}
    
    try:
        response = requests.post(f"{API_BASE}/scan-surroundings", 
                               json=data, headers=headers, timeout=30)
        
        # Should return valid JSON response
        result = response.json()
        
        if response.status_code == 200:
            return "photo_paths" in result.get("data", {})
        else:
            # Check if it's a proper error response
            return "detail" in result or "message" in result
            
    except Exception as e:
        print(f"Error testing scan surroundings: {e}")
        return False

def test_stream_endpoints():
    """Test streaming endpoints"""
    headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}
    
    # Test stream status
    try:
        response = requests.get(f"{API_BASE}/stream/status", headers=headers, timeout=10)
        if response.status_code != 200:
            return False
        
        # Test stream start (may fail due to camera, but should have proper response)
        stream_data = {"width": 640, "height": 480, "framerate": 15}
        response = requests.post(f"{API_BASE}/stream/start", 
                               json=stream_data, headers=headers, timeout=10)
        
        # Should return proper JSON (success or error)
        result = response.json()
        return "success" in result or "detail" in result
        
    except Exception as e:
        print(f"Error testing stream endpoints: {e}")
        return False

def test_capture_endpoint():
    """Test frame capture endpoint"""
    headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}
    data = {"width": 640, "height": 480}
    
    try:
        response = requests.post(f"{API_BASE}/capture", 
                               json=data, headers=headers, timeout=30)
        
        # Should return valid JSON response
        result = response.json()
        
        if response.status_code == 200:
            return "frame_path" in result.get("data", {})
        else:
            # Check if it's a proper error response
            return "detail" in result or "message" in result
            
    except Exception as e:
        print(f"Error testing capture endpoint: {e}")
        return False

def test_validation():
    """Test input validation"""
    headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}
    
    # Test invalid scan count
    response = requests.post(f"{API_BASE}/scan-surroundings", 
                           json={"count": 0}, headers=headers, timeout=10)
    
    return response.status_code == 422  # Validation error

def run_quick_tests():
    """Run a quick test suite"""
    print("🚀 Running Quick API Test Suite")
    print("=" * 50)
    
    tests = [
        ("Server Health", test_server_health),
        ("Authentication", test_authentication),
        ("Scan Surroundings", test_scan_surroundings),
        ("Stream Endpoints", test_stream_endpoints),
        ("Capture Endpoint", test_capture_endpoint),
        ("Input Validation", test_validation),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🧪 Testing {test_name}...")
        try:
            result = test_func()
            results[test_name] = result
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {status}")
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 TEST RESULTS")
    print("=" * 50)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<20} {status}")
    
    print("=" * 50)
    print(f"📊 Summary: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! API is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Check the server logs for details.")
        return False

if __name__ == "__main__":
    success = run_quick_tests()
    sys.exit(0 if success else 1)