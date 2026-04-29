"""
SafeWatch AI — Elevator Warning System
Triggers in-elevator deterrent warnings when misconduct is detected
"""

import time
import threading
from datetime import datetime

# Try importing Raspberry Pi GPIO (only works on Pi hardware)
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO_AVAILABLE = False

# GPIO pin config (Raspberry Pi)
BUZZER_PIN  = 18   # GPIO pin connected to buzzer
DISPLAY_PIN = 23   # GPIO pin connected to LED/display relay


class ElevatorWarningSystem:
    def __init__(self):
        self._active_warnings = {}   # cam_id → timestamp
        self._warning_duration = 5   # seconds
        self._cooldown         = 30  # seconds between warnings

        if GPIO_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(BUZZER_PIN, GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(DISPLAY_PIN, GPIO.OUT, initial=GPIO.LOW)
            print("✅ Raspberry Pi GPIO initialized for elevator warning")
        else:
            print("ℹ️  GPIO not available — elevator warnings will print to console")

    def trigger_warning(self, cam_id):
        """Trigger warning for a specific elevator camera."""
        now = time.time()

        # Cooldown check
        if cam_id in self._active_warnings:
            if now - self._active_warnings[cam_id] < self._cooldown:
                return  # Still in cooldown

        self._active_warnings[cam_id] = now
        print(f"\n🔊 ELEVATOR WARNING TRIGGERED — {cam_id} at {datetime.now().strftime('%H:%M:%S')}")
        print("   ⚠️  WARNING: You are being monitored. Inappropriate behavior detected.")

        # Run warning in background thread
        t = threading.Thread(target=self._activate_hardware, daemon=True)
        t.start()

    def _activate_hardware(self):
        """Activate physical hardware (buzzer + display)."""
        if GPIO_AVAILABLE:
            # Beep pattern: 3 short beeps
            for _ in range(3):
                GPIO.output(BUZZER_PIN, GPIO.HIGH)
                time.sleep(0.3)
                GPIO.output(BUZZER_PIN, GPIO.LOW)
                time.sleep(0.2)

            # Activate warning display relay
            GPIO.output(DISPLAY_PIN, GPIO.HIGH)
            time.sleep(self._warning_duration)
            GPIO.output(DISPLAY_PIN, GPIO.LOW)
        else:
            # Software-only: log the warning
            print("   🔔 BEEP BEEP BEEP — Warning signal activated!")
            time.sleep(self._warning_duration)
            print("   ✅ Warning signal deactivated")

    def cleanup(self):
        if GPIO_AVAILABLE:
            GPIO.cleanup()
