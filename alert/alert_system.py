"""
SafeWatch AI — Alert System
Sends SMS (Twilio) and Email notifications on threat detection
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime

try:
    from twilio.rest import Client as TwilioClient
    TWILIO_OK = True
except ImportError:
    TWILIO_OK = False

# ── CONFIG — Fill in your real credentials ─────────────────
CONFIG = {
    # Twilio SMS (get free at twilio.com)
    "twilio_sid":       os.getenv("TWILIO_SID",   "YOUR_TWILIO_SID"),
    "twilio_token":     os.getenv("TWILIO_TOKEN", "YOUR_TWILIO_TOKEN"),
    "twilio_from":      os.getenv("TWILIO_FROM",  "+1XXXXXXXXXX"),
    "alert_phone":      os.getenv("ALERT_PHONE",  "+91XXXXXXXXXX"),  # Control room number

    # Gmail (use App Password — not your real password!)
    "gmail_user":       os.getenv("GMAIL_USER",   "your@gmail.com"),
    "gmail_password":   os.getenv("GMAIL_PASS",   "your-app-password"),
    "alert_email":      os.getenv("ALERT_EMAIL",  "controlroom@gmail.com"),

    "sms_enabled":   False,   # Set True after adding credentials
    "email_enabled": False,   # Set True after adding credentials
}


class AlertSystem:
    def __init__(self):
        self.settings = CONFIG.copy()
        self._alert_count = 0

    def update_settings(self, new_settings):
        self.settings.update(new_settings)

    def send_alert(self, location, threat_type, snapshot_path=None):
        """Send alert via all enabled channels."""
        self._alert_count += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = (f"🚨 SAFEWATCH AI ALERT #{self._alert_count}\n"
               f"Location: {location}\n"
               f"Threat: {threat_type}\n"
               f"Time: {timestamp}\n"
               f"Action: Please dispatch security immediately!")

        print(f"\n{'='*50}")
        print(f"🚨 ALERT TRIGGERED!")
        print(msg)
        print(f"{'='*50}\n")

        if self.settings.get("sms_enabled"):
            self._send_sms(msg)
        if self.settings.get("email_enabled"):
            self._send_email(location, threat_type, timestamp, snapshot_path)

    # ── SMS via Twilio ─────────────────────────────────────
    def _send_sms(self, message):
        if not TWILIO_OK:
            print("⚠️  Twilio not installed: pip install twilio")
            return
        try:
            client = TwilioClient(
                self.settings["twilio_sid"],
                self.settings["twilio_token"]
            )
            client.messages.create(
                to=self.settings["alert_phone"],
                from_=self.settings["twilio_from"],
                body=message
            )
            print("✅ SMS sent successfully")
        except Exception as e:
            print(f"❌ SMS failed: {e}")

    # ── Email via Gmail ────────────────────────────────────
    def _send_email(self, location, threat_type, timestamp, snapshot_path=None):
        try:
            msg = MIMEMultipart()
            msg['From']    = self.settings["gmail_user"]
            msg['To']      = self.settings["alert_email"]
            msg['Subject'] = f"🚨 SafeWatch AI ALERT — {location}"

            body = f"""
            <html><body style="font-family:Arial;color:#333;">
            <h2 style="color:red;">⚠️ THREAT DETECTED — SafeWatch AI</h2>
            <table style="border-collapse:collapse;width:100%;">
              <tr><td style="padding:8px;background:#f44336;color:white;"><b>Location</b></td>
                  <td style="padding:8px;border:1px solid #ddd;">{location}</td></tr>
              <tr><td style="padding:8px;background:#f44336;color:white;"><b>Threat Type</b></td>
                  <td style="padding:8px;border:1px solid #ddd;">{threat_type}</td></tr>
              <tr><td style="padding:8px;background:#f44336;color:white;"><b>Time</b></td>
                  <td style="padding:8px;border:1px solid #ddd;">{timestamp}</td></tr>
            </table>
            <br>
            <p style="background:#fff3cd;padding:12px;border-left:4px solid #ffc107;">
            ⚡ <b>Immediate action required.</b> Please dispatch security personnel to the location.
            </p>
            <p style="font-size:12px;color:#999;">— SafeWatch AI Surveillance System</p>
            </body></html>
            """
            msg.attach(MIMEText(body, 'html'))

            # Attach snapshot if available
            if snapshot_path and os.path.exists(snapshot_path):
                with open(snapshot_path, 'rb') as f:
                    img = MIMEImage(f.read())
                    img.add_header('Content-Disposition', 'attachment',
                                   filename=os.path.basename(snapshot_path))
                    msg.attach(img)

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.settings["gmail_user"], self.settings["gmail_password"])
            server.sendmail(self.settings["gmail_user"],
                            self.settings["alert_email"], msg.as_string())
            server.quit()
            print("✅ Email sent successfully")
        except Exception as e:
            print(f"❌ Email failed: {e}")
