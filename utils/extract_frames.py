"""
utils/extract_frames.py
========================
Converts video files from datasets into image frames
for training the CNN threat classifier.

USAGE:
  python utils/extract_frames.py

Put your downloaded video datasets in:
  raw_videos/
    Normal/
      video1.mp4
      video2.avi
    Harassment/
      video1.mp4
    ...etc

Output frames will be saved to:
  datasets/train/<class>/
  datasets/val/<class>/
"""

import cv2
import os
import random

RAW_VIDEO_DIR  = "raw_videos"
OUTPUT_DIR     = "datasets"
FRAME_INTERVAL = 10     # Extract 1 frame every N frames
IMG_SIZE       = (224, 224)
TRAIN_SPLIT    = 0.85   # 85% training, 15% validation

CLASSES = ["Normal", "Harassment", "Physical", "Indecent", "Distress"]


def extract_frames():
    if not os.path.exists(RAW_VIDEO_DIR):
        print(f"Put your videos in: {RAW_VIDEO_DIR}/<ClassName>/video.mp4")
        os.makedirs(RAW_VIDEO_DIR)
        for c in CLASSES:
            os.makedirs(os.path.join(RAW_VIDEO_DIR, c), exist_ok=True)
        print("Folders created. Add videos and re-run.")
        return

    total_frames = 0

    for class_name in CLASSES:
        video_dir = os.path.join(RAW_VIDEO_DIR, class_name)
        if not os.path.exists(video_dir):
            continue

        videos = [f for f in os.listdir(video_dir)
                  if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]

        if not videos:
            print(f"No videos found in {video_dir}")
            continue

        print(f"\nProcessing class: {class_name} ({len(videos)} videos)")

        class_frames = []
        for video_file in videos:
            video_path = os.path.join(video_dir, video_file)
            cap = cv2.VideoCapture(video_path)

            frame_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                if frame_idx % FRAME_INTERVAL == 0:
                    resized = cv2.resize(frame, IMG_SIZE)
                    class_frames.append(resized)
                frame_idx += 1

            cap.release()
            print(f"  {video_file}: {frame_idx // FRAME_INTERVAL} frames extracted")

        # Shuffle and split
        random.shuffle(class_frames)
        split    = int(len(class_frames) * TRAIN_SPLIT)
        train_f  = class_frames[:split]
        val_f    = class_frames[split:]

        # Save train frames
        train_class_dir = os.path.join(OUTPUT_DIR, "train", class_name)
        os.makedirs(train_class_dir, exist_ok=True)
        for i, frame in enumerate(train_f):
            cv2.imwrite(os.path.join(train_class_dir, f"{class_name}_{i:05d}.jpg"), frame)

        # Save val frames
        val_class_dir = os.path.join(OUTPUT_DIR, "val", class_name)
        os.makedirs(val_class_dir, exist_ok=True)
        for i, frame in enumerate(val_f):
            cv2.imwrite(os.path.join(val_class_dir, f"{class_name}_{i:05d}.jpg"), frame)

        print(f"  Saved {len(train_f)} train + {len(val_f)} val frames")
        total_frames += len(class_frames)

    print(f"\n✅ Done! Total frames extracted: {total_frames}")
    print(f"   Training data: {OUTPUT_DIR}/train/")
    print(f"   Validation data: {OUTPUT_DIR}/val/")
    print(f"\nNow run: python models/train_model.py")


if __name__ == "__main__":
    extract_frames()
