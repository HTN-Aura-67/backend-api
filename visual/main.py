from Detic.pipeline import predict_pipe_line
import cv2
import os
import torch
from typing import List, Dict, Any

class DetectedObject:
    """Class to represent a detected object with its coordinates and metadata"""
    
    def __init__(self, class_name: str, confidence: float, bbox: torch.Tensor, 
                 image_width: int, image_height: int):
        self.class_name = class_name
        self.confidence = confidence
        self.bbox_tensor = bbox  # Original tensor format
        self.image_width = image_width
        self.image_height = image_height
        
        # Extract coordinates from tensor (format: [x1, y1, x2, y2])
        coords = bbox.cpu().numpy()
        self.x1, self.y1, self.x2, self.y2 = coords
        
        # Calculate additional useful properties
        self.width = self.x2 - self.x1
        self.height = self.y2 - self.y1
        self.center_x = (self.x1 + self.x2) / 2
        self.center_y = (self.y1 + self.y2) / 2
        self.area = self.width * self.height
        
    def get_corners(self) -> Dict[str, tuple]:
        """Get all four corner coordinates"""
        return {
            'top_left': (self.x1, self.y1),
            'top_right': (self.x2, self.y1),
            'bottom_left': (self.x1, self.y2),
            'bottom_right': (self.x2, self.y2)
        }
    
    def get_normalized_coords(self) -> Dict[str, float]:
        """Get normalized coordinates (0-1 range) relative to image size"""
        return {
            'x1_norm': self.x1 / self.image_width,
            'y1_norm': self.y1 / self.image_height,
            'x2_norm': self.x2 / self.image_width,
            'y2_norm': self.y2 / self.image_height,
            'center_x_norm': self.center_x / self.image_width,
            'center_y_norm': self.center_y / self.image_height
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for easy serialization"""
        return {
            'class_name': self.class_name,
            'confidence': float(self.confidence),
            'bbox': {
                'x1': float(self.x1),
                'y1': float(self.y1),
                'x2': float(self.x2),
                'y2': float(self.y2)
            },
            'center': {
                'x': float(self.center_x),
                'y': float(self.center_y)
            },
            'dimensions': {
                'width': float(self.width),
                'height': float(self.height),
                'area': float(self.area)
            },
            'corners': self.get_corners(),
            'normalized_coords': self.get_normalized_coords()
        }
    
    def __repr__(self):
        return f"DetectedObject(class='{self.class_name}', confidence={self.confidence:.2f}, bbox=({self.x1:.1f}, {self.y1:.1f}, {self.x2:.1f}, {self.y2:.1f}))"

def extract_detected_objects(outputs: Dict[str, Any], object_list: List[str], 
                           image_width: int, image_height: int) -> List[DetectedObject]:
    """Extract detected objects from Detic outputs and return as DetectedObject instances"""
    
    instances = outputs["instances"]
    detected_objects = []
    
    # Get the number of detections
    num_detections = len(instances)
    
    if num_detections == 0:
        print("No objects detected!")
        return detected_objects
    
    # Extract data from tensors
    pred_classes = instances.pred_classes.cpu().numpy()
    scores = instances.scores.cpu().numpy()
    pred_boxes = instances.pred_boxes.tensor.cpu()
    
    print(f"Found {num_detections} detected objects:")
    
    for i in range(num_detections):
        class_idx = pred_classes[i]
        confidence = scores[i]
        bbox = pred_boxes[i]
        
        # Get class name
        if object_list and class_idx < len(object_list):
            class_name = object_list[class_idx]
        else:
            class_name = f"class_{class_idx}"
        
        # Create DetectedObject instance
        obj = DetectedObject(class_name, confidence, bbox, image_width, image_height)
        detected_objects.append(obj)
        
        print(f"  {i+1}. {obj}")
    
    return detected_objects

if __name__ == "__main__":
    PWD = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(PWD, "test-imgs", "bird.jpg")  # Change to your input image path!
    object_list = ['bird']  # Change to your custom vocabulary
    
    # Load image
    im = cv2.imread(image_path)
    if im is None:
        print(f"Error: Could not load image from {image_path}")
        exit(1)
    
    image_height, image_width = im.shape[:2]
    print(f"Image dimensions: {image_width}x{image_height}")
    
    # Run detection
    result = predict_pipe_line(im, object_list)
    
    # Extract detected objects with coordinates
    detected_objects = extract_detected_objects(result, object_list, image_width, image_height)
    
    # Print detailed information for each detected object
    print("\n" + "="*50)
    print("DETAILED DETECTION RESULTS:")
    print("="*50)
    
    for i, obj in enumerate(detected_objects):
        print(f"\nObject {i+1}:")
        print(f"  Class: {obj.class_name}")
        print(f"  Confidence: {obj.confidence:.2%}")
        print(f"  Bounding Box: ({obj.x1:.1f}, {obj.y1:.1f}) to ({obj.x2:.1f}, {obj.y2:.1f})")
        print(f"  Center: ({obj.center_x:.1f}, {obj.center_y:.1f})")
        print(f"  Size: {obj.width:.1f} x {obj.height:.1f} pixels")
        print(f"  Area: {obj.area:.1f} square pixels")
        print(f"  Corners: {obj.get_corners()}")
        print(f"  Normalized coords: {obj.get_normalized_coords()}")
    
    # Example: Convert to dictionary format for easy use
    print("\n" + "="*50)
    print("SERIALIZED FORMAT (for API/algorithm use):")
    print("="*50)
    
    serialized_objects = [obj.to_dict() for obj in detected_objects]
    for i, obj_dict in enumerate(serialized_objects):
        print(f"\nObject {i+1} (dict format):")
        print(obj_dict)
    
    # Example: Calculate distances (placeholder for your distance algorithm)
    print("\n" + "="*50)
    print("EXAMPLE: Distance calculation setup:")
    print("="*50)
    
    if detected_objects:
        # Example: Calculate distance from image center to each object
        image_center_x = image_width / 2
        image_center_y = image_height / 2
        
        for i, obj in enumerate(detected_objects):
            # Simple Euclidean distance from image center
            distance_from_center = ((obj.center_x - image_center_x)**2 + 
                                  (obj.center_y - image_center_y)**2)**0.5
            print(f"Object {i+1} distance from image center: {distance_from_center:.1f} pixels")
            
            # You can add your specific distance calculation algorithm here
            # For example, if you know the camera parameters, you could calculate
            # real-world distance using the bounding box size and camera focal length
