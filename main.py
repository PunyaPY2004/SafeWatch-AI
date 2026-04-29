"""
SafeWatch AI — Main Entry Point
================================
An AI-Based Smart Surveillance System for Women Safety
and Public Decency Enforcement in Urban Spaces

Run this file to start the entire system.
Usage: python main.py
"""

import threading
import time
import os
from camera.capture import CameraCapture
from detection.person_detector import PersonDetector
from detection.pose_estimator import PoseEstimator
from detection.threat_classifier import ThreatClassifier
from alert.alert_manager import AlertManager
from elevator.warning_system import ElevatorWarningSystem
from database.db_manager import DatabaseManager
from dashboard.app import create_app
from utils.logger import setup_logger

logger = setup_logger("SafeWatch-AI")

def run_dashboard(app):
    """Run Flask dashboard in a separate thread."""
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

def main():
    print("""
╔══════════════════════════════════════════════════════╗
║           SafeWatch AI — Starting System             ║
║   AI-Based Women Safety Surveillance System          ║
╚══════════════════════════════════════════════════════╝
    """)

    # ── Initialize all components ──────────────────────────
    logger.info("Initializing database...")
    db = DatabaseManager()
    db.init_db()

    logger.info("Loading AI models...")
    person_detector  = PersonDetector()
    pose_estimator   = PoseEstimator()
    threat_classifier = ThreatClassifier()

    logger.info("Setting up alert system...")
    alert_manager = AlertManager(db)

    logger.info("Setting up elevator warning system...")
    elevator_system = ElevatorWarningSystem()

    # ── Start Flask dashboard in background thread ─────────
    logger.info("Starting web dashboard at http://localhost:5000 ...")
    app = create_app(db)
    dashboard_thread = threading.Thread(target=run_dashboard, args=(app,), daemon=True)
    dashboard_thread.start()

    # ── Camera sources config ──────────────────────────────
    # Add your camera sources here:
    # 0 = laptop webcam
    # "rtsp://ip:port/stream" = IP camera
    # "path/to/video.mp4" = test with video file
    CAMERA_SOURCES = {
        "CAM_01": {"source": 0,          "location": "Main Entrance"},
        # "CAM_02": {"source": "rtsp://...", "location": "Elevator 1"},
        # "CAM_03": {"source": "rtsp://...", "location": "Park Gate"},
    }

    # ── Start camera threads ───────────────────────────────
    camera_threads = []
    for cam_id, config in CAMERA_SOURCES.items():
        cam = CameraCapture(
            camera_id      = cam_id,
            source         = config["source"],
            location       = config["location"],
            person_detector = person_detector,
            pose_estimator  = pose_estimator,
            threat_classifier = threat_classifier,
            alert_manager   = alert_manager,
            elevator_system = elevator_system,
            db              = db,
        )
        t = threading.Thread(target=cam.run, daemon=True)
        t.start()
        camera_threads.append(t)
        logger.info(f"Started camera: {cam_id} — {config['location']}")

    logger.info("✅ SafeWatch AI is running! Open http://localhost:5000 in your browser.")
    logger.info("Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down SafeWatch AI...")
        print("\n👋 SafeWatch AI stopped.")

if __name__ == "__main__":
    main()
