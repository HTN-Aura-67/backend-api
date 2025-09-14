#!/usr/bin/env python3
"""
pytest configuration and fixtures for the test suite.
"""

import pytest
import os
import sys
import requests
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from camera.control import CameraController

# Test configuration
API_BASE = "http://localhost:5056"  # Updated to test server port
CAMERA_AVAILABLE = None  # Will be determined at runtime

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "camera_hardware: mark test as requiring camera hardware")
    config.addinivalue_line("markers", "server_required: mark test as requiring running server")

@pytest.fixture(scope="session")
def camera_available():
    """Check if camera hardware is available."""
    global CAMERA_AVAILABLE
    if CAMERA_AVAILABLE is None:
        try:
            controller = CameraController()
            CAMERA_AVAILABLE = controller.test_camera_connection()
        except Exception:
            CAMERA_AVAILABLE = False
    return CAMERA_AVAILABLE

@pytest.fixture(scope="session") 
def server_running():
    """Check if the API server is running."""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=2)
        return response.status_code == 200
    except:
        return False

@pytest.fixture(scope="session")
def test_server():
    """Start a test server if one isn't already running."""
    import threading
    import subprocess
    import time
    
    # Check if server is already running
    try:
        response = requests.get(f"{API_BASE}/health", timeout=2)
        if response.status_code == 200:
            print("✓ Server already running")
            yield True
            return
    except:
        pass
    
    print("🚀 Starting test server...")
    
    # Start server in background
    server_process = None
    try:
        # Set environment variable for testing
        env = os.environ.copy()
        env['BACKEND_API_KEY'] = 'dev-secret'
        
        server_process = subprocess.Popen([
            sys.executable, '-m', 'uvicorn', 'router.server:app',
            '--host', '0.0.0.0', '--port', '5055'
        ], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Wait for server to start
        for i in range(30):  # Wait up to 30 seconds
            try:
                response = requests.get(f"{API_BASE}/health", timeout=1)
                if response.status_code == 200:
                    print("✓ Test server started")
                    yield True
                    break
            except:
                time.sleep(1)
        else:
            print("✗ Failed to start test server")
            yield False
            
    finally:
        if server_process:
            print("🛑 Stopping test server...")
            server_process.terminate()
            server_process.wait(timeout=5)

@pytest.fixture
def mock_camera_controller():
    """Mock CameraController for tests without hardware."""
    with patch('camera.control.CameraController') as mock:
        controller = Mock()
        
        # Mock successful operations
        controller.test_camera_connection.return_value = True
        controller.get_camera_info.return_value = {
            'connected': True,
            'remote_host': 'mock-host',
            'camera_list': 'Mock Camera [0]'
        }
        controller.capture_frame.return_value = '/tmp/mock_frame.jpg'
        controller.set_camera_settings.return_value = True
        controller.get_stream_status.return_value = {
            'streaming': False,
            'http_server': False,
            'stream_url': None
        }
        controller.get_recording_status.return_value = {
            'active_recordings': 0
        }
        controller.start_stream.return_value = True
        controller.stop_stream.return_value = True
        controller.start_recording.return_value = 'mock_recording_123'
        controller.cleanup_finished_recordings.return_value = True
        
        mock.return_value = controller
        yield controller

@pytest.fixture
def mock_quick_functions():
    """Mock quick functions for tests without hardware."""
    with patch('camera.control.quick_capture') as mock_capture, \
         patch('camera.control.quick_record') as mock_record:
        
        mock_capture.return_value = '/tmp/mock_quick_frame.jpg'
        mock_record.return_value = 'mock_quick_recording_456'
        
        yield {
            'capture': mock_capture,
            'record': mock_record
        }

def pytest_runtest_setup(item):
    """Skip tests based on markers and availability."""
    # Skip camera hardware tests if no camera available
    camera_hardware_marker = item.get_closest_marker("camera_hardware")
    if camera_hardware_marker:
        try:
            controller = CameraController()
            if not controller.test_camera_connection():
                pytest.skip("Camera hardware not available")
        except Exception:
            pytest.skip("Camera hardware not available")
    
    # Skip server tests if server not running
    server_required_marker = item.get_closest_marker("server_required")
    if server_required_marker:
        try:
            response = requests.get(f"{API_BASE}/health", timeout=2)
            if response.status_code != 200:
                pytest.skip(f"Server not running at {API_BASE}")
        except:
            pytest.skip(f"Server not running at {API_BASE}")