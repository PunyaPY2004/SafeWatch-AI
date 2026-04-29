"""
test_system.py
================
Quick test script to verify all components work.
Run this before running main.py

Usage: python test_system.py
"""

import sys

print("=" * 55)
print("  SafeWatch AI — System Component Test")
print("=" * 55)

errors = []

# ── Test 1: OpenCV ─────────────────────────────────────────
print("\n[1/7] Testing OpenCV...")
try:
    import cv2
    print(f"  ✅ OpenCV version: {cv2.__version__}")
except ImportError:
    print("  ❌ OpenCV not found — run: pip install opencv-python")
    errors.append("opencv")

# ── Test 2: YOLO ───────────────────────────────────────────
print("\n[2/7] Testing YOLO v8...")
try:
    from ultralytics import YOLO
    model = YOLO("yolov8n.pt")
    print("  ✅ YOLOv8 loaded (model auto-downloaded if needed)")
except ImportError:
    print("  ❌ ultralytics not found — run: pip install ultralytics")
    errors.append("ultralytics")
except Exception as e:
    print(f"  ⚠️  YOLO warning: {e}")

# ── Test 3: MediaPipe ──────────────────────────────────────
print("\n[3/7] Testing MediaPipe...")
try:
    import mediapipe as mp
    pose = mp.solutions.pose.Pose()
    print(f"  ✅ MediaPipe loaded")
except ImportError:
    print("  ❌ mediapipe not found — run: pip install mediapipe")
    errors.append("mediapipe")
except Exception as e:
    print(f"  ⚠️  MediaPipe warning: {e}")

# ── Test 4: TensorFlow ─────────────────────────────────────
print("\n[4/7] Testing TensorFlow...")
try:
    import tensorflow as tf
    print(f"  ✅ TensorFlow version: {tf.__version__}")
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        print(f"  🎯 GPU detected: {gpus}")
    else:
        print("  ℹ️  No GPU — using CPU (slower training, OK for demo)")
except ImportError:
    print("  ❌ tensorflow not found — run: pip install tensorflow")
    errors.append("tensorflow")

# ── Test 5: Flask ──────────────────────────────────────────
print("\n[5/7] Testing Flask...")
try:
    import flask
    print(f"  ✅ Flask version: {flask.__version__}")
except ImportError:
    print("  ❌ flask not found — run: pip install flask")
    errors.append("flask")

# ── Test 6: Database ───────────────────────────────────────
print("\n[6/7] Testing Database...")
try:
    from database.db_manager import DatabaseManager
    db = DatabaseManager()
    db.init_db()
    # Insert test record
    db.log_incident("TEST_CAM", "Test Location", "Test Threat", 0.85, True, "Test")
    incidents = db.get_recent_incidents(limit=1)
    stats = db.get_stats()
    print(f"  ✅ Database working — {stats['total_incidents']} incidents in DB")
except Exception as e:
    print(f"  ❌ Database error: {e}")
    errors.append("database")

# ── Test 7: Camera ─────────────────────────────────────────
print("\n[7/7] Testing Camera access...")
try:
    import cv2
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        ret, frame = cap.read()
        cap.release()
        if ret:
            print(f"  ✅ Camera working — frame size: {frame.shape}")
        else:
            print("  ⚠️  Camera opened but couldn't read frame")
    else:
        print("  ⚠️  No webcam detected (OK if using IP cameras)")
except Exception as e:
    print(f"  ⚠️  Camera test: {e}")

# ── Summary ────────────────────────────────────────────────
print("\n" + "=" * 55)
if not errors:
    print("✅ ALL TESTS PASSED — Ready to run: python main.py")
else:
    print(f"❌ {len(errors)} issue(s) found: {', '.join(errors)}")
    print("   Fix the above and re-run this test.")
print("=" * 55)
