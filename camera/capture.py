"""
camera/capture.py
==================
Captures live frames from CCTV cameras and runs
the full detection pipeline on each frame.
"""

import cv2
import time
import os
import numpy as np
from utils.logger import setup_logger

logger = setup_logger("Camera")

# Threat score threshold to trigger alert
ALERT_THRESHOLD = 0.70  # 70% confidence = send alert
SUSPICIOUS_THRESHOLD = 0.40  # 40% = log and monitor

# How many seconds between repeat alerts (avoid spam)
ALERT_COOLDOWN_SECONDS = 30


class CameraCapture:
    def __init__(self, camera_id, source, location,
                 person_detector, pose_estimator, threat_classifier,
                 alert_manager, elevator_system, db):

        self.camera_id         = camera_id
        self.source            = source
        self.location          = location
        self.person_detector   = person_detector
        self.pose_estimator    = pose_estimator
        self.threat_classifier = threat_classifier
        self.alert_manager     = alert_manager
        self.elevator_system   = elevator_system
        self.db                = db

        self.last_alert_time   = 0
        self.frame_count       = 0
        self.is_elevator       = "lift" in location.lower() or "elevator" in location.lower()

        # Ensure snapshots folder exists
        os.makedirs("snapshots", exist_ok=True)

    def run(self):
        """Main loop — reads frames and runs detection pipeline."""
        cap = cv2.VideoCapture(self.source)

        if not cap.isOpened():
            logger.error(f"[{self.camera_id}] Cannot open camera source: {self.source}")
            return

        logger.info(f"[{self.camera_id}] Camera started at: {self.location}")

        while True:
            ret, frame = cap.read()
            if not ret:
                logger.warning(f"[{self.camera_id}] Frame read failed — retrying...")
                time.sleep(1)
                cap = cv2.VideoCapture(self.source)
                continue

            self.frame_count += 1

            # Process every 3rd frame to reduce CPU load
            if self.frame_count % 3 != 0:
                continue

            try:
                self._process_frame(frame)
            except Exception as e:
                logger.error(f"[{self.camera_id}] Error processing frame: {e}")

        cap.release()

    def _process_frame(self, frame):
        """Run full AI pipeline on one frame."""

        # ── Step 1: Detect persons ─────────────────────────
        detections = self.person_detector.detect(frame)
        # detections = list of {"bbox": [x1,y1,x2,y2], "class": "person"/"woman"/"man", "confidence": float}

        if not detections:
            return  # No people — nothing to analyse

        # ── Step 2: Pose estimation ────────────────────────
        pose_result = self.pose_estimator.estimate(frame)
        # pose_result = {"threat_pose": bool, "pose_description": str}

        # ── Step 3: Threat classification ─────────────────
        threat_result = self.threat_classifier.classify(frame, detections, pose_result)
        # threat_result = {"threat_score": float, "threat_type": str, "woman_present": bool}

        threat_score = threat_result["threat_score"]
        threat_type  = threat_result["threat_type"]
        woman_present = threat_result["woman_present"]

        # ── Step 4: Log suspicious activity ───────────────
        if threat_score >= SUSPICIOUS_THRESHOLD:
            self.db.log_incident(
                camera_id     = self.camera_id,
                location      = self.location,
                threat_type   = threat_type,
                threat_score  = threat_score,
                woman_present = woman_present,
                status        = "Monitoring" if threat_score < ALERT_THRESHOLD else "Alert Sent"
            )

        # ── Step 5: Trigger alert if threshold exceeded ────
        now = time.time()
        cooldown_ok = (now - self.last_alert_time) > ALERT_COOLDOWN_SECONDS

        if threat_score >= ALERT_THRESHOLD and cooldown_ok:
            # Save snapshot of the incident
            snapshot_path = self._save_snapshot(frame, threat_type)

            # Send alert to control room
            self.alert_manager.send_alert(
                camera_id     = self.camera_id,
                location      = self.location,
                threat_type   = threat_type,
                threat_score  = threat_score,
                snapshot_path = snapshot_path,
            )

            # If this is an elevator camera — trigger in-elevator warning
            if self.is_elevator:
                self.elevator_system.trigger_warning(
                    camera_id = self.camera_id,
                    location  = self.location,
                    threat_type = threat_type,
                )

            self.last_alert_time = now
            logger.warning(
                f"[{self.camera_id}] 🚨 ALERT! {threat_type} at {self.location} "
                f"(Score: {threat_score:.0%})"
            )

    def _save_snapshot(self, frame, threat_type):
        """Save a snapshot image of the incident."""
        timestamp   = time.strftime("%Y%m%d_%H%M%S")
        safe_type   = threat_type.replace(" ", "_")
        filename    = f"snapshots/{self.camera_id}_{safe_type}_{timestamp}.jpg"
        cv2.imwrite(filename, frame)
        logger.info(f"[{self.camera_id}] Snapshot saved: {filename}")
        return filename
