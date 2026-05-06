from ultralytics import YOLO
import numpy as np


class Detector:
    """YOLOv8 object detector."""

    def __init__(self, model_path: str, device: str = "cpu"):
        self.model = YOLO(model_path)
        self.device = device

    def detect(self, frame: np.ndarray) -> np.ndarray:
        """
        Run detection on a frame.

        Returns:
            np.ndarray of shape (N, 6): [x1, y1, x2, y2, confidence, class_id]
            Returns empty (0, 6) array if no detections.
        """
        results = self.model(frame, device=self.device, verbose=False)[0]
        boxes = results.boxes
        if boxes is None or len(boxes) == 0:
            return np.empty((0, 6))
        return boxes.data.cpu().numpy()
