"""
models/train_model.py
======================
Train a CNN threat classifier on your downloaded datasets.

USAGE:
  python models/train_model.py

DATASET FOLDER STRUCTURE (put datasets here):
  datasets/
    train/
      Normal/           ← video frames of normal activity
      Harassment/       ← video frames of harassment
      Physical/         ← video frames of physical assault
      Indecent/         ← video frames of indecent behavior
      Distress/         ← video frames of person in distress
    val/
      (same structure)

Run extract_frames.py first to convert videos to frames.
"""

import os
import numpy as np

try:
    import tensorflow as tf
    from tensorflow.keras import layers, models
    from tensorflow.keras.preprocessing.image import ImageDataGenerator
    from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    print("TensorFlow not installed. Run: pip install tensorflow")

IMG_SIZE    = (224, 224)
BATCH_SIZE  = 32
EPOCHS      = 30
NUM_CLASSES = 5   # Normal, Harassment, Physical, Indecent, Distress
TRAIN_DIR   = "datasets/train"
VAL_DIR     = "datasets/val"
MODEL_OUT   = "models/threat_model.h5"


def build_model():
    """
    Transfer learning model using MobileNetV2 as backbone.
    Fast to train, works well on limited data.
    """
    base = tf.keras.applications.MobileNetV2(
        input_shape = (*IMG_SIZE, 3),
        include_top = False,
        weights     = "imagenet",
    )
    base.trainable = False   # Freeze backbone initially

    model = models.Sequential([
        base,
        layers.GlobalAveragePooling2D(),
        layers.Dense(256, activation="relu"),
        layers.Dropout(0.4),
        layers.Dense(128, activation="relu"),
        layers.Dropout(0.3),
        layers.Dense(NUM_CLASSES, activation="softmax"),
    ])

    model.compile(
        optimizer = tf.keras.optimizers.Adam(learning_rate=1e-4),
        loss      = "categorical_crossentropy",
        metrics   = ["accuracy"],
    )
    return model


def train():
    if not TF_AVAILABLE:
        return

    if not os.path.exists(TRAIN_DIR):
        print(f"Training data not found at: {TRAIN_DIR}")
        print("Please download and organize datasets first.")
        return

    # ── Data augmentation to prevent overfitting ──────────
    train_gen = ImageDataGenerator(
        rescale          = 1.0/255,
        rotation_range   = 20,
        width_shift_range = 0.2,
        height_shift_range= 0.2,
        horizontal_flip  = True,
        zoom_range       = 0.15,
        brightness_range = [0.8, 1.2],
    )
    val_gen = ImageDataGenerator(rescale=1.0/255)

    train_data = train_gen.flow_from_directory(
        TRAIN_DIR,
        target_size = IMG_SIZE,
        batch_size  = BATCH_SIZE,
        class_mode  = "categorical",
    )
    val_data = val_gen.flow_from_directory(
        VAL_DIR,
        target_size = IMG_SIZE,
        batch_size  = BATCH_SIZE,
        class_mode  = "categorical",
    )

    print(f"Classes found: {train_data.class_indices}")
    print(f"Training samples: {train_data.samples}")
    print(f"Validation samples: {val_data.samples}")

    model = build_model()
    model.summary()

    callbacks = [
        ModelCheckpoint(MODEL_OUT, save_best_only=True, monitor="val_accuracy", verbose=1),
        EarlyStopping(patience=5, restore_best_weights=True),
        ReduceLROnPlateau(patience=3, factor=0.5, min_lr=1e-6),
    ]

    print(f"\nTraining for up to {EPOCHS} epochs...")
    history = model.fit(
        train_data,
        validation_data = val_data,
        epochs          = EPOCHS,
        callbacks       = callbacks,
    )

    # Fine-tune: unfreeze some base layers
    print("\nFine-tuning top layers of backbone...")
    base_model = model.layers[0]
    base_model.trainable = True
    for layer in base_model.layers[:-20]:
        layer.trainable = False

    model.compile(
        optimizer = tf.keras.optimizers.Adam(learning_rate=1e-5),
        loss      = "categorical_crossentropy",
        metrics   = ["accuracy"],
    )
    model.fit(
        train_data,
        validation_data = val_data,
        epochs          = 10,
        callbacks       = callbacks,
    )

    print(f"\n✅ Model saved to: {MODEL_OUT}")
    val_loss, val_acc = model.evaluate(val_data)
    print(f"Final validation accuracy: {val_acc:.2%}")


if __name__ == "__main__":
    train()
