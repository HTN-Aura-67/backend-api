from Detic.pipeline import predict_pipe_line
import cv2
import os

if __name__ == "__main__":
    PWD = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(PWD, "test-imgs", "food.jpg")  # Change to your input image path!
    object_list = ['avocada', 'carrot', 'tomato', 'raspberry']  # Change to your custom vocabulary
    im = cv2.imread(image_path)
    result = predict_pipe_line(im, object_list)
    print(result)
