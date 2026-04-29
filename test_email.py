import yagmail

SENDER   = "mmpr11700@gmail.com"
PASSWORD = "qllputpdwyvioyng"   # 16-char App Password, NO spaces
RECEIVER = "meghanahhuvanur04@gmail.com"

try:
    yag = yagmail.SMTP(SENDER, PASSWORD)
    yag.send(
        to=RECEIVER,
        subject="🚨 SafeWatch AI — Test Alert!",
        contents="✅ Email alerts are working! This is a test from SafeWatch AI."
    )
    print("✅ Email sent successfully!")

except Exception as e:
    print(f"❌ Error: {e}")