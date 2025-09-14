# Camera Control API

A FastAPI service that provides REST endpoints for camera streaming, recording, and frame capture operations. This service wraps the existing `CameraController` functionality and provides a web API interface.

## Features

- 🎥 **Video Streaming**: Start/stop HLS video streams with custom settings
- 📸 **Frame Capture**: Capture individual frames from the remote camera
- 🎬 **Video Recording**: Record video segments with progress monitoring
- 📷 **Photo Scanning**: Take multiple photos for surroundings analysis
- 🔒 **API Authentication**: Secure endpoints with API key authentication
- 🌐 **CORS Support**: Configured for frontend integration
- 📁 **Static File Serving**: Serves HLS stream files directly

## Quick Start

### 1. Install Dependencies

```bash
# Using pip
pip install -r requirements.txt

# Or using the project file
pip install -e .
```

### 2. Environment Setup

Create a `.env` file in the project root:

```env
BACKEND_API_KEY=dev-secret
FRONTEND_ORIGIN=http://localhost:3000
PORT=5055
```

### 3. Run the Server

```bash
# Development mode with auto-reload
BACKEND_API_KEY=dev-secret FRONTEND_ORIGIN=http://localhost:3000 uvicorn router.server:app --host 0.0.0.0 --port 5055 --reload

# Production mode
BACKEND_API_KEY=your-secret-key uvicorn router.server:app --host 0.0.0.0 --port 5055
```

### 4. Access the API

- **API Documentation**: http://localhost:5055/docs
- **Health Check**: http://localhost:5055/health
- **HLS Stream**: http://localhost:5055/stream.m3u8 (when streaming)

## API Endpoints

### Authentication

All endpoints (except `/health` and static files) require the `x-api-key` header:

```bash
curl -H "x-api-key: dev-secret" http://localhost:5055/health
```

### Core Endpoints

#### Health Check
```http
GET /health
```
Returns: `{"ok": true, "status": "healthy"}`

#### Scan Surroundings
```http
POST /scan-surroundings
Content-Type: application/json
x-api-key: your-api-key

{
  "count": 5
}
```

#### Stream Control
```http
# Start streaming
POST /stream/start
{
  "width": 640,
  "height": 480,
  "framerate": 15,
  "bitrate": 2000000,
  "segmentDuration": 0.5,
  "playlistSize": 6
}

# Stop streaming  
POST /stream/stop

# Get stream status
GET /stream/status
```

#### Frame Capture
```http
POST /capture
{
  "width": 640,
  "height": 480
}
```

#### Recording Control
```http
# Start recording
POST /record/start
{
  "duration": 30,
  "width": 640,
  "height": 480,
  "framerate": 15,
  "bitrate": 2000000
}

# Stop recording
POST /record/stop
{
  "recording_id": "rec_1234567890"
}

# Get recording status
GET /record/status?recording_id=rec_1234567890
```

#### Camera Testing
```http
POST /camera/test
```

#### Cleanup
```http
POST /cleanup
```

## Usage Examples

### Python Client Example

```python
import requests

# Configuration
API_BASE = "http://localhost:5055"
API_KEY = "dev-secret"
headers = {"x-api-key": API_KEY}

# Test camera connection
response = requests.post(f"{API_BASE}/camera/test", headers=headers)
print(response.json())

# Start streaming
stream_config = {
    "width": 1280,
    "height": 720,
    "framerate": 30,
    "bitrate": 3000000
}
response = requests.post(f"{API_BASE}/stream/start", 
                        json=stream_config, headers=headers)
print(response.json())

# Capture a frame
response = requests.post(f"{API_BASE}/capture", 
                        json={"width": 640, "height": 480}, 
                        headers=headers)
frame_info = response.json()
print(f"Frame captured: {frame_info['data']['frame_path']}")

# Stop stream
requests.post(f"{API_BASE}/stream/stop", headers=headers)
```

### JavaScript/Frontend Example

```javascript
const API_BASE = 'http://localhost:5055';
const API_KEY = 'dev-secret';

const headers = {
  'Content-Type': 'application/json',
  'x-api-key': API_KEY
};

// Start streaming
async function startStream() {
  const response = await fetch(`${API_BASE}/stream/start`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      width: 640,
      height: 480,
      framerate: 15,
      bitrate: 2000000
    })
  });
  
  const result = await response.json();
  if (result.success) {
    console.log('Stream started:', result.data.stream_url);
    
    // Load HLS stream in video player
    const video = document.getElementById('video');
    video.src = '/stream.m3u8';
  }
}

// Capture frame
async function captureFrame() {
  const response = await fetch(`${API_BASE}/capture`, {
    method: 'POST',
    headers,
    body: JSON.stringify({width: 640, height: 480})
  });
  
  const result = await response.json();
  console.log('Frame captured:', result.data.frame_path);
}
```

### cURL Examples

```bash
# Health check
curl http://localhost:5055/health

# Start stream
curl -X POST http://localhost:5055/stream/start \
  -H "x-api-key: dev-secret" \
  -H "Content-Type: application/json" \
  -d '{"width": 640, "height": 480, "framerate": 15}'

# Capture frame
curl -X POST http://localhost:5055/capture \
  -H "x-api-key: dev-secret" \
  -H "Content-Type: application/json" \
  -d '{"width": 640, "height": 480}'

# Scan surroundings
curl -X POST http://localhost:5055/scan-surroundings \
  -H "x-api-key: dev-secret" \
  -H "Content-Type: application/json" \
  -d '{"count": 3}'
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_API_KEY` | `dev-secret` | API key for authentication |
| `FRONTEND_ORIGIN` | `http://localhost:3000` | CORS origin for frontend |
| `PORT` | `5055` | Server port |

### Camera Configuration

The camera settings are managed by the underlying `CameraController` class. Default settings can be modified in `camera/control.py`:

- **Remote Host**: `aura67@100.97.205.28`
- **Default Resolution**: 640x480
- **Default Framerate**: 15 fps
- **Default Bitrate**: 2,000,000 bps

## Development

## Development

### Running Tests

The project includes comprehensive test suites to validate API functionality:

#### Quick Tests (Recommended)
```bash
# Simple test runner (no dependencies)
python tests/run_tests.py

# Test specific functionality
python test_scan.py
```

#### Comprehensive Test Suite
```bash
# Install test dependencies
pip install -r requirements.txt
# Or install dev dependencies
pip install -e ".[dev]"

# Run all tests with pytest
pytest

# Run specific test files
pytest tests/test_camera_api.py -v
pytest tests/run_tests.py -v

# Run specific test classes
pytest tests/test_camera_api.py::TestAuthentication -v
pytest tests/test_camera_api.py::TestScanSurroundings -v

# Run tests with coverage
pytest --cov=server --cov-report=html
```

#### Load Testing
```bash
# Test API performance under load
python tests/load_test.py

# Requires aiohttp for async requests (included in dev dependencies)
pip install aiohttp
```

### Test Structure

- **`tests/run_tests.py`** - Quick standalone test runner
- **`tests/test_camera_api.py`** - Comprehensive pytest test suite
- **`tests/load_test.py`** - Load and performance testing
- **`test_scan.py`** - Simple endpoint test example (root level)

### Test Categories

1. **Health & Info Tests** - Basic connectivity and API info
2. **Authentication Tests** - API key validation and security
3. **Camera Tests** - Camera connection and functionality
4. **Stream Tests** - Video streaming endpoints
5. **Recording Tests** - Video recording functionality
6. **Validation Tests** - Input validation and error handling
7. **Integration Tests** - Complete workflow scenarios
8. **Load Tests** - Concurrent request handling

### Test Requirements

- **Server Running**: Tests require the API server to be running
- **Camera Optional**: Many tests work without camera hardware
- **Network**: Some tests require network connectivity for SSH camera access

### Code Formatting

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Format code
black .

# Lint code
flake8 .
```

### Project Structure

```
├── router/
│   └── server.py          # FastAPI application
├── camera/
│   ├── control.py         # Camera controller logic
│   └── test_camera_control.py
├── tests/                 # Test suite
│   ├── test_camera_api.py
│   ├── run_tests.py
│   └── load_test.py
├── hls_out/              # HLS stream output directory
├── requirements.txt       # Python dependencies
├── pyproject.toml         # Project configuration
├── .env                   # Environment variables
└── README.md
```

## Deployment

### Docker (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "5055"]
```

### Systemd Service

```ini
[Unit]
Description=Camera Control API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/backend-api
Environment=BACKEND_API_KEY=production-secret
Environment=FRONTEND_ORIGIN=https://your-frontend.com
ExecStart=/usr/local/bin/uvicorn router.server:app --host 0.0.0.0 --port 5055
Restart=always

[Install]
WantedBy=multi-user.target
```

## Troubleshooting

### Common Issues

1. **Camera Connection Failed**
   - Verify SSH access to remote camera: `ssh aura67@100.97.205.28`
   - Check network connectivity and camera status

2. **Stream Not Starting**
   - Ensure FFmpeg is installed: `ffmpeg -version`
   - Check that port 8000 is available for HTTP server
   - Verify camera is not being used by another process

3. **API Authentication Errors**
   - Check that `x-api-key` header is included in requests
   - Verify the API key matches the `BACKEND_API_KEY` environment variable

4. **CORS Issues**
   - Ensure `FRONTEND_ORIGIN` matches your frontend URL
   - Check that required headers are included in CORS configuration

### Logs

Enable verbose logging:

```bash
uvicorn router.server:app --host 0.0.0.0 --port 5055 --log-level debug
```

### Health Monitoring

The `/health` endpoint provides basic health information. For production, consider implementing more comprehensive health checks.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details.