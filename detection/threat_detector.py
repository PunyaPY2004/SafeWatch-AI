"""
SafeWatch AI — Threat Detection Engine
Uses YOLO v8 for person detection + MediaPipe for pose analysis
+ rule-based threat scoring
"""

import cv2
import numpy as np
import time

# Try importing heavy libraries — fall back to demo mode if not installed
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("⚠️  YOLO not installed — using demo mode (pip install ultralytics)")

try:
    import mediapipe as mp
    MP_AVAILABLE = True
except ImportError:
    MP_AVAILABLE = False
    print("⚠️  MediaPipe not installed — pose detection disabled (pip install mediapipe)")


class ThreatDetector:
    def __init__(self):
        print("🧠 Loading AI models...")

        # YOLO Person Detector
        self.yolo = None
        if YOLO_AVAILABLE:
            try:
                self.yolo = YOLO('yolov8n.pt')  # Downloads automatically first time
                print("✅ YOLO v8 loaded")
            except Exception as e:
                print(f"⚠️  YOLO load error: {e}")

        # MediaPipe Pose
        self.pose = None
        self.mp_pose = None
        self.mp_draw = None
        if MP_AVAILABLE:
            try:
                mp_lib = mp.solutions.pose
                self.pose = mp_lib.Pose(
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
                self.mp_pose = mp_lib
                self.mp_draw = mp.solutions.drawing_utils
                print("✅ MediaPipe Pose loaded")
            except Exception as e:
                print(f"⚠️  MediaPipe error: {e}")

        # Track recent alerts to avoid spam
        self._last_alert = {}   # cam_id → timestamp
        self._alert_cooldown = 10  # seconds between alerts per camera

        # Demo mode: simulate detections if no camera/models
        self._demo_tick = 0

        print("✅ Threat Detector ready")

    # ── Main Analysis Function ─────────────────────────────
    def analyze_frame(self, frame, location="Unknown"):
        """
        Analyzes one video frame.
        Returns dict with:
          - people_count, women_detected, men_count
          - pose_flags: list of pose warning labels
          - threat_type: string describing what was detected
          - score: 0–100 confidence
          - threat_level: "NORMAL" / "SUSPICIOUS" / "THREAT"
        """
        result = {
            "people_count": 0,
            "women_detected": False,
            "men_count": 0,
            "pose_flags": [],
            "threat_type": "Normal",
            "score": 0.0,
            "threat_level": "NORMAL",
            "boxes": [],
            "landmarks": None
        }

        h, w = frame.shape[:2]

        # ── Step 1: Person Detection via YOLO ──────────────
        if self.yolo:
            try:
                yolo_results = self.yolo(frame, verbose=False, classes=[0])  # class 0 = person
                boxes = yolo_results[0].boxes
                result["people_count"] = len(boxes)
                result["boxes"] = [(int(b.xyxy[0][0]), int(b.xyxy[0][1]),
                                    int(b.xyxy[0][2]), int(b.xyxy[0][3]),
                                    float(b.conf[0])) for b in boxes]
            except Exception as e:
                pass
        else:
            # Demo: use basic motion/contour detection as fallback
            result = self._demo_detect(frame, result)

        # ── Step 2: Pose Analysis via MediaPipe ────────────
        if self.pose and result["people_count"] > 0:
            try:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pose_result = self.pose.process(rgb)
                if pose_result.pose_landmarks:
                    result["landmarks"] = pose_result.pose_landmarks
                    flags = self._analyze_pose(pose_result.pose_landmarks, h, w)
                    result["pose_flags"].extend(flags)
            except Exception as e:
                pass

        # ── Step 3: Scene-level Rules ──────────────────────
        scene_flags = self._scene_rules(result, location)
        result["pose_flags"].extend(scene_flags)

        # ── Step 4: Threat Scoring ─────────────────────────
        result = self._score_threat(result)

        return result

    # ── Pose Analysis ──────────────────────────────────────
    def _analyze_pose(self, landmarks, h, w):
        """Analyze body keypoints for threatening gestures."""
        flags = []
        lm = landmarks.landmark
        mp_lm = self.mp_pose.PoseLandmark

        try:
            # Get key joint positions (normalized 0–1)
            nose       = lm[mp_lm.NOSE]
            l_shoulder = lm[mp_lm.LEFT_SHOULDER]
            r_shoulder = lm[mp_lm.RIGHT_SHOULDER]
            l_elbow    = lm[mp_lm.LEFT_ELBOW]
            r_elbow    = lm[mp_lm.RIGHT_ELBOW]
            l_wrist    = lm[mp_lm.LEFT_WRIST]
            r_wrist    = lm[mp_lm.RIGHT_WRIST]
            l_hip      = lm[mp_lm.LEFT_HIP]
            r_hip      = lm[mp_lm.RIGHT_HIP]
            l_knee     = lm[mp_lm.LEFT_KNEE]
            r_knee     = lm[mp_lm.RIGHT_KNEE]

            shoulder_y = (l_shoulder.y + r_shoulder.y) / 2
            hip_y      = (l_hip.y + r_hip.y) / 2
            wrist_l_y  = l_wrist.y
            wrist_r_y  = r_wrist.y

            # ── Raised hands / striking pose ──────────────
            # Wrist above shoulder → raised hand → possible threat
            if wrist_l_y < (l_shoulder.y - 0.1) or wrist_r_y < (r_shoulder.y - 0.1):
                flags.append("RAISED_HAND")

            # ── Both hands raised ──────────────────────────
            if wrist_l_y < shoulder_y - 0.05 and wrist_r_y < shoulder_y - 0.05:
                flags.append("BOTH_HANDS_RAISED")

            # ── Crouching / fallen person ──────────────────
            body_height = abs(nose.y - hip_y)
            if body_height < 0.2:
                flags.append("PERSON_DOWN")

            # ── Reaching forward aggressively ─────────────
            l_reach = abs(l_wrist.x - l_shoulder.x)
            r_reach = abs(r_wrist.x - r_shoulder.x)
            if l_reach > 0.25 or r_reach > 0.25:
                flags.append("AGGRESSIVE_REACH")

            # ── Arms spread wide (confrontational) ────────
            arm_span = abs(l_wrist.x - r_wrist.x)
            if arm_span > 0.5:
                flags.append("ARMS_SPREAD")

            # ── Cowering / bent over (distress) ───────────
            if nose.y > l_shoulder.y + 0.1:
                flags.append("COWERING_POSTURE")

        except Exception as e:
            pass

        return flags

    # ── Scene-level Rules ──────────────────────────────────
    def _scene_rules(self, result, location):
        """Higher-level rules based on crowd composition & location."""
        flags = []
        pc = result["people_count"]

        # Crowd ratio: many people, isolated situation
        if pc >= 3:
            flags.append("CROWD_PRESENT")
        if pc >= 5:
            flags.append("LARGE_CROWD")

        # Elevator-specific: any person + aggressive pose = higher risk
        loc_lower = location.lower()
        if ("lift" in loc_lower or "elevator" in loc_lower) and pc >= 2:
            flags.append("ELEVATOR_MULTIPLE_PERSONS")

        # Night / low-light detection
        # (would need timestamp check — simplified here)

        return flags

    # ── Threat Scoring ─────────────────────────────────────
    def _score_threat(self, result):
        """Convert flags into a threat score and level."""
        score = 0.0
        threat_type = "Normal"

        flag_weights = {
            "RAISED_HAND":               30,
            "BOTH_HANDS_RAISED":         45,
            "PERSON_DOWN":               55,
            "AGGRESSIVE_REACH":          25,
            "ARMS_SPREAD":               15,
            "COWERING_POSTURE":          40,
            "CROWD_PRESENT":             10,
            "LARGE_CROWD":               20,
            "ELEVATOR_MULTIPLE_PERSONS": 25,
        }

        threat_names = {
            "RAISED_HAND":               "Raised Hand / Potential Strike",
            "BOTH_HANDS_RAISED":         "Both Hands Raised — Confrontation",
            "PERSON_DOWN":               "Person on Ground — Possible Assault",
            "AGGRESSIVE_REACH":          "Aggressive Reaching Gesture",
            "COWERING_POSTURE":          "Person Cowering — Possible Distress",
            "ELEVATOR_MULTIPLE_PERSONS": "Multiple Persons in Elevator",
        }

        active_flags = result["pose_flags"]
        for flag in active_flags:
            score += flag_weights.get(flag, 5)
            if flag in threat_names:
                threat_type = threat_names[flag]

        # Cap at 100
        score = min(score, 100.0)

        # Determine level
        if score >= 65:
            level = "THREAT"
        elif score >= 35:
            level = "SUSPICIOUS"
        else:
            level = "NORMAL"
            threat_type = "Normal"

        result["score"] = score
        result["threat_level"] = level
        result["threat_type"] = threat_type
        return result

    # ── Draw Annotations ──────────────────────────────────
    def draw_annotations(self, frame, result):
        """Draw bounding boxes, skeleton, and labels on frame."""

        # Draw YOLO bounding boxes
        for (x1, y1, x2, y2, conf) in result.get("boxes", []):
            color = (0, 255, 0)
            if result["threat_level"] == "SUSPICIOUS":
                color = (0, 165, 255)
            elif result["threat_level"] == "THREAT":
                color = (0, 0, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"Person {conf:.2f}",
                        (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # Draw pose skeleton
        if self.mp_draw and result.get("landmarks"):
            self.mp_draw.draw_landmarks(
                frame,
                result["landmarks"],
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_draw.DrawingSpec(color=(0, 255, 255), thickness=2),
                connection_drawing_spec=self.mp_draw.DrawingSpec(color=(255, 255, 0), thickness=2)
            )

        # Draw active pose flags
        for i, flag in enumerate(result["pose_flags"][:4]):
            cv2.putText(frame, f"⚑ {flag}",
                        (10, 90 + i * 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        return frame

    # ── Demo Mode ─────────────────────────────────────────
    def _demo_detect(self, frame, result):
        """Simulates detection when no models are available."""
        self._demo_tick += 1
        # Simulate a normal period then a brief suspicious event
        cycle = self._demo_tick % 200
        if 80 <= cycle < 100:
            result["people_count"] = 3
            result["pose_flags"] = ["RAISED_HAND", "CROWD_PRESENT"]
        elif 100 <= cycle < 110:
            result["people_count"] = 2
            result["pose_flags"] = ["COWERING_POSTURE", "AGGRESSIVE_REACH"]
        elif cycle < 80 or cycle >= 110:
            result["people_count"] = 1
        return result
