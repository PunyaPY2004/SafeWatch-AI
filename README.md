# 🛡️ SafeWatch AI
## An AI-Based Smart Surveillance System for Women Safety and Public Decency Enforcement in Urban Spaces

---

## 📁 Project Structure

```
SafeWatch-AI/
│
├── main.py                    ← START HERE — runs everything
├── test_system.py             ← run this first to check setup
├── requirements.txt           ← all Python packages needed
│
├── camera/
│   └── capture.py             ← reads CCTV frames, runs pipeline
│
├── detection/
│   ├── person_detector.py     ← YOLO v8 person detection
│   ├── pose_estimator.py      ← MediaPipe body pose analysis
│   └── threat_classifier.py   ← combines signals → threat score
│
├── alert/
│   └── alert_manager.py       ← SMS + Email + Dashboard alerts
│
├── elevator/
│   └── warning_system.py      ← in-elevator deterrent warning
│
├── database/
│   └── db_manager.py          ← SQLite incident & alert logging
│
├── dashboard/
│   ├── app.py                 ← Flask web app (control room UI)
│   └── templates/
│       ├── index.html         ← main dashboard page
│       ├── alerts.html        ← all alerts page
│       └── incidents.html     ← incident log page
│
├── models/
│   ├── train_model.py         ← train the CNN classifier
│   └── threat_model.h5        ← saved model (after training)
│
├── utils/
│   ├── logger.py              ← logging setup
│   └── extract_frames.py      ← convert videos → image frames
│
├── datasets/                  ← put downloaded datasets here
├── raw_videos/                ← put raw video files here
├── snapshots/                 ← incident snapshots saved here
└── logs/                      ← system log files
```

---

## 🚀 Setup Instructions

### Step 1 — Install Python 3.10
Download from: https://www.python.org/downloads/
✅ Check "Add Python to PATH" during install

### Step 2 — Install all libraries
```bash
pip install -r requirements.txt
```

### Step 3 — Test everything works
```bash
python test_system.py
```

### Step 4 — Configure your cameras
Edit `main.py` and update `CAMERA_SOURCES`:
```python
CAMERA_SOURCES = {
    "CAM_01": {"source": 0,                     "location": "Main Entrance"},
    "CAM_02": {"source": "rtsp://192.168.1.5/", "location": "Elevator 1"},
    "CAM_03": {"source": "videos/test.mp4",      "location": "Park Gate"},
}
```

### Step 5 — (Optional) Setup SMS alerts
Edit `alert/alert_manager.py`:
- Set `USE_SMS = True`
- Fill in your Twilio credentials

### Step 6 — (Optional) Setup Email alerts
Edit `alert/alert_manager.py`:
- Set `USE_EMAIL = True`
- Fill in your Gmail address + App Password

### Step 7 — Run the system
```bash
python main.py
```

### Step 8 — Open the Dashboard
Go to: **http://localhost:5000** in your browser

---

## 🧠 Training Your Own CNN Model

### Step 1 — Organize your video datasets
```
raw_videos/
  Normal/         ← normal CCTV footage
  Harassment/     ← harassment videos (from UCF Crime dataset)
  Physical/       ← physical assault videos
  Indecent/       ← indecent behavior clips
  Distress/       ← distress scenarios
```

### Step 2 — Extract frames from videos
```bash
python utils/extract_frames.py
```

### Step 3 — Train the model
```bash
python models/train_model.py
```
Model saved to `models/threat_model.h5` — system uses it automatically.

---

## 📊 Datasets to Download

| Dataset | Link | Use |
|---------|------|-----|
| UCF Crime Dataset | https://www.crcv.ucf.edu/projects/real-world/ | Violence/crime detection |
| Violence Detection (Kaggle) | https://kaggle.com/datasets/mohamedmustafa/real-life-violence-situations-dataset | Threat classifier training |
| Gender Classification | https://kaggle.com/datasets/cashutosh/gender-classification-dataset | Gender detection |
| HMDB51 | https://serre-lab.clps.brown.edu/resource/hmdb-a-large-human-motion-database/ | Action recognition |

---

## 🛠️ Technologies Used

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10 |
| Video | OpenCV |
| Detection | YOLOv8 (Ultralytics) |
| Pose | MediaPipe |
| AI Model | TensorFlow/Keras CNN |
| Web App | Flask |
| Database | SQLite |
| SMS Alerts | Twilio |
| Email | Gmail SMTP |

---

## 👥 Team
- Mrunali G M
- Punya P Y
- Rashmi C G
- Meghana H Huvanur

**Department of Computer Science & Engineering | 2025–26**
