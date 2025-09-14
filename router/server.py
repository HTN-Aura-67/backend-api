"""
FastAPI server that wraps the CameraController functionality.
Provides REST API endpoints for camera operations including streaming, recording, and frame capture.
"""

import os
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Import our camera controller
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from camera.control import CameraController, take_photos

# Load environment variables
load_dotenv()

# Configuration
BACKEND_API_KEY = os.getenv("BACKEND_API_KEY", "dev-secret")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
HLS_OUTPUT_DIR = "./hls_out"

# Initialize FastAPI app
app = FastAPI(
    title="Camera Control API",
    description="REST API for camera streaming, recording, and frame capture",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "x-api-key", "Content-Type"],
)

# Create HLS output directory if it doesn't exist
Path(HLS_OUTPUT_DIR).mkdir(exist_ok=True)

# Global camera controller instance
camera_controller = CameraController()

# Pydantic models for request/response
class ScanSurroundingsRequest(BaseModel):
    count: int = Field(default=5, ge=1, le=20, description="Number of photos to take")

class StreamStartRequest(BaseModel):
    width: int = Field(default=640, ge=320, le=1920)
    height: int = Field(default=480, ge=240, le=1080)
    framerate: int = Field(default=15, ge=5, le=60)
    bitrate: int = Field(default=2000000, ge=500000, le=10000000)
    segment_duration: float = Field(default=0.5, ge=0.1, le=5.0, alias="segmentDuration")
    playlist_size: int = Field(default=6, ge=3, le=20, alias="playlistSize")

class CaptureRequest(BaseModel):
    width: Optional[int] = Field(default=640, ge=320, le=1920)
    height: Optional[int] = Field(default=480, ge=240, le=1080)

class RecordStartRequest(BaseModel):
    duration: int = Field(ge=1, le=3600, description="Recording duration in seconds")
    width: int = Field(default=640, ge=320, le=1920)
    height: int = Field(default=480, ge=240, le=1080)
    framerate: int = Field(default=15, ge=5, le=60)
    bitrate: int = Field(default=2000000, ge=500000, le=10000000)

class RecordStopRequest(BaseModel):
    recording_id: str = Field(description="ID of the recording to stop")

class ApiResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

# Authentication dependency
async def verify_api_key(request: Request):
    """Verify the x-api-key header"""
    api_key = request.headers.get("x-api-key")
    if not api_key or api_key != BACKEND_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True

# Exception handler
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": f"Internal server error: {str(exc)}"}
    )

# Health check endpoint (no auth required)
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"ok": True, "status": "healthy", "service": "camera-control-api"}

# Camera endpoints (all require authentication)
@app.post("/scan-surroundings", dependencies=[Depends(verify_api_key)])
async def scan_surroundings(request: ScanSurroundingsRequest) -> ApiResponse:
    """
    Scan surroundings by taking multiple photos
    Returns list of file paths where photos were saved
    """
    try:
        # Use the legacy take_photos function which now uses remote camera
        photo_paths = take_photos(count=request.count, save_dir="/tmp/scan_photos")
        
        return ApiResponse(
            success=True,
            data={
                "photo_paths": photo_paths,
                "count": len(photo_paths)
            },
            message=f"Successfully captured {len(photo_paths)} photos"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scan surroundings: {str(e)}")

@app.post("/stream/start", dependencies=[Depends(verify_api_key)])
async def start_stream(request: StreamStartRequest) -> ApiResponse:
    """Start video streaming with specified parameters"""
    try:
        success = camera_controller.start_stream(
            width=request.width,
            height=request.height,
            framerate=request.framerate,
            bitrate=request.bitrate,
            segment_duration=request.segment_duration,
            playlist_size=request.playlist_size
        )
        
        if success:
            status = camera_controller.get_stream_status()
            return ApiResponse(
                success=True,
                data=status,
                message="Stream started successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to start stream")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting stream: {str(e)}")

@app.post("/stream/stop", dependencies=[Depends(verify_api_key)])
async def stop_stream() -> ApiResponse:
    """Stop the current video stream"""
    try:
        success = camera_controller.stop_stream()
        
        return ApiResponse(
            success=success,
            message="Stream stopped successfully" if success else "Failed to stop stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping stream: {str(e)}")

@app.get("/stream/status", dependencies=[Depends(verify_api_key)])
async def get_stream_status() -> ApiResponse:
    """Get current stream status"""
    try:
        status = camera_controller.get_stream_status()
        return ApiResponse(
            success=True,
            data=status
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stream status: {str(e)}")

@app.post("/capture", dependencies=[Depends(verify_api_key)])
async def capture_frame(request: CaptureRequest) -> ApiResponse:
    """Capture a single frame from the camera"""
    try:
        frame_path = camera_controller.capture_frame(
            width=request.width,
            height=request.height
        )
        
        if frame_path:
            return ApiResponse(
                success=True,
                data={
                    "frame_path": frame_path,
                    "width": request.width,
                    "height": request.height
                },
                message="Frame captured successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to capture frame")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error capturing frame: {str(e)}")

@app.post("/record/start", dependencies=[Depends(verify_api_key)])
async def start_recording(request: RecordStartRequest) -> ApiResponse:
    """Start video recording with specified parameters"""
    try:
        recording_id = camera_controller.start_recording(
            duration=request.duration,
            width=request.width,
            height=request.height,
            framerate=request.framerate,
            bitrate=request.bitrate
        )
        
        if recording_id:
            # Get initial recording status
            status = camera_controller.get_recording_status(recording_id)
            
            return ApiResponse(
                success=True,
                data={
                    "recording_id": recording_id,
                    "status": status
                },
                message="Recording started successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to start recording")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting recording: {str(e)}")

@app.post("/record/stop", dependencies=[Depends(verify_api_key)])
async def stop_recording(request: RecordStopRequest) -> ApiResponse:
    """Stop a specific recording"""
    try:
        success = camera_controller.stop_recording(request.recording_id)
        
        if success:
            return ApiResponse(
                success=True,
                data={"recording_id": request.recording_id},
                message="Recording stopped successfully"
            )
        else:
            raise HTTPException(status_code=404, detail="Recording not found or already stopped")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping recording: {str(e)}")

@app.get("/record/status", dependencies=[Depends(verify_api_key)])
async def get_recording_status(recording_id: Optional[str] = None) -> ApiResponse:
    """Get status of recordings (all recordings if recording_id not specified)"""
    try:
        status = camera_controller.get_recording_status(recording_id)
        
        return ApiResponse(
            success=True,
            data=status
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting recording status: {str(e)}")

@app.post("/camera/test", dependencies=[Depends(verify_api_key)])
async def test_camera() -> ApiResponse:
    """Test camera connection and capabilities"""
    try:
        connection_ok = camera_controller.test_camera_connection()
        camera_info = camera_controller.get_camera_info()
        
        return ApiResponse(
            success=connection_ok,
            data={
                "connection": connection_ok,
                "camera_info": camera_info
            },
            message="Camera test completed"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing camera: {str(e)}")

@app.post("/cleanup", dependencies=[Depends(verify_api_key)])
async def cleanup_resources() -> ApiResponse:
    """Cleanup finished recordings and temporary files"""
    try:
        cleaned_count = camera_controller.cleanup_finished_recordings()
        
        return ApiResponse(
            success=True,
            data={"cleaned_recordings": cleaned_count},
            message=f"Cleaned up {cleaned_count} finished recordings"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during cleanup: {str(e)}")

# HLS stream endpoints (no auth required for video playback)
@app.get("/stream.m3u8")
async def get_hls_playlist():
    """Get HLS playlist file"""
    playlist_path = Path(HLS_OUTPUT_DIR) / "stream.m3u8"
    if playlist_path.exists():
        return FileResponse(playlist_path, media_type="application/vnd.apple.mpegurl")
    else:
        raise HTTPException(status_code=404, detail="Stream not found")

@app.get("/stream_{segment:path}.ts")
async def get_hls_segment(segment: str):
    """Get HLS video segment"""
    segment_path = Path(HLS_OUTPUT_DIR) / f"stream_{segment}.ts"
    if segment_path.exists():
        return FileResponse(segment_path, media_type="video/mp2t")
    else:
        raise HTTPException(status_code=404, detail="Segment not found")

# Root endpoint redirect to health
@app.get("/api")
async def api_info():
    """API information endpoint"""
    return {
        "service": "Camera Control API",
        "version": "1.0.0",
        "endpoints": {
            "health": "GET /health",
            "scan": "POST /scan-surroundings",
            "stream": {
                "start": "POST /stream/start",
                "stop": "POST /stream/stop", 
                "status": "GET /stream/status"
            },
            "capture": "POST /capture",
            "record": {
                "start": "POST /record/start",
                "stop": "POST /record/stop",
                "status": "GET /record/status"
            },
            "camera": "POST /camera/test",
            "cleanup": "POST /cleanup"
        },
        "hls_stream": "/stream.m3u8",
        "auth": "x-api-key header required"
    }

# Mount static files for HLS streaming AFTER all API routes
app.mount("/hls", StaticFiles(directory=HLS_OUTPUT_DIR), name="hls")

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or default to 5055
    port = int(os.getenv("PORT", 5055))
    
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )