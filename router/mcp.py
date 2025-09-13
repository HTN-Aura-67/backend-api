from __future__ import annotations
import base64, io, time, math
from dataclasses import dataclass
from typing import List, Literal, Optional, Tuple

import numpy as np
from PIL import Image
# If you have OpenCV on the Pi:
import cv2

from mcp.server.fastmcp import FastMCP, Context

# ---------- Types ----------

@dataclass
class BBox:
    x: int
    y: int
    w: int
    h: int

@dataclass
class DetectedObject:
    id: str
    label: str
    confidence: float
    angle: float  # Current angle when detected
    bbox: BBox
    area_px: int

# ---------- Hardware stubs (replace with your real calls) ----------
def _capture_png() -> bytes:
    """
    Replace with libcamera or cv2.VideoCapture frame grab + encode.
    For now, generate a dummy image.
    """
    img = np.zeros((240, 320, 3), dtype=np.uint8)
    cv2.putText(img, "CAMERA", (40, 120),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2, cv2.LINE_AA)
    ok, buf = cv2.imencode(".png", img)
    return buf.tobytes() if ok else b""

def _run_detector(image_png: bytes, current_angle: float,
                  max_objects: int) -> List[DetectedObject]:
    """
    Replace with a real detector (e.g., Ultralytics YOLOv8n/YOLOv5n).
    Return a few fake boxes so the tool shape is exercised.
    """
    h, w = 240, 320
    objs: List[DetectedObject] = []
    # Fake: one box 
    bbox = BBox(x=int(w*0.4), y=int(h*0.3), w=64, h=96)
    objs.append(DetectedObject(
        id=f"obj_{int(current_angle)}_{int(time.time())}",
        label="bottle",
        confidence=0.92,
        angle=current_angle,
        bbox=bbox,
        area_px=bbox.w * bbox.h
    ))
    return objs[:max_objects]

def _point_to_angle(angle_deg: float):
    """Point/rotate chassis to an absolute angle (0=front, 90=right, etc)."""
    time.sleep(0.1)

def _get_current_angle() -> float:
    """Get current chassis heading in degrees (stub)."""
    return 0.0

def _center_object_and_advance(stop_distance_m: float, timeout_s: int) -> Tuple[str, float, int, int, bytes]:
    """
    Visual servoing loop (stub):
    - Maintain the target at image center (PID on x-offset)
    - Move forward until estimated range ~ stop_distance_m
    Returns: status, final_range_m, steps, turns, terminal_snapshot_png
    """
    # Simulate success:
    time.sleep(min(timeout_s, 2))
    snapshot = _capture_png("front")
    return ("arrived", stop_distance_m, 28, 2, snapshot)

def _motors_stop():
    """Emergency/clean stop (stub)."""
    pass

def _set_led_bitmap(width: int, height: int, data: List[int]):
    """Write to MAX7219/HT16K33/etc. (stub)."""
    pass

# ---------- Utils ----------
def _b64(png_bytes: bytes) -> str:
    return base64.b64encode(png_bytes).decode("ascii")

# ---------- MCP server ----------
mcp = FastMCP("car-agent")

@mcp.tool()
def point_direction(angle_deg: float):
    """
    Point the car to a specific angle.
    Args:
        angle_deg: Absolute angle in degrees (0=front, 90=right, 180=back, 270=left)
    Returns:
        status and current angle
    """
    _point_to_angle(angle_deg)
    current = _get_current_angle()
    return {
        "status": "ok", 
        "target_angle": angle_deg,
        "current_angle": current
    }

# ---------- MCP server ----------
mcp = FastMCP("car-agent")

@mcp.tool()
def look_around(
    sweep_angles: Optional[List[float]] = None,
    per_angle_pause_ms: int = 250,
    max_objects: int = 20,
    return_images: bool = True,
):
    """
    Sweep through specified angles, capture PNGs, detect objects.
    Args:
      sweep_angles: list of angles in degrees to point to; if omitted uses [0,90,180,270].
      per_angle_pause_ms: pause after each rotation.
      max_objects: max objects to return across all views.
      return_images: include base64 PNGs.
    Returns:
      images: list of {angle, mime_type, base64}
      objects: list of DetectedObject dicts
      telemetry: e.g., battery/pose (stubbed here)
    """
    images = []
    objects: List[dict] = []
    angles = sweep_angles or [0.0, 90.0, 180.0, 270.0]

    for angle in angles:
        _point_to_angle(angle)
        time.sleep(per_angle_pause_ms / 1000.0)
        
        png = _capture_png()
        if return_images:
            images.append({
                "angle": angle, 
                "mime_type": "image/png", 
                "base64": _b64(png)
            })

        dets = _run_detector(png, angle, max_objects=max(1, max_objects // len(angles)))
        for d in dets:
            objects.append({
                "id": d.id,
                "label": d.label,
                "confidence": d.confidence,
                "angle": d.angle,
                "bbox": d.bbox.__dict__,
                "area_px": d.area_px
            })

    telemetry = {"battery_v": 7.8, "pose": {"x": 0.0, "y": 0.0, "theta_deg": _get_current_angle()}}
    return {"images": images, "objects": objects, "telemetry": telemetry}

@mcp.tool()
def approach_object(
    object_id: str,
    stop_distance_m: float = 0.30,
    timeout_s: int = 30,
    strategy: Literal["center_then_advance", "pure_pursuit"] = "center_then_advance",
):
    """
    Navigate toward a previously detected object.
    Returns:
      status: "arrived" | "lost" | "blocked" | "timeout" | "aborted"
      final_range_m, path_summary, snapshot (PNG b64)
    """
    # In a real setup, you’d:
    # 1) Reacquire the object by id (cache from look_around)
    # 2) Center (PID on bbox.x + yaw) then move forward, gating by TOF/bumper
    status, rng, steps, turns, snap = _center_object_and_advance(stop_distance_m, timeout_s)
    return {
        "status": status,
        "final_range_m": rng,
        "path_summary": {"steps": steps, "turns": turns},
        "snapshot": {"mime_type": "image/png", "base64": _b64(snap)}
    }

@mcp.tool()
def terminate(reason: str = "user_request"):
    """
    Safely stop motion and release resources.
    """
    _motors_stop()
    # Close camera, threads, GPIO, etc.
    return {"status": "ok", "reason": reason}

# Simple 8x8 presets
PRESETS = {
    "smile":  [
        "00111100",
        "01000010",
        "10100101",
        "10000001",
        "10100101",
        "10011001",
        "01000010",
        "00111100",
    ],
    "heart":  [
        "01100110",
        "11111111",
        "11111111",
        "11111111",
        "01111110",
        "00111100",
        "00011000",
        "00000000",
    ],
}

@mcp.tool()
def set_led_emoji(
    preset: Optional[Literal["smile","heart"]] = None,
    emoji: Optional[str] = None,
    bitmap: Optional[dict] = None,
):
    """
    Display an emoji/preset/bitmap on the LED matrix.
    Provide exactly one of: preset, emoji, bitmap.
    - preset: "smile" or "heart"
    - emoji: a single-char glyph (render via your own font mapping)
    - bitmap: {"width":8,"height":8,"data":[0/1,... length=64]}
    """
    choices = [preset is not None, emoji is not None, bitmap is not None]
    if sum(choices) != 1:
        return {"error": "Provide exactly one of preset, emoji, or bitmap"}

    if preset:
        rows = PRESETS[preset]
        data = [int(c) for row in rows for c in row]
        _set_led_bitmap(8, 8, data)
        return {"status": "ok", "mode": "preset", "name": preset}

    if emoji:
        # TODO: map the emoji to an 8x8 glyph using a tiny font table
        # For now, render a square “face”
        data = [0]*64
        for i in range(64):
            x, y = i % 8, i // 8
            if (x in (2,5) and y in (2,3)) or (y in (5,) and 1 <= x <= 6):
                data[i] = 1
        _set_led_bitmap(8, 8, data)
        return {"status": "ok", "mode": "emoji", "char": emoji}

    # bitmap path
    w = int(bitmap["width"]); h = int(bitmap["height"]); data = list(bitmap["data"])
    if w*h != len(data):
        return {"error": "bitmap size does not match data length"}
    _set_led_bitmap(w, h, data)
    return {"status": "ok", "mode": "bitmap"}

# Optional read-only resources
@mcp.resource("car://state")
def state_resource():
    return ("application/json",
            b'{"battery_v":7.8,"pose":{"x":0,"y":0,"theta_deg":0}}')

if __name__ == "__main__":
    mcp.run()  # stdio transport
