"""
detection/person_detector.py
==============================
Detects persons in a video frame using YOLOv8.
Also attempts basic gender classification.
"""

import cv2
import numpy as np
from utils.logger import setup_logger

logger = setup_logger("PersonDetector")


class PersonDetector:
    def __init__(self, model_size="yolov8n.pt"):
        """
        model_size options:
          yolov8n.pt  — nano  (fastest, less accurate)
          yolov8s.pt  — small
          yolov8m.pt  — medium (recommended)
          yolov8l.pt  — large (most accurate, slowest)
        """
        try:
            from ultralytics import YOLO
            logger.info(f"Loading YOLO model: {model_size}")
            self.model = YOLO(model_size)
            self.yolo_available = True
            logger.info("✅ YOLO model loaded successfully")
        except ImportError:
            logger.warning("ultralytics not installed — using fallback HOG detector")
            self.yolo_available = False
            # Fallback: OpenCV HOG people detector
            self.hog = cv2.HOGDescriptor()
            self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

        # COCO class index for person
        self.PERSON_CLASS = 0

    def detect(self, frame):
        """
        Detect all persons in a frame.

        Returns:
            list of dicts:
            [
              {
                "bbox": [x1, y1, x2, y2],
                "confidence": 0.87,
                "class": "person",
                "gender": "unknown"  # can be extended with gender model
              },
              ...
            ]
        """
        if self.yolo_available:
            return self._detect_yolo(frame)
        else:
            return self._detect_hog(frame)

    def _detect_yolo(self, frame):
        """Use YOLOv8 for detection."""
        results = self.model(frame, verbose=False, conf=0.4)
        detections = []

        for result in results:
            for box in result.boxes:
                cls = int(box.cls[0])
                if cls == self.PERSON_CLASS:  # Only persons
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    detections.append({
                        "bbox":       [x1, y1, x2, y2],
                        "confidence": round(conf, 3),
                        "class":      "person",
                        "gender":     "unknown",
                        "area":       (x2 - x1) * (y2 - y1),
                    })

        return detections

    def _detect_hog(self, frame):
        """Fallback HOG detector (no YOLO)."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rects, weights = self.hog.detectMultiScale(
            gray, winStride=(8, 8), padding=(4, 4), scale=1.05
        )
        detections = []
        for i, (x, y, w, h) in enumerate(rects):
            detections.append({
                "bbox":       [x, y, x + w, y + h],
                "confidence": float(weights[i][0]) if len(weights) > i else 0.5,
                "class":      "person",
                "gender":     "unknown",
                "area":       w * h,
            })
        return detections

    def count_persons(self, detections):
        """Return total person count."""
        return len(detections)

    def woman_likely_present(self, detections):
        """
        Heuristic: smaller bounding boxes in a group
        can suggest mixed gender (extend with a real
        gender classifier for better accuracy).
        """
        if not detections:
            return False
        # Placeholder: assume woman present if 1+ persons
        # Replace with actual gender model in production
        return len(detections) >= 1

    def draw_detections(self, frame, detections):
        """Draw bounding boxes on frame for visualization."""
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            conf = det["confidence"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"Person {conf:.0%}"
            cv2.putText(frame, label, (x1, y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        return frame
