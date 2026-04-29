"""
alert/alert_manager.py
========================
Handles all alert notifications when a threat is detected:
  1. SMS via Twilio
  2. Email via Gmail SMTP
  3. Dashboard real-time notification (via DB flag)
  4. Saves snapshot evidence
"""

import smtplib
import os
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from utils.logger import setup_logger

logger = setup_logger("AlertManager")

# ── CONFIG — fill in your credentials ──────────────────────
# SMS (Twilio)
TWILIO_ACCOUNT_SID  = "YOUR_TWILIO_SID"         # ← replace
TWILIO_AUTH_TOKEN   = "YOUR_TWILIO_TOKEN"        # ← replace
TWILIO_FROM_NUMBER  = "+1XXXXXXXXXX"             # ← replace
CONTROL_ROOM_PHONE  = "+91XXXXXXXXXX"            # ← replace

# Email (Gmail)
GMAIL_ADDRESS       = "mmpr11700@gmail.com"     # ← replace
GMAIL_APP_PASSWORD  = "qllp utpd wyvi oyng"        # ← replace
CONTROL_ROOM_EMAIL  = "meghanahhuvanur04@gmail.com"  # ← replace

# Toggle which alert methods to use
USE_SMS             = False   # Set True when Twilio configured
USE_EMAIL           = True   # Set True when Gmail configured
USE_DASHBOARD       = True    # Always True — web dashboard alert


class AlertManager:
    def __init__(self, db):
        self.db = db
        self._init_twilio()

    def _init_twilio(self):
        """Initialize Twilio client if credentials are set."""
        self.twilio_client = None
        if USE_SMS and TWILIO_ACCOUNT_SID != "YOUR_TWILIO_SID":
            try:
                from twilio.rest import Client
                self.twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                logger.info("✅ Twilio SMS client initialized")
            except ImportError:
                logger.warning("twilio not installed — SMS disabled. Run: pip install twilio")
            except Exception as e:
                logger.warning(f"Twilio init failed: {e}")

    def send_alert(self, camera_id, location, threat_type, threat_score, snapshot_path):
        """
        Master alert function — calls all enabled alert channels.
        """
        timestamp   = time.strftime("%Y-%m-%d %H:%M:%S")
        score_pct   = f"{threat_score:.0%}"

        message = (
            f"🚨 SAFEWATCH AI ALERT\n"
            f"Location  : {location}\n"
            f"Camera    : {camera_id}\n"
            f"Threat    : {threat_type}\n"
            f"Confidence: {score_pct}\n"
            f"Time      : {timestamp}\n"
            f"Evidence  : {snapshot_path}"
        )

        logger.warning(f"\n{'='*50}\n{message}\n{'='*50}")

        # ── Channel 1: Dashboard (always) ─────────────────
        if USE_DASHBOARD:
            self._alert_dashboard(camera_id, location, threat_type,
                                  threat_score, snapshot_path, timestamp)

        # ── Channel 2: SMS ────────────────────────────────
        if USE_SMS:
            self._send_sms(message)

        # ── Channel 3: Email ──────────────────────────────
        if USE_EMAIL:
            self._send_email(location, threat_type, score_pct,
                             timestamp, snapshot_path, message)

    def _alert_dashboard(self, camera_id, location, threat_type,
                         threat_score, snapshot_path, timestamp):
        """Save alert to database so dashboard shows it."""
        try:
            self.db.save_alert(
                camera_id     = camera_id,
                location      = location,
                threat_type   = threat_type,
                threat_score  = threat_score,
                snapshot_path = snapshot_path,
                timestamp     = timestamp,
            )
            logger.info(f"Dashboard alert saved for {camera_id}")
        except Exception as e:
            logger.error(f"Dashboard alert failed: {e}")

    def _send_sms(self, message):
        """Send SMS alert via Twilio."""
        if not self.twilio_client:
            logger.warning("SMS skipped — Twilio not configured")
            return
        try:
            msg = self.twilio_client.messages.create(
                body  = message,
                from_ = TWILIO_FROM_NUMBER,
                to    = CONTROL_ROOM_PHONE,
            )
            logger.info(f"✅ SMS sent! SID: {msg.sid}")
        except Exception as e:
            logger.error(f"SMS failed: {e}")

    def _send_email(self, location, threat_type, score_pct,
                    timestamp, snapshot_path, plain_text):
        """Send email alert with snapshot attached via Gmail SMTP."""
        if GMAIL_ADDRESS == "your_email@gmail.com":
            logger.warning("Email skipped — Gmail not configured")
            return
        try:
            msg              = MIMEMultipart()
            msg["Subject"]   = f"🚨 SafeWatch AI Alert — {threat_type} at {location}"
            msg["From"]      = GMAIL_ADDRESS
            msg["To"]        = CONTROL_ROOM_EMAIL

            # HTML body
            html_body = f"""
            <html><body style="font-family:Arial; color:#333;">
            <h2 style="color:#c0392b;">🚨 SafeWatch AI — Threat Detected!</h2>
            <table>
              <tr><td><b>Location:</b></td><td>{location}</td></tr>
              <tr><td><b>Threat Type:</b></td><td>{threat_type}</td></tr>
              <tr><td><b>Confidence:</b></td><td>{score_pct}</td></tr>
              <tr><td><b>Time:</b></td><td>{timestamp}</td></tr>
            </table>
            <br>
            <p>Please check the control room dashboard for more details.</p>
            <p style="color:#888; font-size:12px;">SafeWatch AI — Protecting Urban Spaces</p>
            </body></html>
            """
            msg.attach(MIMEText(html_body, "html"))

            # Attach snapshot if it exists
            if snapshot_path and os.path.exists(snapshot_path):
                with open(snapshot_path, "rb") as f:
                    img = MIMEImage(f.read())
                    img.add_header("Content-Disposition", "attachment",
                                   filename=os.path.basename(snapshot_path))
                    msg.attach(img)

            # Send
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
                server.sendmail(GMAIL_ADDRESS, CONTROL_ROOM_EMAIL, msg.as_string())

            logger.info(f"✅ Email alert sent to {CONTROL_ROOM_EMAIL}")
        except Exception as e:
            logger.error(f"Email failed: {e}")
