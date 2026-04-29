"""
detection/pose_estimator.py
============================
Uses MediaPipe to estimate body pose and detect
threatening or distress body language.
"""

import cv2
import numpy as np
from utils.logger import setup_logger

logger = setup_logger("PoseEstimator")

# MediaPipe landmark indices (body keypoints)
# Reference: https://google.github.io/mediapipe/solutions/pose.html
NOSE           = 0
LEFT_SHOULDER  = 11
RIGHT_SHOULDER = 12
LEFT_ELBOW     = 13
RIGHT_ELBOW    = 14
LEFT_WRIST     = 15
RIGHT_WRIST    = 16
LEFT_HIP       = 23
RIGHT_HIP      = 24
LEFT_KNEE      = 25
RIGHT_KNEE     = 26


class PoseEstimator:
    def __init__(self):
        try:
            import mediapipe as mp
            self.mp_pose   = mp.solutions.pose
            self.mp_draw   = mp.solutions.drawing_utils
            self.pose      = self.mp_pose.Pose(
                static_image_mode      = False,
                model_complexity       = 1,       # 0=lite, 1=full, 2=heavy
                min_detection_confidence = 0.5,
                min_tracking_confidence  = 0.5,
            )
            self.available = True
            logger.info("✅ MediaPipe Pose loaded")
        except ImportError:
            logger.warning("mediapipe not installed — pose estimation disabled")
            self.available = False

    def estimate(self, frame):
        """
        Run pose estimation on a frame.

        Returns:
          {
            "threat_pose":        bool,
            "distress_pose":      bool,
            "raised_hand":        bool,
            "crouching":          bool,
            "pose_description":   str,
            "landmarks":          list or None,
          }
        """
        result = {
            "threat_pose":      False,
            "distress_pose":    False,
            "raised_hand":      False,
            "crouching":        False,
            "pose_description": "Normal",
            "landmarks":        None,
        }

        if not self.available:
            return result

        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        out   = self.pose.process(rgb)

        if not out.pose_landmarks:
            return result

        lm = out.pose_landmarks.landmark
        result["landmarks"] = lm

        # ── Raised hand / arm raised above head ───────────
        nose_y = lm[NOSE].y
        lw_y   = lm[LEFT_WRIST].y
        rw_y   = lm[RIGHT_WRIST].y

        if lw_y < nose_y or rw_y < nose_y:
            result["raised_hand"]      = True
            result["threat_pose"]      = True
            result["pose_description"] = "Raised Hand / Threatening Gesture"

        # ── Crouching / cowering (distress) ───────────────
        ls_y  = lm[LEFT_SHOULDER].y
        rs_y  = lm[RIGHT_SHOULDER].y
        lh_y  = lm[LEFT_HIP].y
        rh_y  = lm[RIGHT_HIP].y

        shoulder_avg = (ls_y + rs_y) / 2
        hip_avg      = (lh_y + rh_y) / 2
        torso_height = abs(hip_avg - shoulder_avg)

        if torso_height < 0.12:   # Shoulders and hips very close → crouching
            result["crouching"]        = True
            result["distress_pose"]    = True
            result["pose_description"] = "Crouching / Cowering (Distress)"

        # ── Arms spread wide (blocking / threatening) ─────
        lw_x  = lm[LEFT_WRIST].x
        rw_x  = lm[RIGHT_WRIST].x
        arm_span = abs(lw_x - rw_x)

        if arm_span > 0.6:
            result["threat_pose"]      = True
            result["pose_description"] = "Wide Arm Spread (Blocking/Threatening)"

        # ── Leaning / falling sideways ────────────────────
        ls_x  = lm[LEFT_SHOULDER].x
        rs_x  = lm[RIGHT_SHOULDER].x
        lh_x  = lm[LEFT_HIP].x
        rh_x  = lm[RIGHT_HIP].x

        shoulder_mid_x = (ls_x + rs_x) / 2
        hip_mid_x      = (lh_x + rh_x) / 2
        lean_offset    = abs(shoulder_mid_x - hip_mid_x)

        if lean_offset > 0.15:
            result["distress_pose"]    = True
            if not result["threat_pose"]:
                result["pose_description"] = "Leaning / Falling Sideways"

        return result

    def draw_pose(self, frame, landmarks):
        """Draw skeleton on frame for visualization."""
        if not self.available or landmarks is None:
            return frame
        import mediapipe as mp
        mp_draw = mp.solutions.drawing_utils
        mp_pose = mp.solutions.pose
        # landmarks here is a NormalizedLandmarkList
        # Re-process to draw — store raw result for real use
        return frame
