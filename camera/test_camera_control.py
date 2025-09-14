#!/usr/bin/env python3
"""
Comprehensive test script for the enhanced camera control system.
This script tests all the new functionality including streaming, recording, and frame capture.
"""

import sys
import time
import os
from pathlib import Path

# Add the current directory to the path to import control
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from control import CameraController, quick_stream, quick_capture, quick_record

def test_camera_connection():
    """Test basic camera connection"""
    print("🔍 Testing camera connection...")
    controller = CameraController()
    
    success = controller.test_camera_connection()
    if success:
        print("✅ Camera connection successful!")
        
        # Get camera info
        info = controller.get_camera_info()
        if info.get('connected'):
            print(f"📷 Remote host: {info['remote_host']}")
            print("📋 Camera information:")
            print(info['camera_list'])
        
        return True
    else:
        print("❌ Camera connection failed!")
        return False

def test_frame_capture():
    """Test frame capture functionality"""
    print("\n📸 Testing frame capture...")
    controller = CameraController()
    
    # Test basic frame capture
    frame_path = controller.capture_frame()
    if frame_path and os.path.exists(frame_path):
        print(f"✅ Frame captured successfully: {frame_path}")
        file_size = os.path.getsize(frame_path)
        print(f"   File size: {file_size} bytes")
        return True
    else:
        print("❌ Frame capture failed!")
        return False

def test_quick_functions():
    """Test the convenience functions"""
    print("\n⚡ Testing quick functions...")
    
    # Test quick capture
    print("Testing quick_capture()...")
    frame_path = quick_capture()
    if frame_path:
        print(f"✅ Quick capture successful: {frame_path}")
    else:
        print("❌ Quick capture failed!")
        return False
    
    return True

def test_streaming():
    """Test video streaming functionality"""
    print("\n📹 Testing video streaming...")
    controller = CameraController()
    
    # Start stream
    print("Starting stream...")
    success = controller.start_stream(width=640, height=480, framerate=15)
    
    if not success:
        print("❌ Failed to start stream!")
        return False
    
    print("✅ Stream started successfully!")
    
    # Check stream status
    status = controller.get_stream_status()
    print(f"📊 Stream status: {status}")
    
    if status['streaming'] and status['http_server']:
        print(f"🌐 Stream URL: {status['stream_url']}")
        print("⏱️  Streaming for 10 seconds...")
        time.sleep(10)
        
        # Test frame capture from stream
        print("📸 Testing frame capture from stream...")
        frames = controller.capture_frames_from_stream(count=2, interval=2)
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
    
    return True

def test_recording():
    """Test video recording functionality"""
    print("\n🎬 Testing video recording...")
    controller = CameraController()
    
    # Start recording
    print("Starting 10-second recording...")
    recording_id = controller.start_recording(duration=10)
    
    if not recording_id:
        print("❌ Failed to start recording!")
        return False
    
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
            return False
    
    # Cleanup
    controller.cleanup_finished_recordings()
    
    return True

def test_quick_record():
    """Test quick record function"""
    print("\n⚡ Testing quick record function...")
    
    recording_id = quick_record(duration=5)
    if recording_id:
        print(f"✅ Quick record successful: {recording_id}")
        return True
    else:
        print("❌ Quick record failed!")
        return False

def test_camera_settings():
    """Test camera settings functionality"""
    print("\n⚙️  Testing camera settings...")
    controller = CameraController()
    
    # Test setting different resolutions
    settings = {
        'width': 1280,
        'height': 720,
        'framerate': 30,
        'bitrate': 3000000
    }
    
    success = controller.set_camera_settings(settings)
    if success:
        print("✅ Camera settings updated successfully")
        return True
    else:
        print("❌ Failed to update camera settings")
        return False

def test_status_monitoring():
    """Test status monitoring functionality"""
    print("\n📊 Testing status monitoring...")
    controller = CameraController()
    
    # Get initial status
    stream_status = controller.get_stream_status()
    recording_status = controller.get_recording_status()
    
    print("📋 Initial status:")
    print(f"   Stream active: {stream_status['streaming']}")
    print(f"   HTTP server: {stream_status['http_server']}")
    print(f"   Active recordings: {recording_status['active_recordings']}")
    
    print("✅ Status monitoring working")
    return True

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