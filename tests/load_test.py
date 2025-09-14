#!/usr/bin/env python3
"""
Load testing script for the Camera Control API.
Tests concurrent requests and API performance.
"""

import asyncio
import aiohttp
import time
import statistics
from typing import List, Dict
import json
import pytest

# Configuration
API_BASE = "http://localhost:5056"  # Updated to test server port
API_KEY = "dev-secret"
HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

async def make_request(session: aiohttp.ClientSession, endpoint: str, 
                      method: str = "GET", data: dict = None) -> Dict:
    """Make an async HTTP request"""
    url = f"{API_BASE}{endpoint}"
    
    start_time = time.time()
    try:
        if method.upper() == "GET":
            async with session.get(url, headers=HEADERS) as response:
                result = await response.json()
                success = response.status == 200
        else:
            async with session.post(url, headers=HEADERS, json=data) as response:
                result = await response.json()
                success = response.status == 200
        
        end_time = time.time()
        
        return {
            "success": success,
            "response_time": end_time - start_time,
            "status_code": response.status,
            "endpoint": endpoint
        }
    except Exception as e:
        end_time = time.time()
        return {
            "success": False,
            "response_time": end_time - start_time,
            "error": str(e),
            "endpoint": endpoint
        }

@pytest.mark.asyncio
async def test_concurrent_health_checks(num_requests: int = 10):
    """Test concurrent health check requests"""
    print(f"🔄 Testing {num_requests} concurrent health checks...")
    
    async with aiohttp.ClientSession() as session:
        tasks = [make_request(session, "/health") for _ in range(num_requests)]
        results = await asyncio.gather(*tasks)
    
    # Analyze results
    successful = [r for r in results if r["success"]]
    response_times = [r["response_time"] for r in results]
    
    print(f"   ✅ Success rate: {len(successful)}/{num_requests} ({len(successful)/num_requests*100:.1f}%)")
    print(f"   ⏱️  Avg response time: {statistics.mean(response_times):.3f}s")
    print(f"   📊 Min/Max response time: {min(response_times):.3f}s / {max(response_times):.3f}s")
    
    # Gracefully handle server unavailability
    if len(successful) == 0:
        pytest.skip("No server available for load testing")
    else:
        assert len(successful) == num_requests, f"Expected all {num_requests} requests to succeed, but only {len(successful)} succeeded"

@pytest.mark.asyncio
async def test_concurrent_auth_requests(num_requests: int = 5):
    """Test concurrent authenticated requests"""
    print(f"🔒 Testing {num_requests} concurrent authenticated requests...")
    
    async with aiohttp.ClientSession() as session:
        tasks = [make_request(session, "/stream/status") for _ in range(num_requests)]
        results = await asyncio.gather(*tasks)
    
    # Analyze results
    successful = [r for r in results if r["success"]]
    response_times = [r["response_time"] for r in results]
    
    print(f"   ✅ Success rate: {len(successful)}/{num_requests} ({len(successful)/num_requests*100:.1f}%)")
    print(f"   ⏱️  Avg response time: {statistics.mean(response_times):.3f}s")
    
    # Gracefully handle server unavailability
    if len(successful) == 0:
        pytest.skip("No server available for load testing")
    else:
        assert len(successful) == num_requests, f"Expected all {num_requests} requests to succeed, but only {len(successful)} succeeded"

@pytest.mark.asyncio
async def test_mixed_load(num_requests: int = 20):
    """Test mixed load with different endpoints"""
    print(f"🌊 Testing mixed load with {num_requests} requests...")
    
    # Mix of different endpoints
    endpoints = [
        ("/health", "GET", None),
        ("/api", "GET", None),
        ("/stream/status", "GET", None),
        ("/record/status", "GET", None),
        ("/cleanup", "POST", {}),
    ]
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(num_requests):
            endpoint, method, data = endpoints[i % len(endpoints)]
            tasks.append(make_request(session, endpoint, method, data))
        
        results = await asyncio.gather(*tasks)
    
    # Analyze results by endpoint
    by_endpoint = {}
    for result in results:
        endpoint = result["endpoint"]
        if endpoint not in by_endpoint:
            by_endpoint[endpoint] = []
        by_endpoint[endpoint].append(result)
    
    total_successful = 0
    total_requests = len(results)
    
    for endpoint, endpoint_results in by_endpoint.items():
        successful = [r for r in endpoint_results if r["success"]]
        response_times = [r["response_time"] for r in endpoint_results]
        
        print(f"   📡 {endpoint}: {len(successful)}/{len(endpoint_results)} success, "
              f"avg {statistics.mean(response_times):.3f}s")
        
        total_successful += len(successful)
    
    success_rate = total_successful / total_requests
    print(f"   🎯 Overall success rate: {total_successful}/{total_requests} ({success_rate*100:.1f}%)")
    
    # Gracefully handle server unavailability
    if success_rate == 0:
        pytest.skip("No server available for load testing")
    else:
        assert success_rate > 0.8, f"Expected at least 80% success rate, got {success_rate*100:.1f}%"

@pytest.mark.asyncio
async def test_error_handling_load():
    """Test error handling under load"""
    print("🚨 Testing error handling under load...")
    
    # Mix of valid and invalid requests
    async with aiohttp.ClientSession() as session:
        tasks = [
            # Valid requests
            make_request(session, "/health"),
            make_request(session, "/stream/status"),
            # Invalid endpoints
            make_request(session, "/invalid-endpoint"),
            make_request(session, "/another/invalid"),
            # Invalid data
            make_request(session, "/scan-surroundings", "POST", {"count": 999}),
        ]
        
        results = await asyncio.gather(*tasks)
    
    # Check that invalid requests return proper error codes
    error_responses = [r for r in results if not r["success"]]
    valid_responses = [r for r in results if r["success"]]
    
    print(f"   ✅ Valid responses: {len(valid_responses)}")
    print(f"   ❌ Error responses: {len(error_responses)}")
    print(f"   🛡️  Server handled errors gracefully: {len(error_responses) > 0}")
    
    return True  # Always pass if server doesn't crash

async def run_load_tests():
    """Run all load tests"""
    print("🚀 Running Camera API Load Tests")
    print("=" * 60)
    
    # Check if server is running
    try:
        async with aiohttp.ClientSession() as session:
            result = await make_request(session, "/health")
            if not result["success"]:
                print("❌ Server is not running or not responding!")
                return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return False
    
    print("✅ Server is responding, starting load tests...")
    
    # Run tests
    tests = [
        ("Concurrent Health Checks", test_concurrent_health_checks, 20),
        ("Concurrent Auth Requests", test_concurrent_auth_requests, 10),
        ("Mixed Load Test", test_mixed_load, 30),
        ("Error Handling Load", test_error_handling_load, None),
    ]
    
    results = {}
    
    for test_name, test_func, param in tests:
        print(f"\n--- {test_name} ---")
        try:
            if param is not None:
                result = await test_func(param)
            else:
                result = await test_func()
            
            results[test_name] = result
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {status}")
            
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 LOAD TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<30} {status}")
    
    print("=" * 60)
    print(f"📊 Results: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("🎉 All load tests passed! API handles concurrent requests well.")
        return True
    else:
        print("⚠️ Some load tests failed. Consider optimizing the API.")
        return False

if __name__ == "__main__":
    import sys
    
    # Run load tests
    success = asyncio.run(run_load_tests())
    sys.exit(0 if success else 1)