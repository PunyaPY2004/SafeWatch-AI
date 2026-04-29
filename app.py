"""
SafeWatch AI — Main Flask Application
Women Safety & Public Decency Enforcement System
"""

from flask import Flask, render_template, Response, jsonify, request, redirect, url_for
from flask_socketio import SocketIO, emit
import cv2
import threading
import time
import base64
import os
from datetime import datetime

from detection.threat_detector import ThreatDetector
from alert.alert_system import AlertSystem
from database.db_manager import DatabaseManager
from elevator.warning_system import ElevatorWarningSystem

# ── App Setup ──────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = 'safewatch-ai-secret-2025'
app.config['UPLOAD_FOLDER'] = 'uploads/snapshots'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ── Global Objects ─────────────────────────────────────────
detector     = ThreatDetector()
alert_sys    = AlertSystem()
db           = DatabaseManager()
elevator_sys = ElevatorWarningSystem()

# Camera feeds: {cam_id: {"cap": cv2.VideoCapture, "location": str, "active": bool}}
cameras      = {}
camera_lock  = threading.Lock()
latest_frames= {}   # cam_id → jpeg bytes
monitoring   = False

# ── Camera Management ──────────────────────────────────────
def add_camera(cam_id, source, location):
    """source = 0 (webcam) or 'rtsp://...' (IP cam)"""
    try:
        cap = cv2.VideoCapture(source)
        if cap.isOpened():
            with camera_lock:
                cameras[cam_id] = {
                    "cap": cap,
                    "location": location,
                    "source": source,
                    "active": True,
                    "type": "elevator" if "lift" in location.lower() or "elevator" in location.lower() else "public"
                }
            return True
    except Exception as e:
        print(f"Camera error: {e}")
    return False

def process_camera(cam_id):
    """Background thread: reads frames, runs AI, emits alerts."""
    while True:
        with camera_lock:
            cam = cameras.get(cam_id)
            if not cam or not cam["active"]:
                break

        cap = cam["cap"]
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue

        # Resize for speed
        frame = cv2.resize(frame, (640, 480))

        # ── Run AI Detection ──
        result = detector.analyze_frame(frame, cam["location"])

        # ── Draw overlays ──
        annotated = detector.draw_annotations(frame.copy(), result)

        # Add camera label
        cv2.putText(annotated, f"CAM: {cam_id} | {cam['location']}",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Threat level badge
        color = (0, 255, 0)
        if result["threat_level"] == "SUSPICIOUS":
            color = (0, 165, 255)
        elif result["threat_level"] == "THREAT":
            color = (0, 0, 255)

        cv2.rectangle(annotated, (10, 35), (300, 65), color, -1)
        cv2.putText(annotated, f"STATUS: {result['threat_level']} ({result['score']:.0f}%)",
                    (15, 57), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # ── Store frame ──
        _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 75])
        latest_frames[cam_id] = buffer.tobytes()

        # ── Handle Threats ──
        if result["threat_level"] in ("SUSPICIOUS", "THREAT") and monitoring:
            snapshot_path = save_snapshot(frame, cam_id, result)

            # Log to database
            incident_id = db.log_incident(
                camera_id=cam_id,
                location=cam["location"],
                threat_type=result["threat_type"],
                confidence=result["score"],
                snapshot_path=snapshot_path
            )

            # Real-time alert via WebSocket
            socketio.emit('alert', {
                'cam_id': cam_id,
                'location': cam['location'],
                'threat_type': result['threat_type'],
                'score': result['score'],
                'level': result['threat_level'],
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'snapshot': frame_to_b64(frame),
                'incident_id': incident_id
            })

            # Elevator-specific warning
            if cam["type"] == "elevator" and result["threat_level"] == "THREAT":
                elevator_sys.trigger_warning(cam_id)

            # Send SMS/Email for high threats
            if result["threat_level"] == "THREAT":
                alert_sys.send_alert(
                    location=cam["location"],
                    threat_type=result["threat_type"],
                    snapshot_path=snapshot_path
                )

        time.sleep(0.05)  # ~20 FPS

def save_snapshot(frame, cam_id, result):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"snap_{cam_id}_{ts}.jpg"
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    cv2.imwrite(path, frame)
    return path

def frame_to_b64(frame):
    _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode()

# ── Routes ─────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    stats = db.get_stats()
    recent = db.get_recent_incidents(10)
    cam_list = [{"id": k, "location": v["location"], "type": v["type"], "active": v["active"]}
                for k, v in cameras.items()]
    return render_template('dashboard.html', stats=stats, incidents=recent, cameras=cam_list)

@app.route('/incidents')
def incidents():
    all_inc = db.get_all_incidents()
    return render_template('incidents.html', incidents=all_inc)

@app.route('/live')
def live():
    cam_list = [{"id": k, "location": v["location"]} for k, v in cameras.items()]
    return render_template('live.html', cameras=cam_list)

@app.route('/video_feed/<cam_id>')
def video_feed(cam_id):
    def gen():
        while True:
            frame = latest_frames.get(cam_id)
            if frame:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.05)
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/add_camera', methods=['POST'])
def api_add_camera():
    data = request.json
    cam_id   = data.get('cam_id', f'CAM_{len(cameras)+1:02d}')
    source   = data.get('source', 0)
    location = data.get('location', 'Unknown Location')

    # Convert source to int if webcam index
    try:
        source = int(source)
    except:
        pass

    ok = add_camera(cam_id, source, location)
    if ok:
        t = threading.Thread(target=process_camera, args=(cam_id,), daemon=True)
        t.start()
        return jsonify({"status": "ok", "cam_id": cam_id})
    return jsonify({"status": "error", "message": "Could not open camera"}), 400

@app.route('/api/remove_camera/<cam_id>', methods=['DELETE'])
def api_remove_camera(cam_id):
    with camera_lock:
        cam = cameras.get(cam_id)
        if cam:
            cam["active"] = False
            cam["cap"].release()
            del cameras[cam_id]
            latest_frames.pop(cam_id, None)
    return jsonify({"status": "ok"})

@app.route('/api/toggle_monitoring', methods=['POST'])
def api_toggle_monitoring():
    global monitoring
    monitoring = not monitoring
    socketio.emit('monitoring_status', {'active': monitoring})
    return jsonify({"monitoring": monitoring})

@app.route('/api/incidents')
def api_incidents():
    inc = db.get_all_incidents()
    return jsonify(inc)

@app.route('/api/resolve/<int:inc_id>', methods=['POST'])
def api_resolve(inc_id):
    db.resolve_incident(inc_id)
    return jsonify({"status": "resolved"})

@app.route('/api/stats')
def api_stats():
    return jsonify(db.get_stats())

@app.route('/api/test_alert', methods=['POST'])
def api_test_alert():
    socketio.emit('alert', {
        'cam_id': 'TEST',
        'location': 'Test Location',
        'threat_type': 'Test Alert',
        'score': 95,
        'level': 'THREAT',
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'snapshot': '',
        'incident_id': 0
    })
    return jsonify({"status": "test alert sent"})

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/api/save_settings', methods=['POST'])
def api_save_settings():
    data = request.json
    alert_sys.update_settings(data)
    return jsonify({"status": "saved"})

# ── WebSocket Events ───────────────────────────────────────
@socketio.on('connect')
def on_connect():
    emit('monitoring_status', {'active': monitoring})
    emit('camera_list', [{"id": k, "location": v["location"]}
                         for k, v in cameras.items()])

@socketio.on('request_stats')
def on_stats():
    emit('stats_update', db.get_stats())

# ── Start ──────────────────────────────────────────────────
if __name__ == '__main__':
    os.makedirs('uploads/snapshots', exist_ok=True)

    # Auto-add demo webcam (camera index 0)
    print("🚀 SafeWatch AI starting...")
    print("📷 Adding default webcam...")
    ok = add_camera("CAM_01", 0, "Main Entrance")
    if ok:
        t = threading.Thread(target=process_camera, args=("CAM_01",), daemon=True)
        t.start()
        monitoring = True
        print("✅ Camera started")
    else:
        print("⚠️  No webcam found — you can add cameras from the dashboard")

    print("🌐 Open browser: http://127.0.0.1:5000")
    socketio.run(app, debug=False, host='0.0.0.0', port=5000)
