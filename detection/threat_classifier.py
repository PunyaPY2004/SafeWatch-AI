"""
detection/threat_classifier.py
================================
Combines person detection + pose estimation signals
into a final threat score and threat type label.

This uses a rule-based scoring engine by default.
You can replace/extend with a trained CNN model.
"""

import cv2
import numpy as np
import os
from utils.logger import setup_logger

logger = setup_logger("ThreatClassifier")


class ThreatClassifier:
    def __init__(self, model_path="models/threat_model.h5"):
        """
        Tries to load a trained Keras CNN model.
        Falls back to rule-based scoring if model not found.
        """
        self.model = None
        self.model_available = False

        if os.path.exists(model_path):
            try:
                from tensorflow.keras.models import load_model
                self.model = load_model(model_path)
                self.model_available = True
                self.IMG_SIZE = (224, 224)
                logger.info(f"✅ Threat CNN model loaded: {model_path}")
            except Exception as e:
                logger.warning(f"Could not load CNN model: {e} — using rule-based scoring")
        else:
            logger.info("No CNN model found — using rule-based threat scoring")

        # Threat type labels
        self.THREAT_TYPES = {
            "harassment":      "Harassment / Threat",
            "physical":        "Physical Assault",
            "indecent":        "Indecent Behavior",
            "crowd_surround":  "Surrounded / Cornered",
            "distress":        "Person in Distress",
            "normal":          "Normal Activity",
        }

    def classify(self, frame, detections, pose_result):
        """
        Main classification function.

        Args:
            frame       : numpy array (BGR image)
            detections  : list from PersonDetector.detect()
            pose_result : dict from PoseEstimator.estimate()

        Returns:
            {
                "threat_score":  float (0.0 to 1.0),
                "threat_type":   str,
                "woman_present": bool,
                "person_count":  int,
            }
        """
        if self.model_available:
            cnn_result = self._classify_cnn(frame)
            # Blend CNN result with rule-based for robustness
            rule_result = self._classify_rules(detections, pose_result)
            blended_score = 0.6 * cnn_result["threat_score"] + 0.4 * rule_result["threat_score"]
            return {
                "threat_score":  round(min(blended_score, 1.0), 3),
                "threat_type":   cnn_result["threat_type"] if blended_score > 0.5 else rule_result["threat_type"],
                "woman_present": rule_result["woman_present"],
                "person_count":  rule_result["person_count"],
            }
        else:
            return self._classify_rules(detections, pose_result)

    def _classify_rules(self, detections, pose_result):
        """
        Rule-based threat scoring system.
        Each signal adds points to the threat score.
        """
        score        = 0.0
        threat_type  = "Normal Activity"
        person_count = len(detections)

        # ── Signal 1: Dangerous crowd ratio ───────────────
        # 1 woman surrounded by 3+ men → suspicious
        if person_count >= 4:
            score += 0.30
            threat_type = self.THREAT_TYPES["crowd_surround"]
        elif person_count >= 2:
            score += 0.10

        # ── Signal 2: Threatening pose detected ───────────
        if pose_result.get("threat_pose"):
            score += 0.35
            threat_type = self.THREAT_TYPES["harassment"]

        # ── Signal 3: Raised hand (about to strike) ───────
        if pose_result.get("raised_hand"):
            score += 0.25
            threat_type = self.THREAT_TYPES["physical"]

        # ── Signal 4: Distress / cowering pose ────────────
        if pose_result.get("distress_pose"):
            score += 0.20
            threat_type = self.THREAT_TYPES["distress"]

        # ── Signal 5: Crouching (hiding/being pushed) ─────
        if pose_result.get("crouching"):
            score += 0.15

        # ── Signal 6: Multiple people in close proximity ──
        if person_count >= 2:
            proximity_score = self._check_proximity(detections)
            score += proximity_score
            if proximity_score > 0.2:
                threat_type = self.THREAT_TYPES["harassment"]

        # ── Woman present heuristic ────────────────────────
        woman_present = person_count >= 1

        return {
            "threat_score":  round(min(score, 1.0), 3),
            "threat_type":   threat_type,
            "woman_present": woman_present,
            "person_count":  person_count,
        }

    def _check_proximity(self, detections):
        """
        Check if people are dangerously close to each other.
        Returns a score contribution (0.0 – 0.25).
        """
        if len(detections) < 2:
            return 0.0

        centers = []
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            centers.append((cx, cy))

        min_dist = float("inf")
        for i in range(len(centers)):
            for j in range(i + 1, len(centers)):
                dx = centers[i][0] - centers[j][0]
                dy = centers[i][1] - centers[j][1]
                dist = (dx**2 + dy**2) ** 0.5
                min_dist = min(min_dist, dist)

        # If centers are very close (< 80px) → potential physical contact
        if min_dist < 80:
            return 0.25
        elif min_dist < 150:
            return 0.12
        return 0.0

    def _classify_cnn(self, frame):
        """
        Use trained CNN model to classify the scene.
        Classes: 0=Normal, 1=Harassment, 2=Physical, 3=Indecent, 4=Distress
        """
        try:
            img = cv2.resize(frame, self.IMG_SIZE)
            img = img.astype("float32") / 255.0
            img = np.expand_dims(img, axis=0)   # (1, 224, 224, 3)

            predictions = self.model.predict(img, verbose=0)[0]
            class_idx   = int(np.argmax(predictions))
            confidence  = float(predictions[class_idx])

            class_map = {
                0: ("Normal Activity",            0.0),
                1: ("Harassment / Threat",         confidence),
                2: ("Physical Assault",            confidence),
                3: ("Indecent Behavior",           confidence),
                4: ("Person in Distress",          confidence),
            }

            threat_type, threat_score = class_map.get(class_idx, ("Normal Activity", 0.0))
            return {
                "threat_score": round(threat_score, 3),
                "threat_type":  threat_type,
            }
        except Exception as e:
            logger.error(f"CNN inference failed: {e}")
            return {"threat_score": 0.0, "threat_type": "Normal Activity"}
