"""
Face Recognition Training Pipeline using Siamese Network with Triplet Loss
Based on the notebook: face-recognition-siamese-network-triplet-loss.ipynb

This script trains a face recognition model using:
- FaceNet embeddings as the base model
- Siamese Network architecture
- Triplet Loss function
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
import cv2
import math
import argparse
from tqdm import tqdm

import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator, load_img, img_to_array
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras import metrics

# ========================
# Configuration
# ========================
class Config:
    """Training configuration"""
    # Paths - Update these for your environment
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    TRAIN_CSV = os.path.join(BASE_DIR, "train.csv")
    TEST_CSV = os.path.join(BASE_DIR, "test.csv")
    IMAGES_DIR = os.path.join(BASE_DIR, "Detected Faces")
    MODEL_SAVE_PATH = os.path.join(BASE_DIR, "face_recognition_model.weights.h5")
    EMBEDDINGS_SAVE_PATH = os.path.join(BASE_DIR, "face_embeddings_model.keras")
    
    # Model parameters
    IMG_SIZE = 160  # FaceNet input size
    EMBEDDING_SIZE = 128  # FaceNet embedding size
    MARGIN = 0.5  # Triplet loss margin
    
    # Training parameters
    BATCH_SIZE = 32
    EPOCHS = 50
    LEARNING_RATE = 0.0001
    
    # Data split
    TRAIN_RATIO = 0.8


# ========================
# Data Preparation
# ========================
def load_and_prepare_data(config):
    """
    Load CSV files and prepare triplets from pairs.
    The dataset has pairs (Image1, Image2, class: similar/different).
    We need to create triplets (anchor, positive, negative) for training.
    """
    print("Loading data...")
    
    train_df = pd.read_csv(config.TRAIN_CSV)
    test_df = pd.read_csv(config.TEST_CSV)
    
    # Filter only rows where faces are present
    train_df = train_df[train_df['face_present'] == 'Yes'].reset_index(drop=True)
    test_df = test_df[test_df['face_present'] == 'Yes'].reset_index(drop=True)
    
    print(f"Training samples: {len(train_df)}")
    print(f"Test samples: {len(test_df)}")
    
    return train_df, test_df


def create_triplets_from_pairs(df, images_dir, max_triplets=None):
    """
    Create triplets from pair data.
    For each 'similar' pair, find a 'different' pair to create a triplet.
    """
    print("Creating triplets from pairs...")
    
    similar_pairs = df[df['class'] == 'similar'].reset_index(drop=True)
    different_pairs = df[df['class'] == 'different'].reset_index(drop=True)
    
    triplets = []
    
    for idx, row in tqdm(similar_pairs.iterrows(), total=len(similar_pairs), desc="Creating triplets"):
        anchor = row['Image1']
        positive = row['Image2']
        
        # Find a negative sample from different pairs
        neg_idx = idx % len(different_pairs)
        negative = different_pairs.iloc[neg_idx]['Image2']
        
        # Verify all images exist
        anchor_path = os.path.join(images_dir, anchor)
        positive_path = os.path.join(images_dir, positive)
        negative_path = os.path.join(images_dir, negative)
        
        if os.path.exists(anchor_path) and os.path.exists(positive_path) and os.path.exists(negative_path):
            triplets.append({
                'anchor': anchor,
                'positive': positive,
                'negative': negative
            })
        
        if max_triplets and len(triplets) >= max_triplets:
            break
    
    triplet_df = pd.DataFrame(triplets)
    print(f"Created {len(triplet_df)} triplets")
    
    return triplet_df


# ========================
# Data Generator
# ========================
class TripletDataGenerator(tf.keras.utils.Sequence):
    """
    Custom data generator for triplet data.
    Generates batches of (anchor, positive, negative) images.
    """
    
    def __init__(self, dataframe, images_dir, img_size=160, batch_size=32, augment=False):
        self.dataframe = dataframe
        self.images_dir = images_dir
        self.img_size = img_size
        self.batch_size = batch_size
        self.augment = augment
        self.indexes = np.arange(len(self.dataframe))
        
        if augment:
            self.datagen = ImageDataGenerator(
                rotation_range=10,
                width_shift_range=0.1,
                height_shift_range=0.1,
                horizontal_flip=True,
                brightness_range=[0.9, 1.1]
            )
        else:
            self.datagen = None
    
    def __len__(self):
        return int(np.ceil(len(self.dataframe) / self.batch_size))
    
    def __getitem__(self, index):
        batch_indexes = self.indexes[index * self.batch_size:(index + 1) * self.batch_size]
        batch_data = self.dataframe.iloc[batch_indexes]
        
        anchors = []
        positives = []
        negatives = []
        
        for _, row in batch_data.iterrows():
            anchor = self._load_image(row['anchor'])
            positive = self._load_image(row['positive'])
            negative = self._load_image(row['negative'])
            
            if self.augment and self.datagen:
                anchor = self.datagen.random_transform(anchor)
                positive = self.datagen.random_transform(positive)
                negative = self.datagen.random_transform(negative)
            
            anchors.append(anchor)
            positives.append(positive)
            negatives.append(negative)
        
        return [np.array(anchors), np.array(positives), np.array(negatives)]
    
    def _load_image(self, filename):
        """Load and preprocess a single image."""
        img_path = os.path.join(self.images_dir, filename)
        img = load_img(img_path, target_size=(self.img_size, self.img_size))
        img = img_to_array(img)
        img = img / 255.0  # Normalize to [0, 1]
        return img
    
    def on_epoch_end(self):
        """Shuffle indexes at the end of each epoch."""
        np.random.shuffle(self.indexes)


# ========================
# Model Definition
# ========================
def create_embedding_model(img_size=160, embedding_size=128):
    """
    Create a simple embedding model for face recognition.
    In production, you would use a pre-trained FaceNet model.
    """
    from tensorflow.keras.layers import (
        Conv2D, MaxPooling2D, GlobalAveragePooling2D,
        Dense, Dropout, BatchNormalization
    )
    from tensorflow.keras.applications import MobileNetV2
    
    # Use MobileNetV2 as base (lighter than ResNet for training)
    base_model = MobileNetV2(
        input_shape=(img_size, img_size, 3),
        include_top=False,
        weights='imagenet'
    )
    
    # Freeze early layers
    for layer in base_model.layers[:-30]:
        layer.trainable = False
    
    x = base_model.output
    x = GlobalAveragePooling2D()(x)
    x = Dense(512, activation='relu')(x)
    x = BatchNormalization()(x)
    x = Dropout(0.5)(x)
    x = Dense(embedding_size)(x)  # L2 normalization will be applied in loss
    
    embedding_model = Model(inputs=base_model.input, outputs=x, name='embedding_model')
    
    return embedding_model


def create_siamese_network(embedding_model, img_size=160):
    """
    Create a Siamese network with three inputs for triplet loss training.
    """
    # Define inputs
    anchor_input = Input(shape=(img_size, img_size, 3), name='anchor')
    positive_input = Input(shape=(img_size, img_size, 3), name='positive')
    negative_input = Input(shape=(img_size, img_size, 3), name='negative')
    
    # Get embeddings
    anchor_embedding = embedding_model(anchor_input)
    positive_embedding = embedding_model(positive_input)
    negative_embedding = embedding_model(negative_input)
    
    # Create siamese network
    siamese_network = Model(
        inputs=[anchor_input, positive_input, negative_input],
        outputs=[anchor_embedding, positive_embedding, negative_embedding],
        name='siamese_network'
    )
    
    return siamese_network


class SiameseModel(Model):
    """
    Custom Siamese Model with Triplet Loss.
    
    Triplet Loss = max(0, d(anchor, positive) - d(anchor, negative) + margin)
    
    where d is the Euclidean distance between embeddings.
    """
    
    def __init__(self, siamese_network, margin=0.5):
        super().__init__()
        self.siamese_network = siamese_network
        self.margin = margin
        self.loss_tracker = metrics.Mean(name='loss')
        self.pos_dist_tracker = metrics.Mean(name='pos_dist')
        self.neg_dist_tracker = metrics.Mean(name='neg_dist')
    
    def call(self, inputs):
        return self.siamese_network(inputs)
    
    def train_step(self, data):
        with tf.GradientTape() as tape:
            loss, pos_dist, neg_dist = self._compute_loss(data)
        
        gradients = tape.gradient(loss, self.siamese_network.trainable_weights)
        self.optimizer.apply_gradients(zip(gradients, self.siamese_network.trainable_weights))
        
        self.loss_tracker.update_state(loss)
        self.pos_dist_tracker.update_state(pos_dist)
        self.neg_dist_tracker.update_state(neg_dist)
        
        return {
            "loss": self.loss_tracker.result(),
            "pos_dist": self.pos_dist_tracker.result(),
            "neg_dist": self.neg_dist_tracker.result()
        }
    
    def test_step(self, data):
        loss, pos_dist, neg_dist = self._compute_loss(data)
        
        self.loss_tracker.update_state(loss)
        self.pos_dist_tracker.update_state(pos_dist)
        self.neg_dist_tracker.update_state(neg_dist)
        
        return {
            "loss": self.loss_tracker.result(),
            "pos_dist": self.pos_dist_tracker.result(),
            "neg_dist": self.neg_dist_tracker.result()
        }
    
    def _compute_loss(self, data):
        """Compute triplet loss."""
        anchor, positive, negative = self.siamese_network(data)
        
        # L2 normalize embeddings
        anchor = tf.nn.l2_normalize(anchor, axis=1)
        positive = tf.nn.l2_normalize(positive, axis=1)
        negative = tf.nn.l2_normalize(negative, axis=1)
        
        # Calculate distances
        pos_dist = tf.reduce_sum(tf.square(anchor - positive), axis=-1)
        neg_dist = tf.reduce_sum(tf.square(anchor - negative), axis=-1)
        
        # Triplet loss
        loss = tf.maximum(pos_dist - neg_dist + self.margin, 0.0)
        loss = tf.reduce_mean(loss)
        
        return loss, tf.reduce_mean(pos_dist), tf.reduce_mean(neg_dist)
    
    @property
    def metrics(self):
        return [self.loss_tracker, self.pos_dist_tracker, self.neg_dist_tracker]


# ========================
# Training Functions
# ========================
def train_model(config):
    """Main training function."""
    print("=" * 50)
    print("Face Recognition Training Pipeline")
    print("=" * 50)
    
    # Set random seeds for reproducibility
    tf.random.set_seed(42)
    np.random.seed(42)
    
    # Load data
    train_df, test_df = load_and_prepare_data(config)
    
    # Create triplets
    train_triplets = create_triplets_from_pairs(train_df, config.IMAGES_DIR)
    test_triplets = create_triplets_from_pairs(test_df, config.IMAGES_DIR)
    
    if len(train_triplets) == 0:
        print("ERROR: No valid triplets could be created. Check your data paths.")
        return None
    
    # Create data generators
    print("\nCreating data generators...")
    train_generator = TripletDataGenerator(
        train_triplets,
        config.IMAGES_DIR,
        img_size=config.IMG_SIZE,
        batch_size=config.BATCH_SIZE,
        augment=True
    )
    
    test_generator = TripletDataGenerator(
        test_triplets,
        config.IMAGES_DIR,
        img_size=config.IMG_SIZE,
        batch_size=config.BATCH_SIZE,
        augment=False
    )
    
    # Create model
    print("\nBuilding model...")
    embedding_model = create_embedding_model(
        img_size=config.IMG_SIZE,
        embedding_size=config.EMBEDDING_SIZE
    )
    
    siamese_network = create_siamese_network(
        embedding_model,
        img_size=config.IMG_SIZE
    )
    
    siamese_model = SiameseModel(siamese_network, margin=config.MARGIN)
    siamese_model.compile(optimizer=Adam(learning_rate=config.LEARNING_RATE))
    
    # Build the model by running a dummy batch
    print("\nBuilding model with dummy data...")
    dummy_batch = train_generator[0]
    _ = siamese_model(dummy_batch)
    
    # Print model summary
    print("\nEmbedding Model Summary:")
    embedding_model.summary()
    
    print("\nSiamese Network Summary:")
    siamese_network.summary()
    
    # Custom callback to save embedding model
    class EmbeddingModelCheckpoint(tf.keras.callbacks.Callback):
        def __init__(self, embedding_model, filepath, monitor='val_loss', mode='min'):
            super().__init__()
            self.embedding_model = embedding_model
            self.filepath = filepath
            self.monitor = monitor
            self.mode = mode
            self.best = float('inf') if mode == 'min' else float('-inf')
        
        def on_epoch_end(self, epoch, logs=None):
            current = logs.get(self.monitor)
            if current is None:
                return
            
            if (self.mode == 'min' and current < self.best) or \
               (self.mode == 'max' and current > self.best):
                self.best = current
                print(f"\nEpoch {epoch + 1}: {self.monitor} improved to {current:.5f}, saving embedding model...")
                self.embedding_model.save(self.filepath)
    
    # Callbacks
    callbacks = [
        EmbeddingModelCheckpoint(
            embedding_model,
            config.EMBEDDINGS_SAVE_PATH,
            monitor='val_loss',
            mode='min'
        ),
        EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True,
            verbose=1
        ),
        ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.3,
            patience=5,
            min_lr=1e-8,
            verbose=1
        )
    ]
    
    # Training
    print("\n" + "=" * 50)
    print("Starting Training...")
    print("=" * 50)
    
    try:
        history = siamese_model.fit(
            train_generator,
            validation_data=test_generator,
            epochs=config.EPOCHS,
            callbacks=callbacks,
            verbose=1
        )
        
        # Plot training history
        plot_training_history(history, config.BASE_DIR)
        
        # Save the final embedding model
        print(f"\nSaving final embedding model to: {config.EMBEDDINGS_SAVE_PATH}")
        embedding_model.save(config.EMBEDDINGS_SAVE_PATH)
        
        print("\n" + "=" * 50)
        print("Training Complete!")
        print(f"Best model saved to: {config.EMBEDDINGS_SAVE_PATH}")
        print("=" * 50)
        
        return history
        
    except KeyboardInterrupt:
        print("\nTraining interrupted by user.")
        # Save the model even if interrupted
        print(f"Saving current embedding model to: {config.EMBEDDINGS_SAVE_PATH}")
        embedding_model.save(config.EMBEDDINGS_SAVE_PATH)
        return None


def plot_training_history(history, save_dir):
    """Plot and save training history."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    
    # Loss
    axes[0].plot(history.history['loss'], label='Train Loss')
    axes[0].plot(history.history['val_loss'], label='Val Loss')
    axes[0].set_title('Triplet Loss')
    axes[0].set_xlabel('Epoch')
    axes[0].set_ylabel('Loss')
    axes[0].legend()
    
    # Positive Distance
    axes[1].plot(history.history['pos_dist'], label='Train')
    axes[1].plot(history.history['val_pos_dist'], label='Val')
    axes[1].set_title('Positive Distance (should decrease)')
    axes[1].set_xlabel('Epoch')
    axes[1].set_ylabel('Distance')
    axes[1].legend()
    
    # Negative Distance
    axes[2].plot(history.history['neg_dist'], label='Train')
    axes[2].plot(history.history['val_neg_dist'], label='Val')
    axes[2].set_title('Negative Distance (should increase)')
    axes[2].set_xlabel('Epoch')
    axes[2].set_ylabel('Distance')
    axes[2].legend()
    
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, 'training_history.png'), dpi=150)
    plt.close()
    print(f"Training history plot saved to: {os.path.join(save_dir, 'training_history.png')}")


# ========================
# Fine-tuning Function
# ========================
def finetune_model(config, new_data_only=False, freeze_layers=100):
    """
    Fine-tune an existing model with new data.
    This loads the existing model and continues training with new data only.
    """
    from tensorflow.keras.models import load_model
    
    print("\n" + "=" * 50)
    print("Fine-tuning Face Recognition Model")
    print("=" * 50)
    
    # Check if existing model exists
    if not os.path.exists(config.EMBEDDINGS_SAVE_PATH):
        print(f"ERROR: No existing model found at {config.EMBEDDINGS_SAVE_PATH}")
        print("Please train a model first using: python train_face_recognition.py --mode train")
        return None
    
    # Load existing embedding model
    print(f"\nLoading existing model from {config.EMBEDDINGS_SAVE_PATH}...")
    try:
        embedding_model = load_model(config.EMBEDDINGS_SAVE_PATH)
        print("Model loaded successfully!")
    except Exception as e:
        print(f"ERROR: Failed to load model: {e}")
        return None
    
    # Freeze early layers
    print(f"\nFreezing first {freeze_layers} layers...")
    layers_frozen = 0
    for i, layer in enumerate(embedding_model.layers):
        if i < freeze_layers:
            layer.trainable = False
            layers_frozen += 1
        else:
            layer.trainable = True
    
    trainable_count = sum([1 for layer in embedding_model.layers if layer.trainable])
    print(f"Frozen layers: {layers_frozen}")
    print(f"Trainable layers: {trainable_count}")
    
    # Load data
    new_pairs_file = os.path.join(config.BASE_DIR, 'new_pairs.csv')
    
    if new_data_only and os.path.exists(new_pairs_file):
        print(f"\nLoading new pairs from {new_pairs_file}...")
        try:
            new_pairs_df = pd.read_csv(new_pairs_file)
            # Remove date_added column if exists
            if 'date_added' in new_pairs_df.columns:
                new_pairs_df = new_pairs_df.drop(columns=['date_added'])
            
            print(f"New pairs loaded: {len(new_pairs_df)}")
            
            # Check if we have enough similar pairs for triplet creation
            similar_count = len(new_pairs_df[new_pairs_df['class'] == 'similar'])
            if similar_count < 5:
                print(f"Warning: Only {similar_count} similar pairs in new data.")
                print("Adding some data from main training set for better fine-tuning...")
                # Load main training data and add some pairs
                main_train_df = pd.read_csv(config.TRAIN_CSV)
                main_train_df = main_train_df[main_train_df['face_present'] == 'Yes'].reset_index(drop=True)
                # Sample some existing pairs to mix with new data
                sample_size = min(100, len(main_train_df))
                sampled_df = main_train_df.sample(n=sample_size, random_state=42)
                new_pairs_df = pd.concat([new_pairs_df, sampled_df], ignore_index=True)
                print(f"Combined pairs: {len(new_pairs_df)}")
            
            # Split into train/test - use 90/10 for small datasets
            split_ratio = 0.1 if len(new_pairs_df) < 50 else 0.2
            from sklearn.model_selection import train_test_split
            train_df, test_df = train_test_split(new_pairs_df, test_size=split_ratio, random_state=42)
            train_df = train_df.reset_index(drop=True)
            test_df = test_df.reset_index(drop=True)
        except Exception as e:
            print(f"Warning: Could not load new pairs file: {e}")
            print("Falling back to full dataset...")
            train_df, test_df = load_and_prepare_data(config)
    else:
        if new_data_only:
            print(f"Warning: new_pairs.csv not found at {new_pairs_file}")
            print("Falling back to full dataset...")
        train_df, test_df = load_and_prepare_data(config)
    
    # Create triplets
    train_triplets = create_triplets_from_pairs(train_df, config.IMAGES_DIR)
    test_triplets = create_triplets_from_pairs(test_df, config.IMAGES_DIR)
    
    if len(train_triplets) == 0:
        print("ERROR: No training triplets created. Check your data.")
        return None
    
    # If test triplets are empty, use some train triplets for validation
    if len(test_triplets) == 0:
        print("Warning: No test triplets. Using portion of training data for validation.")
        split_idx = int(len(train_triplets) * 0.8)
        test_triplets = train_triplets.iloc[split_idx:].reset_index(drop=True)
        train_triplets = train_triplets.iloc[:split_idx].reset_index(drop=True)
    
    print(f"Training triplets: {len(train_triplets)}")
    print(f"Validation triplets: {len(test_triplets)}")
    
    # Create data generators
    print("\nCreating data generators...")
    train_generator = TripletDataGenerator(
        train_triplets,
        config.IMAGES_DIR,
        img_size=config.IMG_SIZE,
        batch_size=config.BATCH_SIZE,
        augment=True
    )
    
    test_generator = TripletDataGenerator(
        test_triplets,
        config.IMAGES_DIR,
        img_size=config.IMG_SIZE,
        batch_size=config.BATCH_SIZE,
        augment=False
    )
    
    # Create siamese network with existing embedding model
    anchor_input = Input(shape=(config.IMG_SIZE, config.IMG_SIZE, 3), name='anchor')
    positive_input = Input(shape=(config.IMG_SIZE, config.IMG_SIZE, 3), name='positive')
    negative_input = Input(shape=(config.IMG_SIZE, config.IMG_SIZE, 3), name='negative')
    
    anchor_embedding = embedding_model(anchor_input)
    positive_embedding = embedding_model(positive_input)
    negative_embedding = embedding_model(negative_input)
    
    siamese_network = Model(
        inputs=[anchor_input, positive_input, negative_input],
        outputs=[anchor_embedding, positive_embedding, negative_embedding],
        name='siamese_network_finetune'
    )
    
    # Create SiameseModel for training
    siamese_model = SiameseModel(siamese_network, margin=config.MARGIN)
    
    # Use lower learning rate for fine-tuning
    finetune_lr = config.LEARNING_RATE * 0.1  # 10x smaller
    print(f"\nUsing fine-tuning learning rate: {finetune_lr}")
    
    siamese_model.compile(optimizer=Adam(learning_rate=finetune_lr))
    
    # Build model with dummy data
    print("\nBuilding model with dummy data...")
    dummy_batch = train_generator[0]
    _ = siamese_model(dummy_batch)
    
    # Custom callback to save embedding model
    class EmbeddingModelCheckpoint(tf.keras.callbacks.Callback):
        def __init__(self, embedding_model, filepath, monitor='val_loss', mode='min'):
            super().__init__()
            self.embedding_model = embedding_model
            self.filepath = filepath
            self.monitor = monitor
            self.mode = mode
            self.best = float('inf') if mode == 'min' else float('-inf')
        
        def on_epoch_end(self, epoch, logs=None):
            current = logs.get(self.monitor)
            if current is None:
                return
            
            if (self.mode == 'min' and current < self.best) or \
               (self.mode == 'max' and current > self.best):
                self.best = current
                print(f"\nEpoch {epoch + 1}: {self.monitor} improved to {current:.5f}, saving embedding model...")
                self.embedding_model.save(self.filepath)
    
    # Callbacks
    callbacks = [
        EmbeddingModelCheckpoint(
            embedding_model,
            config.EMBEDDINGS_SAVE_PATH,
            monitor='val_loss',
            mode='min'
        ),
        EarlyStopping(
            monitor='val_loss',
            patience=5,  # Less patience for fine-tuning
            restore_best_weights=True,
            verbose=1
        ),
        ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=3,
            min_lr=1e-8,
            verbose=1
        )
    ]
    
    # Training
    print("\n" + "=" * 50)
    print("Starting Fine-tuning...")
    print("=" * 50)
    
    try:
        history = siamese_model.fit(
            train_generator,
            validation_data=test_generator,
            epochs=config.EPOCHS,
            callbacks=callbacks,
            verbose=1
        )
        
        # Plot training history
        plot_training_history(history, config.BASE_DIR)
        
        # Save the final embedding model
        print(f"\nSaving fine-tuned model to: {config.EMBEDDINGS_SAVE_PATH}")
        embedding_model.save(config.EMBEDDINGS_SAVE_PATH)
        
        # Clear new_pairs.csv after successful training
        if new_data_only and os.path.exists(new_pairs_file):
            try:
                os.remove(new_pairs_file)
                print(f"Cleared new pairs file: {new_pairs_file}")
            except Exception as e:
                print(f"Warning: Could not remove new pairs file: {e}")
        
        print("\n" + "=" * 50)
        print("Fine-tuning Complete!")
        print(f"Model saved to: {config.EMBEDDINGS_SAVE_PATH}")
        print("=" * 50)
        
        return history
        
    except KeyboardInterrupt:
        print("\nFine-tuning interrupted by user.")
        print(f"Saving current model to: {config.EMBEDDINGS_SAVE_PATH}")
        embedding_model.save(config.EMBEDDINGS_SAVE_PATH)
        return None
    except Exception as e:
        print(f"\nERROR during fine-tuning: {e}")
        return None


# ========================
# Evaluation Functions
# ========================
def evaluate_model(config, threshold=1.5):
    """
    Evaluate the trained model on the test set.
    """
    print("\n" + "=" * 50)
    print("Evaluating Model...")
    print("=" * 50)
    
    # Load test data
    test_df = pd.read_csv(config.TEST_CSV)
    test_df = test_df[test_df['face_present'] == 'Yes'].reset_index(drop=True)
    
    # Load model
    embedding_model = tf.keras.models.load_model(config.EMBEDDINGS_SAVE_PATH, compile=False)
    
    correct = 0
    total = 0
    distances = {'similar': [], 'different': []}
    
    print("Computing distances...")
    for idx, row in tqdm(test_df.iterrows(), total=len(test_df)):
        img1_path = os.path.join(config.IMAGES_DIR, row['Image1'])
        img2_path = os.path.join(config.IMAGES_DIR, row['Image2'])
        
        if not os.path.exists(img1_path) or not os.path.exists(img2_path):
            continue
        
        # Load images
        img1 = load_img(img1_path, target_size=(config.IMG_SIZE, config.IMG_SIZE))
        img2 = load_img(img2_path, target_size=(config.IMG_SIZE, config.IMG_SIZE))
        
        img1 = img_to_array(img1) / 255.0
        img2 = img_to_array(img2) / 255.0
        
        # Get embeddings
        emb1 = embedding_model.predict(np.expand_dims(img1, axis=0), verbose=0)
        emb2 = embedding_model.predict(np.expand_dims(img2, axis=0), verbose=0)
        
        # L2 normalize
        emb1 = emb1 / np.linalg.norm(emb1)
        emb2 = emb2 / np.linalg.norm(emb2)
        
        # Calculate distance
        distance = np.linalg.norm(emb1 - emb2)
        
        # Store distance for analysis
        distances[row['class']].append(distance)
        
        # Make prediction
        predicted_similar = distance < threshold
        actual_similar = row['class'] == 'similar'
        
        if predicted_similar == actual_similar:
            correct += 1
        total += 1
    
    accuracy = correct / total if total > 0 else 0
    
    print(f"\nResults with threshold = {threshold}:")
    print(f"Accuracy: {accuracy:.4f} ({correct}/{total})")
    
    # Print distance statistics
    print(f"\nDistance Statistics:")
    print(f"Similar pairs - Mean: {np.mean(distances['similar']):.4f}, Std: {np.std(distances['similar']):.4f}")
    print(f"Different pairs - Mean: {np.mean(distances['different']):.4f}, Std: {np.std(distances['different']):.4f}")
    
    # Plot distance distributions
    plt.figure(figsize=(10, 5))
    plt.hist(distances['similar'], bins=30, alpha=0.5, label='Similar', color='green')
    plt.hist(distances['different'], bins=30, alpha=0.5, label='Different', color='red')
    plt.axvline(x=threshold, color='black', linestyle='--', label=f'Threshold={threshold}')
    plt.xlabel('L2 Distance')
    plt.ylabel('Count')
    plt.title('Distance Distribution')
    plt.legend()
    plt.savefig(os.path.join(config.BASE_DIR, 'distance_distribution.png'), dpi=150)
    plt.close()
    
    # Find optimal threshold
    best_threshold = find_optimal_threshold(distances)
    print(f"\nSuggested optimal threshold: {best_threshold:.4f}")
    
    return accuracy, distances


def find_optimal_threshold(distances):
    """Find the optimal threshold that maximizes accuracy."""
    all_distances = distances['similar'] + distances['different']
    labels = [1] * len(distances['similar']) + [0] * len(distances['different'])
    
    best_threshold = 0
    best_accuracy = 0
    
    for threshold in np.arange(0.5, 3.0, 0.05):
        predictions = [1 if d < threshold else 0 for d in all_distances]
        accuracy = sum([p == l for p, l in zip(predictions, labels)]) / len(labels)
        
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_threshold = threshold
    
    return best_threshold


# ========================
# Inference Functions
# ========================
def predict_similarity(embedding_model, img1_path, img2_path, threshold=1.5, img_size=160):
    """
    Predict if two face images belong to the same person.
    """
    # Load images
    img1 = load_img(img1_path, target_size=(img_size, img_size))
    img2 = load_img(img2_path, target_size=(img_size, img_size))
    
    img1 = img_to_array(img1) / 255.0
    img2 = img_to_array(img2) / 255.0
    
    # Get embeddings
    emb1 = embedding_model.predict(np.expand_dims(img1, axis=0), verbose=0)
    emb2 = embedding_model.predict(np.expand_dims(img2, axis=0), verbose=0)
    
    # L2 normalize
    emb1 = emb1 / np.linalg.norm(emb1)
    emb2 = emb2 / np.linalg.norm(emb2)
    
    # Calculate distance
    distance = np.linalg.norm(emb1 - emb2)
    
    is_same_person = distance < threshold
    confidence = 1 - min(distance / (2 * threshold), 1)
    
    return {
        'is_same_person': is_same_person,
        'distance': distance,
        'confidence': confidence,
        'threshold': threshold
    }


# ========================
# Main Entry Point
# ========================
def main():
    parser = argparse.ArgumentParser(description='Face Recognition Training Pipeline')
    parser.add_argument('--mode', type=str, default='train', choices=['train', 'evaluate', 'both', 'finetune'],
                        help='Mode: train, evaluate, both, or finetune')
    parser.add_argument('--epochs', type=int, default=50, help='Number of training epochs')
    parser.add_argument('--batch_size', type=int, default=32, help='Batch size')
    parser.add_argument('--learning_rate', type=float, default=0.0001, help='Learning rate')
    parser.add_argument('--threshold', type=float, default=1.5, help='Similarity threshold for evaluation')
    parser.add_argument('--new_data_only', action='store_true', help='Train only on new data (for finetune mode)')
    parser.add_argument('--freeze_layers', type=int, default=100, help='Number of layers to freeze in finetune mode')
    
    args = parser.parse_args()
    
    # Update config with command line arguments
    config = Config()
    config.EPOCHS = args.epochs
    config.BATCH_SIZE = args.batch_size
    config.LEARNING_RATE = args.learning_rate
    
    # Check if required directories exist
    if not os.path.exists(config.IMAGES_DIR):
        print(f"ERROR: Images directory not found: {config.IMAGES_DIR}")
        return
    
    if args.mode == 'train':
        train_model(config)
    
    elif args.mode == 'finetune':
        finetune_model(config, new_data_only=args.new_data_only, freeze_layers=args.freeze_layers)
    
    elif args.mode == 'evaluate':
        if os.path.exists(config.EMBEDDINGS_SAVE_PATH):
            evaluate_model(config, threshold=args.threshold)
        else:
            print("No trained model found. Please train the model first.")
    
    elif args.mode == 'both':
        train_model(config)
        if os.path.exists(config.EMBEDDINGS_SAVE_PATH):
            evaluate_model(config, threshold=args.threshold)


if __name__ == "__main__":
    main()
