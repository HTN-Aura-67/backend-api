# Camera Control System - Testing Guide

Your enhanced `control.py` now includes comprehensive tools for video streaming, recording, and frame capture based on your `stream-lhs.sh` script. Here's how to test everything:

## Prerequisites

1. **SSH Access**: Ensure you can SSH to your remote camera without password:
   ```bash
   ssh aura67@100.97.205.28
   ```

2. **Dependencies**: Make sure you have the required tools:
   ```bash
   # On your local machine
   brew install ffmpeg  # macOS
   pip install requests
   
   # On your remote camera (Raspberry Pi)
   # libcamera should already be installed
   ```

## Quick Testing

### 1. Test Camera Connection
```bash
cd /Users/jiucheng/Dev/HTN25/backend-api/camera
python control.py test
```

### 2. Capture a Single Frame
```bash
python control.py capture
# Or with custom resolution
python control.py capture --width 1280 --height 720
```

### 3. Start Video Stream
```bash
python control.py stream --duration 60
# View at: http://localhost:8000/stream.m3u8
```

### 4. Record Video
```bash
python control.py record --duration 30 --output /tmp/my_video.mp4
```

### 5. Check Status
```bash
python control.py status
```

### 6. Stop Everything
```bash
python control.py stop
```

## Programmatic Usage

```python
from camera.control import CameraController

# Initialize controller
controller = CameraController()

# Test connection
if controller.test_camera_connection():
    print("Camera ready!")
    
    # Capture frame for analysis
    frame_path = controller.capture_frame_for_analysis()
    
    # Start streaming
    controller.start_stream(width=640, height=480, framerate=15)
    
    # Capture frames from stream
    frames = controller.capture_frames_from_stream(count=3, interval=2)
    
    # Start recording
    recording_id = controller.start_recording(duration=10)
    
    # Monitor recording
    status = controller.get_recording_status(recording_id)
    print(f"Recording progress: {status['progress_percent']:.1f}%")
    
    # Stop everything
    controller.stop_stream()
```

## Comprehensive Testing

Run the full test suite:
```bash
cd /Users/jiucheng/Dev/HTN25/backend-api/camera
python test_camera_control.py
```

Run quick tests:
```bash
python test_camera_control.py --quick
```

Run specific tests:
```bash
python test_camera_control.py --test connection
python test_camera_control.py --test capture
python test_camera_control.py --test stream
python test_camera_control.py --test record
```

## Key Features Added

### 🎥 **Video Streaming**
- Start/stop HLS video streams
- Automatic HTTP server for stream serving
- Real-time stream status monitoring
- Custom resolution, framerate, and bitrate

### 📸 **Frame Capture**
- Capture individual frames directly from camera
- Capture frames from running video stream
- Optimized capture for object detection analysis
- Multiple frame capture with intervals

### 🎬 **Video Recording**
- Start/stop video recordings with custom duration
- Multiple concurrent recordings support
- Real-time recording progress monitoring
- Automatic cleanup of finished recordings

### ⚙️ **Camera Control**
- Remote camera connection testing
- Camera capability information
- Dynamic settings adjustment
- Status monitoring for all operations

### 🛠️ **Integration Ready**
- Compatible with your existing MCP server
- Frame capture optimized for Detic object detection
- Easy integration with visual analysis pipeline
- Backward compatible with legacy photo functions

## Next Steps

1. **Test Basic Functionality**: Start with `python control.py test`
2. **Try Streaming**: Use `python control.py stream --duration 30`
3. **Capture Frames**: Use `python control.py capture`
4. **Run Full Tests**: Use `python test_camera_control.py`
5. **Integrate with MCP**: Use the captured frames with your object detection pipeline

## Troubleshooting

- **SSH Connection Issues**: Check your SSH key setup and network connectivity
- **FFmpeg Errors**: Ensure FFmpeg is installed and accessible
- **Port 8000 Busy**: The HTTP server uses port 8000, make sure it's available
- **Permission Errors**: Check write permissions for `/tmp/` directory

The system is now ready for comprehensive testing! Start with the connection test and work your way through the features.