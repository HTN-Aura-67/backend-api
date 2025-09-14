#!/usr/bin/env python3
"""
Comprehensive test script for the enhanced camera control system.
This script tests all the new functionality including streaming, recording, and frame capture.
"""

import sys
import time
import os
import pytest
from pathlib import Path

# Add the project root to the path to import camera module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from camera.control import CameraController, quick_stream, quick_capture, quick_record

def test_camera_connection(camera_available, mock_camera_controller):
    """Test basic camera connection"""
    print("🔍 Testing camera connection...")
    
    if not camera_available:
        controller = mock_camera_controller
        print("Using mock controller (no camera hardware)")
    else:
        controller = CameraController()
    
    success = controller.test_camera_connection()
    assert success, "Camera connection failed!"
    print("✅ Camera connection successful!")
    
    # Get camera info
    info = controller.get_camera_info()
    if info.get('connected'):
        print(f"📷 Remote host: {info['remote_host']}")
        print("📋 Camera information:")
        print(info['camera_list'])

def test_frame_capture(camera_available, mock_camera_controller):
    """Test frame capture functionality"""
    print("\n📸 Testing frame capture...")
    
    if not camera_available:
        controller = mock_camera_controller
        print("Using mock controller (no camera hardware)")
    else:
        controller = CameraController()
    
    # Test basic frame capture
    frame_path = controller.capture_frame()
    assert frame_path is not None, "Frame capture returned None"
    print(f"✅ Frame captured successfully: {frame_path}")
    
    # For real hardware, check file exists and has content
    if camera_available:
        assert os.path.exists(frame_path), f"Frame file does not exist: {frame_path}"
        file_size = os.path.getsize(frame_path)
        print(f"   File size: {file_size} bytes")
        assert file_size > 0, "Frame file is empty"

def test_quick_functions(camera_available, mock_quick_functions):
    """Test the convenience functions"""
    print("\n⚡ Testing quick functions...")
    
    # Test quick capture
    print("Testing quick_capture()...")
    if not camera_available:
        # Use mock
        frame_path = mock_quick_functions['capture']()
        print("Using mock quick_capture")
    else:
        frame_path = quick_capture()
    
    assert frame_path is not None, "Quick capture failed - returned None"
    print(f"✅ Quick capture successful: {frame_path}")
    
    # For mocked tests, we don't need to check file existence
    if camera_available:
        assert os.path.exists(frame_path), f"Quick capture file does not exist: {frame_path}"

def test_streaming(camera_available, mock_camera_controller):
    """Test video streaming functionality"""
    print("\n📹 Testing video streaming...")
    
    if not camera_available:
        # Use mock for hardware-unavailable scenarios
        controller = mock_camera_controller
        print("Using mock controller (no camera hardware)")
    else:
        controller = CameraController()
    
    # Start stream
    print("Starting stream...")
    success = controller.start_stream(width=640, height=480, framerate=15)
    
    if not camera_available:
        # For mocked tests, we expect success
        assert success, "Mocked stream start should succeed"
        print("✅ Stream started successfully (mocked)!")
    else:
        # For real hardware tests, handle graceful failure
        if not success:
            pytest.skip("Failed to start stream - likely hardware/port issue")
        print("✅ Stream started successfully!")
        
        # Check stream status
        status = controller.get_stream_status()
        print(f"📊 Stream status: {status}")
        
        if status['streaming'] and status['http_server']:
            print(f"🌐 Stream URL: {status['stream_url']}")
            print("⏱️  Streaming for 5 seconds...")
            time.sleep(5)  # Reduced from 10 seconds
            
            # Test frame capture from stream
            print("📸 Testing frame capture from stream...")
            frames = controller.capture_frames_from_stream(count=1, interval=1)
            if frames:
                print(f"✅ Captured {len(frames)} frames from stream")
                for frame in frames:
                    print(f"   - {frame}")
            else:
                print("❌ Failed to capture frames from stream")
        
        # Stop stream
        print("Stopping stream...")
        controller.stop_stream()
        print("✅ Stream stopped")

def test_recording():
    """Test video recording functionality"""
    print("\n🎬 Testing video recording...")
    controller = CameraController()
    
    # Start recording
    print("Starting 10-second recording...")
    recording_id = controller.start_recording(duration=10)
    
    assert recording_id is not None, "Failed to start recording!"
    print(f"✅ Recording started: {recording_id}")
    
    # Monitor recording progress
    start_time = time.time()
    while time.time() - start_time < 11:  # Give extra time
        status = controller.get_recording_status(recording_id)
        if 'error' in status:
            print(f"❌ Recording error: {status['error']}")
            break
        
        if not status.get('is_active', False):
            print("✅ Recording completed")
            break
        
        progress = status.get('progress_percent', 0)
        remaining = status.get('remaining_time', 0)
        print(f"\r   Progress: {progress:.1f}% - {remaining:.1f}s remaining", end='')
        time.sleep(1)
    
    print()  # New line after progress
    
    # Check if recording file exists
    final_status = controller.get_recording_status(recording_id)
    if 'output_path' in final_status:
        output_path = final_status['output_path']
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✅ Recording saved: {output_path} ({file_size} bytes)")
        else:
            print(f"❌ Recording file not found: {output_path}")
            assert False, f"Recording file not found: {output_path}"
    
    # Cleanup
    controller.cleanup_finished_recordings()

def test_quick_record():
    """Test quick record function"""
    print("\n⚡ Testing quick record function...")
    
    recording_id = quick_record(duration=5)
    assert recording_id is not None, "Quick record failed - returned None"
    print(f"✅ Quick record successful: {recording_id}")

def test_camera_settings(camera_available, mock_camera_controller):
    """Test camera settings functionality"""
    print("\n⚙️  Testing camera settings...")
    
    if not camera_available:
        controller = mock_camera_controller
        print("Using mock controller (no camera hardware)")
    else:
        controller = CameraController()
    
    # Test setting different resolutions
    settings = {
        'width': 1280,
        'height': 720,
        'framerate': 30,
        'bitrate': 3000000
    }
    
    success = controller.set_camera_settings(settings)
    assert success, "Failed to update camera settings"
    print("✅ Camera settings updated successfully")

def test_status_monitoring(camera_available, mock_camera_controller):
    """Test status monitoring functionality"""
    print("\n📊 Testing status monitoring...")
    
    if not camera_available:
        controller = mock_camera_controller
        print("Using mock controller (no camera hardware)")
    else:
        controller = CameraController()
    
    # Get initial status
    stream_status = controller.get_stream_status()
    recording_status = controller.get_recording_status()
    
    print("📋 Initial status:")
    print(f"   Stream active: {stream_status['streaming']}")
    print(f"   HTTP server: {stream_status['http_server']}")
    print(f"   Active recordings: {recording_status['active_recordings']}")
    
    # Basic validation that status dictionaries have expected keys
    assert 'streaming' in stream_status, "Stream status missing 'streaming' key"
    assert 'http_server' in stream_status, "Stream status missing 'http_server' key"  
    assert 'active_recordings' in recording_status, "Recording status missing 'active_recordings' key"
    
    print("✅ Status monitoring working")

def run_comprehensive_test():
    """Run all tests in sequence"""
    print("🚀 Starting comprehensive camera control test suite...")
    print("=" * 60)
    
    tests = [
        ("Camera Connection", test_camera_connection),
        ("Frame Capture", test_frame_capture),
        ("Quick Functions", test_quick_functions),
        ("Video Streaming", test_streaming),
        ("Video Recording", test_recording),
        ("Quick Record", test_quick_record),
        ("Camera Settings", test_camera_settings),
        ("Status Monitoring", test_status_monitoring),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*60)
    print("📋 TEST SUMMARY")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<40} {status}")
        if result:
            passed += 1
    
    print("="*60)
    print(f"📊 Results: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! Camera control system is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the logs above for details.")
    
    return passed == total

def run_quick_test():
    """Run a quick subset of tests for fast validation"""
    print("⚡ Running quick test suite...")
    
    # Test connection first
    if not test_camera_connection():
        print("❌ Camera connection failed. Cannot continue with other tests.")
        return False
    
    # Test basic functionality
    tests = [
        test_frame_capture,
        test_status_monitoring,
        test_camera_settings,
    ]
    
    for i, test_func in enumerate(tests, 1):
        print(f"\n--- Quick Test {i}/{len(tests)} ---")
        if not test_func():
            print(f"❌ Quick test {i} failed!")
            return False
    
    print("\n✅ All quick tests passed!")
    return True

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Test camera control system')
    parser.add_argument('--quick', action='store_true', help='Run quick tests only')
    parser.add_argument('--test', choices=[
        'connection', 'capture', 'stream', 'record', 'settings', 'status'
    ], help='Run specific test')
    
    args = parser.parse_args()
    
    if args.test:
        # Run specific test
        test_functions = {
            'connection': test_camera_connection,
            'capture': test_frame_capture,
            'stream': test_streaming,
            'record': test_recording,
            'settings': test_camera_settings,
            'status': test_status_monitoring,
        }
        
        if args.test in test_functions:
            success = test_functions[args.test]()
            sys.exit(0 if success else 1)
        else:
            print(f"Unknown test: {args.test}")
            sys.exit(1)
    
    elif args.quick:
        # Run quick tests
        success = run_quick_test()
        sys.exit(0 if success else 1)
    
    else:
        # Run comprehensive tests
        success = run_comprehensive_test()
        sys.exit(0 if success else 1)