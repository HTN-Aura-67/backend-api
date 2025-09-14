import os
import requests
import subprocess
import signal
import threading
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple

# Configuration
SERVER_URL = 'http://your-server-address/upload'
PHOTO_DIR = '/tmp/photos'
PHOTO_COUNT = 5

# Remote camera configuration (from stream-lhs.sh)
REMOTE_HOST = "aura67@100.97.205.28"
DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 480
DEFAULT_FRAMERATE = 15
DEFAULT_BITRATE = 2000000
HLS_OUTPUT_DIR = "./hls_out"
HTTP_SERVER_PORT = 8000

# Global variables for process management
_stream_process = None
_http_server_process = None
_recording_processes = {}

class CameraController:
    """Enhanced camera controller with streaming capabilities"""
    
    def __init__(self, remote_host: str = REMOTE_HOST):
        self.remote_host = remote_host
        self.output_dir = Path(HLS_OUTPUT_DIR)
        self.output_dir.mkdir(exist_ok=True)
        
    def start_http_server(self, port: int = HTTP_SERVER_PORT) -> bool:
        """Start HTTP server to serve HLS stream"""
        global _http_server_process
        
        if _http_server_process and _http_server_process.poll() is None:
            print(f"HTTP server already running on port {port}")
            return True
            
        try:
            _http_server_process = subprocess.Popen([
                'python3', '-m', 'http.server', 
                '--directory', str(self.output_dir),
                str(port)
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Give server time to start
            time.sleep(1)
            
            if _http_server_process.poll() is None:
                print(f"HTTP server started on port {port}")
                print(f"Stream available at: http://localhost:{port}/stream.m3u8")
                return True
            else:
                print("Failed to start HTTP server")
                return False
                
        except Exception as e:
            print(f"Error starting HTTP server: {e}")
            return False
    
    def stop_http_server(self) -> bool:
        """Stop the HTTP server"""
        global _http_server_process
        
        if _http_server_process and _http_server_process.poll() is None:
            try:
                _http_server_process.terminate()
                _http_server_process.wait(timeout=5)
                print("HTTP server stopped")
                return True
            except subprocess.TimeoutExpired:
                _http_server_process.kill()
                print("HTTP server force killed")
                return True
            except Exception as e:
                print(f"Error stopping HTTP server: {e}")
                return False
        else:
            print("HTTP server not running")
            return True
    
    def start_stream(self, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT,
                    framerate: int = DEFAULT_FRAMERATE, bitrate: int = DEFAULT_BITRATE,
                    segment_duration: float = 0.5, playlist_size: int = 6) -> bool:
        """Start video streaming from remote camera"""
        global _stream_process
        
        if _stream_process and _stream_process.poll() is None:
            print("Stream already running")
            return True
            
        # Start HTTP server first
        if not self.start_http_server():
            return False
            
        try:
            # Calculate intra frame interval
            intra = int(framerate * segment_duration)
            
            # SSH command for remote camera
            ssh_cmd = [
                'ssh', self.remote_host,
                f'libcamera-vid -t 0 --codec h264 --inline '
                f'--framerate {framerate} --intra {intra} '
                f'--width {width} --height {height} '
                f'--bitrate {bitrate} --nopreview -o -'
            ]
            
            # FFmpeg command for HLS streaming
            ffmpeg_cmd = [
                'ffmpeg', '-hide_banner', '-loglevel', 'warning',
                '-fflags', '+genpts+nobuffer',
                '-flags', 'low_delay',
                '-probesize', '32', '-analyzeduration', '0',
                '-f', 'h264', '-r', str(framerate), '-i', 'pipe:0',
                '-c:v', 'copy',
                '-flush_packets', '1',
                '-muxdelay', '0', '-muxpreload', '0',
                '-f', 'hls',
                '-hls_time', str(segment_duration),
                '-hls_list_size', str(playlist_size),
                '-hls_flags', 'delete_segments+append_list+independent_segments+omit_endlist+discont_start',
                '-hls_segment_type', 'mpegts',
                '-hls_segment_filename', f'{self.output_dir}/stream_%03d.ts',
                f'{self.output_dir}/stream.m3u8'
            ]
            
            # Start SSH process
            ssh_process = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE)
            
            # Start FFmpeg process
            _stream_process = subprocess.Popen(
                ffmpeg_cmd, 
                stdin=ssh_process.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Close SSH stdout to allow proper pipe handling
            ssh_process.stdout.close()
            
            # Give processes time to start
            time.sleep(2)
            
            if _stream_process.poll() is None:
                print(f"Stream started successfully")
                print(f"Resolution: {width}x{height}")
                print(f"Framerate: {framerate} fps")
                print(f"Bitrate: {bitrate}")
                print(f"View stream at: http://localhost:{HTTP_SERVER_PORT}/stream.m3u8")
                return True
            else:
                print("Failed to start stream")
                return False
                
        except Exception as e:
            print(f"Error starting stream: {e}")
            return False
    
    def stop_stream(self) -> bool:
        """Stop the video stream"""
        global _stream_process
        
        success = True
        
        # Stop streaming process
        if _stream_process and _stream_process.poll() is None:
            try:
                _stream_process.terminate()
                _stream_process.wait(timeout=5)
                print("Stream stopped")
            except subprocess.TimeoutExpired:
                _stream_process.kill()
                print("Stream force killed")
            except Exception as e:
                print(f"Error stopping stream: {e}")
                success = False
        
        # Stop HTTP server
        if not self.stop_http_server():
            success = False
            
        return success
    
    def get_stream_status(self) -> Dict:
        """Get current stream status"""
        global _stream_process, _http_server_process
        
        status = {
            'streaming': _stream_process is not None and _stream_process.poll() is None,
            'http_server': _http_server_process is not None and _http_server_process.poll() is None,
            'output_dir': str(self.output_dir),
            'stream_url': f"http://localhost:{HTTP_SERVER_PORT}/stream.m3u8" if _http_server_process else None
        }
        
        # Check for HLS files
        if self.output_dir.exists():
            m3u8_file = self.output_dir / "stream.m3u8"
            ts_files = list(self.output_dir.glob("stream_*.ts"))
            
            status.update({
                'playlist_exists': m3u8_file.exists(),
                'segment_count': len(ts_files),
                'latest_segment': max(ts_files, key=lambda f: f.stat().st_mtime).name if ts_files else None
            })
        
        return status
    
    def capture_frame(self, output_path: str = None, width: int = DEFAULT_WIDTH, 
                     height: int = DEFAULT_HEIGHT) -> Optional[str]:
        """Capture a single frame from remote camera"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"/tmp/frame_{timestamp}.jpg"
        
        try:
            # SSH command for single frame capture
            ssh_cmd = [
                'ssh', self.remote_host,
                f'libcamera-jpeg --width {width} --height {height} '
                f'--nopreview --immediate -o -'
            ]
            
            # Capture frame
            result = subprocess.run(ssh_cmd, capture_output=True)
            
            if result.returncode == 0:
                # Save frame locally
                with open(output_path, 'wb') as f:
                    f.write(result.stdout)
                print(f"Frame captured: {output_path}")
                return output_path
            else:
                print(f"Failed to capture frame: {result.stderr.decode()}")
                return None
                
        except Exception as e:
            print(f"Error capturing frame: {e}")
            return None
    
    def capture_frames_from_stream(self, count: int = 1, interval: float = 1.0,
                                  output_dir: str = "/tmp/frames") -> List[str]:
        """Capture multiple frames from the current stream"""
        os.makedirs(output_dir, exist_ok=True)
        captured_frames = []
        
        for i in range(count):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            output_path = os.path.join(output_dir, f"frame_{timestamp}.jpg")
            
            try:
                # Use ffmpeg to extract frame from stream
                ffmpeg_cmd = [
                    'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
                    '-i', f'http://localhost:{HTTP_SERVER_PORT}/stream.m3u8',
                    '-vframes', '1',
                    '-q:v', '2',  # High quality
                    output_path
                ]
                
                result = subprocess.run(ffmpeg_cmd, capture_output=True, timeout=10)
                
                if result.returncode == 0 and os.path.exists(output_path):
                    captured_frames.append(output_path)
                    print(f"Frame {i+1}/{count} captured: {output_path}")
                else:
                    print(f"Failed to capture frame {i+1}: {result.stderr.decode()}")
                    
                if i < count - 1:  # Don't sleep after last frame
                    time.sleep(interval)
                    
            except subprocess.TimeoutExpired:
                print(f"Timeout capturing frame {i+1}")
            except Exception as e:
                print(f"Error capturing frame {i+1}: {e}")
        
        return captured_frames
    
    def capture_frame_for_analysis(self, width: int = 640, height: int = 480) -> Optional[str]:
        """Capture a frame optimized for object detection analysis"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"/tmp/analysis_frame_{timestamp}.jpg"
        
        # If stream is running, capture from stream for better quality
        if self.get_stream_status()['streaming']:
            frames = self.capture_frames_from_stream(count=1, output_dir="/tmp")
            return frames[0] if frames else None
        else:
            # Capture direct from camera
            return self.capture_frame(output_path, width, height)
    
    def start_recording(self, duration: int = 30, output_path: str = None,
                       width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT,
                       framerate: int = DEFAULT_FRAMERATE, bitrate: int = DEFAULT_BITRATE) -> Optional[str]:
        """Start recording a video segment"""
        global _recording_processes
        
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"/tmp/recording_{timestamp}.mp4"
        
        # Generate unique recording ID
        recording_id = f"rec_{int(time.time())}"
        
        try:
            # SSH command for remote camera
            ssh_cmd = [
                'ssh', self.remote_host,
                f'libcamera-vid -t {duration * 1000} --codec h264 '
                f'--framerate {framerate} --width {width} --height {height} '
                f'--bitrate {bitrate} --nopreview -o -'
            ]
            
            # FFmpeg command for recording
            ffmpeg_cmd = [
                'ffmpeg', '-y', '-hide_banner', '-loglevel', 'warning',
                '-f', 'h264', '-i', 'pipe:0',
                '-c:v', 'copy',
                '-movflags', '+faststart',
                output_path
            ]
            
            # Start SSH process
            ssh_process = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE)
            
            # Start FFmpeg process
            ffmpeg_process = subprocess.Popen(
                ffmpeg_cmd,
                stdin=ssh_process.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Close SSH stdout
            ssh_process.stdout.close()
            
            # Store process info
            _recording_processes[recording_id] = {
                'ssh_process': ssh_process,
                'ffmpeg_process': ffmpeg_process,
                'output_path': output_path,
                'start_time': time.time(),
                'duration': duration
            }
            
            print(f"Recording started: {recording_id}")
            print(f"Duration: {duration} seconds")
            print(f"Output: {output_path}")
            
            return recording_id
            
        except Exception as e:
            print(f"Error starting recording: {e}")
            return None
    
    def stop_recording(self, recording_id: str) -> bool:
        """Stop a specific recording"""
        global _recording_processes
        
        if recording_id not in _recording_processes:
            print(f"Recording {recording_id} not found")
            return False
        
        rec_info = _recording_processes[recording_id]
        
        try:
            # Stop FFmpeg process
            if rec_info['ffmpeg_process'].poll() is None:
                rec_info['ffmpeg_process'].terminate()
                rec_info['ffmpeg_process'].wait(timeout=10)
            
            # Stop SSH process
            if rec_info['ssh_process'].poll() is None:
                rec_info['ssh_process'].terminate()
                rec_info['ssh_process'].wait(timeout=5)
            
            # Remove from active recordings
            del _recording_processes[recording_id]
            
            print(f"Recording {recording_id} stopped")
            print(f"Saved to: {rec_info['output_path']}")
            
            return True
            
        except Exception as e:
            print(f"Error stopping recording {recording_id}: {e}")
            return False
    
    def get_recording_status(self, recording_id: str = None) -> Dict:
        """Get status of recordings"""
        global _recording_processes
        
        if recording_id:
            # Get specific recording status
            if recording_id not in _recording_processes:
                return {'error': f'Recording {recording_id} not found'}
            
            rec_info = _recording_processes[recording_id]
            elapsed = time.time() - rec_info['start_time']
            remaining = max(0, rec_info['duration'] - elapsed)
            
            return {
                'recording_id': recording_id,
                'output_path': rec_info['output_path'],
                'elapsed_time': elapsed,
                'remaining_time': remaining,
                'is_active': rec_info['ffmpeg_process'].poll() is None,
                'progress_percent': min(100, (elapsed / rec_info['duration']) * 100)
            }
        else:
            # Get all recordings status
            return {
                'active_recordings': len(_recording_processes),
                'recordings': {
                    rid: self.get_recording_status(rid) 
                    for rid in _recording_processes.keys()
                }
            }
    
    def cleanup_finished_recordings(self) -> int:
        """Remove finished recordings from process list"""
        global _recording_processes
        
        finished = []
        for recording_id, rec_info in _recording_processes.items():
            if rec_info['ffmpeg_process'].poll() is not None:
                finished.append(recording_id)
        
        for recording_id in finished:
            del _recording_processes[recording_id]
            print(f"Cleaned up finished recording: {recording_id}")
        
        return len(finished)
    
    def test_camera_connection(self) -> bool:
        """Test connection to remote camera"""
        try:
            result = subprocess.run([
                'ssh', '-o', 'ConnectTimeout=5', self.remote_host, 
                'echo "Camera connection test"'
            ], capture_output=True, timeout=10)
            
            if result.returncode == 0:
                print("Camera connection successful")
                return True
            else:
                print(f"Camera connection failed: {result.stderr.decode()}")
                return False
                
        except Exception as e:
            print(f"Error testing camera connection: {e}")
            return False
    
    def get_camera_info(self) -> Dict:
        """Get camera capabilities and information"""
        try:
            result = subprocess.run([
                'ssh', self.remote_host, 
                'libcamera-hello --list-cameras'
            ], capture_output=True, timeout=10)
            
            if result.returncode == 0:
                info = {
                    'connected': True,
                    'camera_list': result.stdout.decode(),
                    'remote_host': self.remote_host
                }
            else:
                info = {
                    'connected': False,
                    'error': result.stderr.decode(),
                    'remote_host': self.remote_host
                }
            
            return info
            
        except Exception as e:
            return {
                'connected': False,
                'error': str(e),
                'remote_host': self.remote_host
            }
    
    def set_camera_settings(self, settings: Dict) -> bool:
        """Apply camera settings for next operation"""
        # This would update the default settings for subsequent operations
        valid_settings = ['width', 'height', 'framerate', 'bitrate']
        
        for key, value in settings.items():
            if key in valid_settings:
                globals()[f'DEFAULT_{key.upper()}'] = value
                print(f"Updated {key}: {value}")
            else:
                print(f"Invalid setting: {key}")
                return False
        
        return True

# Legacy functions updated to work with new system
def take_photos(count=PHOTO_COUNT, save_dir=PHOTO_DIR):
    """Legacy function updated to use remote camera"""
    controller = CameraController()
    
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    photo_paths = []
    
    for i in range(count):
        photo_path = os.path.join(save_dir, f'photo_{i+1}.jpg')
        captured_path = controller.capture_frame(photo_path)
        
        if captured_path:
            photo_paths.append(captured_path)
            print(f"Captured photo {i+1}/{count}")
        else:
            print(f"Failed to capture photo {i+1}")
        
        if i < count - 1:  # Don't sleep after last photo
            time.sleep(1)
    
    return photo_paths

def send_photos(photo_paths, server_url=SERVER_URL):
    """Send photos to server - unchanged from original"""
    for photo_path in photo_paths:
        with open(photo_path, 'rb') as f:
            files = {'photo': f}
            response = requests.post(server_url, files=files)
            if response.status_code == 200:
                print(f"Uploaded {photo_path} successfully.")
            else:
                print(f"Failed to upload {photo_path}: {response.status_code}")

# Convenience functions for easy testing
def quick_stream(duration: int = 60):
    """Start a quick stream for testing"""
    controller = CameraController()
    
    print(f"Starting stream for {duration} seconds...")
    if controller.start_stream():
        try:
            time.sleep(duration)
        except KeyboardInterrupt:
            print("\nStopping stream...")
        finally:
            controller.stop_stream()
    else:
        print("Failed to start stream")

def quick_capture(output_path: str = None):
    """Quick frame capture for testing"""
    controller = CameraController()
    
    frame_path = controller.capture_frame(output_path)
    if frame_path:
        print(f"Frame captured: {frame_path}")
        return frame_path
    else:
        print("Failed to capture frame")
        return None

def quick_record(duration: int = 10, output_path: str = None):
    """Quick recording for testing"""
    controller = CameraController()
    
    recording_id = controller.start_recording(duration, output_path)
    if recording_id:
        print(f"Recording for {duration} seconds...")
        
        # Monitor progress
        start_time = time.time()
        while time.time() - start_time < duration:
            status = controller.get_recording_status(recording_id)
            if not status.get('is_active', False):
                break
            
            progress = status.get('progress_percent', 0)
            remaining = status.get('remaining_time', 0)
            print(f"\rProgress: {progress:.1f}% - {remaining:.1f}s remaining", end='')
            time.sleep(1)
        
        print("\nRecording completed")
        controller.cleanup_finished_recordings()
        return recording_id
    else:
        print("Failed to start recording")
        return None

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Camera Control System')
    parser.add_argument('action', choices=[
        'photos', 'stream', 'capture', 'record', 'test', 'status', 'stop'
    ], help='Action to perform')
    
    parser.add_argument('--duration', type=int, default=30, help='Duration for stream/record')
    parser.add_argument('--count', type=int, default=5, help='Number of photos to take')
    parser.add_argument('--output', type=str, help='Output path/directory')
    parser.add_argument('--width', type=int, default=DEFAULT_WIDTH, help='Video width')
    parser.add_argument('--height', type=int, default=DEFAULT_HEIGHT, help='Video height')
    parser.add_argument('--framerate', type=int, default=DEFAULT_FRAMERATE, help='Video framerate')
    parser.add_argument('--bitrate', type=int, default=DEFAULT_BITRATE, help='Video bitrate')
    
    args = parser.parse_args()
    
    controller = CameraController()
    
    if args.action == 'photos':
        # Legacy photo taking
        save_dir = args.output or PHOTO_DIR
        photos = take_photos(args.count, save_dir)
        print(f"Captured {len(photos)} photos in {save_dir}")
        
    elif args.action == 'stream':
        # Start streaming
        print(f"Starting stream for {args.duration} seconds...")
        if controller.start_stream(args.width, args.height, args.framerate, args.bitrate):
            try:
                time.sleep(args.duration)
            except KeyboardInterrupt:
                print("\nStopping stream...")
            finally:
                controller.stop_stream()
        
    elif args.action == 'capture':
        # Capture single frame
        frame_path = controller.capture_frame(args.output, args.width, args.height)
        if frame_path:
            print(f"Frame captured: {frame_path}")
        
    elif args.action == 'record':
        # Record video
        recording_id = controller.start_recording(
            args.duration, args.output, args.width, args.height, 
            args.framerate, args.bitrate
        )
        if recording_id:
            print(f"Recording {recording_id} started for {args.duration} seconds")
            print("Use 'python control.py status' to check progress")
        
    elif args.action == 'test':
        # Test camera connection
        print("Testing camera connection...")
        if controller.test_camera_connection():
            print("Camera test successful!")
            
            # Get camera info
            info = controller.get_camera_info()
            if info['connected']:
                print("Camera information:")
                print(info['camera_list'])
            
            # Quick functionality test
            print("\nTesting frame capture...")
            frame = controller.capture_frame()
            if frame:
                print(f"Test frame captured: {frame}")
            
        else:
            print("Camera test failed!")
            
    elif args.action == 'status':
        # Show status
        stream_status = controller.get_stream_status()
        recording_status = controller.get_recording_status()
        
        print("=== CAMERA STATUS ===")
        print(f"Stream active: {stream_status['streaming']}")
        print(f"HTTP server: {stream_status['http_server']}")
        if stream_status['stream_url']:
            print(f"Stream URL: {stream_status['stream_url']}")
        
        print(f"\nActive recordings: {recording_status['active_recordings']}")
        if recording_status['recordings']:
            for rid, rec_info in recording_status['recordings'].items():
                print(f"  {rid}: {rec_info['progress_percent']:.1f}% complete")
        
    elif args.action == 'stop':
        # Stop everything
        print("Stopping all operations...")
        controller.stop_stream()
        
        # Stop all recordings
        recording_status = controller.get_recording_status()
        for recording_id in recording_status['recordings'].keys():
            controller.stop_recording(recording_id)
        
        print("All operations stopped")