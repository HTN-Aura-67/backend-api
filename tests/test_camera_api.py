#!/usr/bin/env python3
"""
Comprehensive test suite for the FastAPI Camera Control API.
Tests all endpoints, authentication, error handling, and integration scenarios.
"""

import pytest
import requests
import json
import time
import os
from typing import Dict, Any, Optional
from pathlib import Path

# Test configuration
API_BASE = "http://localhost:5056"  # Updated to test server port
API_KEY = "dev-secret"
WRONG_API_KEY = "wrong-key"
HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}
WRONG_HEADERS = {
    "x-api-key": WRONG_API_KEY,
    "Content-Type": "application/json"
}

def _check_server_running() -> bool:
    """Check if the API server is running"""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def _make_request(method: str, endpoint: str, data: Optional[Dict] = None, 
                 headers: Optional[Dict] = None, expect_success: bool = True) -> requests.Response:
    """Helper method to make API requests"""
    url = f"{API_BASE}{endpoint}"
    headers = headers or HEADERS
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        return response
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Request failed for {endpoint}: {e}")

# Health and Info Tests
def test_health_check_no_auth():
    """Test health endpoint without authentication"""
    response = requests.get(f"{API_BASE}/health", timeout=5)
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["status"] == "healthy"
    assert data["service"] == "camera-control-api"
    
    def test_api_info_no_auth(self):
        """Test API info endpoint without authentication"""
        response = requests.get(f"{API_BASE}/api", timeout=5)
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Camera Control API"
        assert data["version"] == "1.0.0"
        assert "endpoints" in data
        assert "hls_stream" in data

class TestAuthentication:
    """Test authentication related endpoints"""
    
    def test_endpoint_requires_auth(self):
        """Test that protected endpoints require authentication"""
        # Test without any headers
        response = requests.post(f"{API_BASE}/camera/test", json={})
        assert response.status_code == 401
        
        # Test with wrong API key
        response = requests.post(f"{API_BASE}/camera/test", json={}, headers=WRONG_HEADERS)
        assert response.status_code == 401
        
        # Test with correct API key (may fail due to camera, but should pass auth)
        response = requests.post(f"{API_BASE}/camera/test", json={}, headers=HEADERS)
        assert response.status_code != 401  # Should not be auth error
    
    def test_auth_error_messages(self):
        """Test authentication error messages"""
        response = requests.post(f"{API_BASE}/camera/test", json={})
        assert response.status_code == 401
        data = response.json()
        assert "Invalid or missing API key" in data["detail"]

class TestCameraEndpoints:
    """Test camera-related endpoints"""
    
    def test_camera_test_endpoint(self):
        """Test camera connection test endpoint"""
        response = _make_request("POST", "/camera/test", {})
        
        # Should return proper JSON structure regardless of camera connection
        assert response.status_code in [200, 500]  # 500 if camera not connected
        data = response.json()
        
        if response.status_code == 200:
            assert data["success"] in [True, False]
            assert "data" in data
            assert "connection" in data["data"]
            assert "camera_info" in data["data"]
        else:
            # Server error due to camera connection issues
            assert "error" in data["detail"].lower() or "camera" in data["detail"].lower()
    
    def test_capture_endpoint_structure(self):
        """Test capture endpoint request/response structure"""
        capture_data = {
            "width": 640,
            "height": 480
        }
        
        response = _make_request("POST", "/capture", capture_data)
        
        # Should return proper structure even if capture fails
        assert response.status_code in [200, 500]
        data = response.json()
        
        if response.status_code == 200:
            assert data["success"] is True
            assert "frame_path" in data["data"]
            assert data["data"]["width"] == 640
            assert data["data"]["height"] == 480
    
    def test_capture_validation(self):
        """Test capture endpoint input validation"""
        # Test with invalid width
        invalid_data = {"width": 99, "height": 480}  # Too small
        response = _make_request("POST", "/capture", invalid_data)
        assert response.status_code == 422  # Validation error
        
        # Test with invalid height
        invalid_data = {"width": 640, "height": 50000}  # Too large
        response = _make_request("POST", "/capture", invalid_data)
        assert response.status_code == 422  # Validation error

class TestScanSurroundings:
    """Test scan surroundings endpoint"""
    
    def test_scan_surroundings_structure(self):
        """Test scan surroundings endpoint structure"""
        scan_data = {"count": 1}  # Minimal test
        
        response = _make_request("POST", "/scan-surroundings", scan_data)
        
        # Should return proper structure
        assert response.status_code in [200, 500]
        data = response.json()
        
        if response.status_code == 200:
            assert data["success"] is True
            assert "photo_paths" in data["data"]
            assert "count" in data["data"]
            assert isinstance(data["data"]["photo_paths"], list)
    
    def test_scan_validation(self):
        """Test scan surroundings input validation"""
        # Test with invalid count (too high)
        invalid_data = {"count": 25}  # Max is 20
        response = _make_request("POST", "/scan-surroundings", invalid_data)
        assert response.status_code == 422
        
        # Test with invalid count (too low)
        invalid_data = {"count": 0}  # Min is 1
        response = _make_request("POST", "/scan-surroundings", invalid_data)
        assert response.status_code == 422
    
    def test_scan_default_values(self):
        """Test scan surroundings with default values"""
        response = _make_request("POST", "/scan-surroundings", {})
        
        # Should accept empty body and use defaults
        assert response.status_code in [200, 500]

class TestStreamEndpoints:
    """Test streaming endpoints"""
    
    def test_stream_status_initial(self):
        """Test initial stream status"""
        response = _make_request("GET", "/stream/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        # Should contain streaming status info
        assert "streaming" in data["data"]
    
    def test_stream_start_validation(self):
        """Test stream start input validation"""
        # Test with invalid framerate
        invalid_data = {"framerate": 100}  # Max is 60
        response = _make_request("POST", "/stream/start", invalid_data)
        assert response.status_code == 422
        
        # Test with invalid bitrate
        invalid_data = {"bitrate": 100}  # Too low
        response = _make_request("POST", "/stream/start", invalid_data)
        assert response.status_code == 422
    
    def test_stream_start_structure(self):
        """Test stream start endpoint structure"""
        stream_data = {
            "width": 640,
            "height": 480,
            "framerate": 15,
            "bitrate": 2000000
        }
        
        response = _make_request("POST", "/stream/start", stream_data)
        
        # Should return proper structure
        assert response.status_code in [200, 500]
        data = response.json()
        
        if response.status_code == 200:
            assert data["success"] is True
            assert "data" in data
    
    def test_stream_stop(self):
        """Test stream stop endpoint"""
        response = _make_request("POST", "/stream/stop")
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data

class TestRecordingEndpoints:
    """Test recording endpoints"""
    
    def test_recording_status_initial(self):
        """Test initial recording status"""
        response = _make_request("GET", "/record/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
    
    def test_recording_start_validation(self):
        """Test recording start input validation"""
        # Test with invalid duration
        invalid_data = {"duration": 0}  # Min is 1
        response = _make_request("POST", "/record/start", invalid_data)
        assert response.status_code == 422
        
        # Test with duration too long
        invalid_data = {"duration": 4000}  # Max is 3600
        response = _make_request("POST", "/record/start", invalid_data)
        assert response.status_code == 422
    
    def test_recording_start_structure(self):
        """Test recording start endpoint structure"""
        record_data = {
            "duration": 5,  # Short test
            "width": 640,
            "height": 480
        }
        
        response = _make_request("POST", "/record/start", record_data)
        
        # Should return proper structure
        assert response.status_code in [200, 500]
        data = response.json()
        
        if response.status_code == 200:
            assert data["success"] is True
            assert "recording_id" in data["data"]
    
    def test_recording_stop_invalid_id(self):
        """Test stopping non-existent recording"""
        stop_data = {"recording_id": "invalid_id"}
        response = _make_request("POST", "/record/stop", stop_data)
        
        assert response.status_code == 404  # Not found

class TestCleanupEndpoint:
    """Test cleanup endpoint"""
    
    def test_cleanup_structure(self):
        """Test cleanup endpoint structure"""
        response = _make_request("POST", "/cleanup")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cleaned_recordings" in data["data"]
        assert isinstance(data["data"]["cleaned_recordings"], int)

class TestHLSEndpoints:
    """Test HLS streaming file endpoints"""
    
    def test_hls_playlist_not_found(self):
        """Test HLS playlist when stream not running"""
        response = requests.get(f"{API_BASE}/stream.m3u8")
        
        # Should return 404 if no stream is active
        assert response.status_code == 404
    
    def test_hls_segment_not_found(self):
        """Test HLS segment when not available"""
        response = requests.get(f"{API_BASE}/stream_001.ts")
        
        # Should return 404 if segment doesn't exist
        assert response.status_code == 404

class TestCORSAndSecurity:
    """Test CORS and security features"""
    
    def test_cors_headers(self):
        """Test CORS configuration"""
        # Send preflight request
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-api-key,content-type"
        }
        
        response = requests.options(f"{API_BASE}/camera/test", headers=headers)
        
        # Should handle CORS properly
        assert response.status_code in [200, 204]
        
        # Check for CORS headers
        cors_headers = response.headers
        assert "Access-Control-Allow-Origin" in cors_headers or "access-control-allow-origin" in cors_headers

class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_invalid_json(self):
        """Test invalid JSON in request body"""
        headers = {**HEADERS, "Content-Type": "application/json"}
        
        # Send malformed JSON
        response = requests.post(
            f"{API_BASE}/capture", 
            data='{"invalid": json}',  # Malformed JSON
            headers=headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_missing_content_type(self):
        """Test request without content-type header"""
        headers = {"x-api-key": API_KEY}  # No content-type
        
        response = requests.post(
            f"{API_BASE}/capture",
            json={"width": 640},
            headers=headers
        )
        
        # Should still work (FastAPI is flexible)
        assert response.status_code in [200, 422, 500]
    
    def test_nonexistent_endpoint(self):
        """Test accessing non-existent endpoint"""
        response = requests.get(f"{API_BASE}/nonexistent", headers=HEADERS)
        assert response.status_code == 404

# Integration test scenarios
class TestIntegrationScenarios:
    """Test complete workflow scenarios"""
    
    def test_basic_workflow(self):
        """Test a basic camera workflow"""
        # 1. Check camera status
        response = _make_request("POST", "/camera/test")
        assert response.status_code in [200, 500]
        
        # 2. Check stream status
        response = _make_request("GET", "/stream/status")
        assert response.status_code == 200
        
        # 3. Try to capture a frame
        response = _make_request("POST", "/capture", {"width": 640, "height": 480})
        assert response.status_code in [200, 500]
        
        # 4. Cleanup
        response = _make_request("POST", "/cleanup")
        assert response.status_code == 200

# Custom test runner for standalone execution
def run_tests():
    """Run tests without pytest (for standalone execution)"""
    import sys
    
    print("🧪 Running Camera Control API Tests")
    print("=" * 60)
    
    # Check if server is running
    if not _check_server_running():
        print("❌ Server is not running!")
        print("Please start the server first:")
        print("BACKEND_API_KEY=dev-secret uvicorn router.server:app --host 0.0.0.0 --port 5056 --reload")
        return False
    
    print("✅ Server is running, starting tests...")
    
    # Run test classes manually
    test_classes = [
        TestHealthAndInfo,
        TestAuthentication,
        TestCameraEndpoints,
        TestScanSurroundings,
        TestStreamEndpoints,
        TestRecordingEndpoints,
        TestCleanupEndpoint,
        TestHLSEndpoints,
        TestCORSAndSecurity,
        TestErrorHandling,
        TestIntegrationScenarios
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        print(f"\n--- {test_class.__name__} ---")
        instance = test_class()
        instance.setup_class()
        
        # Get all test methods
        test_methods = [method for method in dir(instance) if method.startswith('test_')]
        
        for test_method in test_methods:
            total_tests += 1
            try:
                method = getattr(instance, test_method)
                method()
                print(f"  ✅ {test_method}")
                passed_tests += 1
            except Exception as e:
                print(f"  ❌ {test_method}: {str(e)}")
    
    # Summary
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed_tests}/{total_tests} passed ({(passed_tests/total_tests)*100:.1f}%)")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️ Some tests failed. Check the output above.")
        return False

if __name__ == "__main__":
    # Run tests standalone
    success = run_tests()
    exit(0 if success else 1)