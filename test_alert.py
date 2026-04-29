import sys, os
sys.path.insert(0, '.')
from database.db_manager import DatabaseManager
from alert.alert_manager import AlertManager
import time

db = DatabaseManager()
alert = AlertManager(db)

print("Sending test alert...")
alert.send_alert(
    camera_id     = "CAM_01",
    location      = "Main Entrance - Test",
    threat_type   = "Harassment / Threat",
    threat_score  = 0.87,
    snapshot_path = None
)
print("Done! Now check:")
print("  1. Dashboard at http://localhost:5000")
print("  2. Your email inbox")