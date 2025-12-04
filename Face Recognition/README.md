# Face Recognition System

A face recognition system using Siamese Networks with Triplet Loss. This system can identify faces, verify if two faces belong to the same person, and perform real-time face recognition via webcam.

## Project Structure

```
Face Recognition/
├── train_face_recognition.py    # Training pipeline
├── predict_face.py              # Prediction/identification script
├── realtime_recognition.py      # Real-time webcam face recognition
├── add_new_faces.py             # Add new faces to training dataset
├── face_embeddings_model.keras  # Trained model (generated after training)
├── train.csv                    # Training data pairs
├── test.csv                     # Test data pairs
├── Detected Faces/              # Database of known faces
├── new/                         # New faces to add
├── README.md
└── future.md                    # Future enhancements documentation
```

## How It Works

### Training (`train_face_recognition.py`)

1. **Data Loading**: Reads image pairs from `train.csv` and `test.csv`
2. **Triplet Creation**: Creates triplets (anchor, positive, negative) from pairs
   - Anchor & Positive: Same person
   - Anchor & Negative: Different person
3. **Model Training**: Trains a Siamese Network using triplet loss
4. **Model Saving**: Saves the embedding model to `face_embeddings_model.keras`

### Prediction (`predict_face.py`)

1. **Model Loading**: Loads the trained embedding model
2. **Database Building**: Creates embeddings for all faces in `Detected Faces/` folder
3. **Face Matching**: Compares query face embedding with database embeddings
4. **Result**: Returns the closest matching person(s)

### Real-time Recognition (`realtime_recognition.py`)

1. **Webcam Capture**: Opens webcam and captures frames
2. **Face Detection**: Detects faces using Haar Cascade
3. **Recognition**: Recognizes each detected face using the trained model
4. **Display**: Shows live video with bounding boxes and names

## Model Files

| File | Description |
|------|-------------|
| `face_embeddings_model.keras` | The trained model that converts face images to 128-dimensional embeddings |

The model takes a 160x160 RGB image and outputs a 128-dimensional vector (embedding) that represents the face.

## Usage

### Training a New Model

```bash
python train_face_recognition.py --mode train --epochs 50 --batch_size 32
```

### Identifying a Face

```bash
python predict_face.py --mode predict --image "path/to/face.jpg"
```

**With cosine similarity (recommended):**
```bash
python predict_face.py --mode predict --image "new/person.jpg" --threshold 0.9 --use_cosine
```

### Verifying Two Faces

Check if two images are the same person:

```bash
python predict_face.py --mode verify --image1 "face1.jpg" --image2 "face2.jpg" --threshold 0.9
```

### Building a Face Database

Pre-compute embeddings for faster predictions:

```bash
# Build and save database
python predict_face.py --mode build_db --save_db "face_database.npy"

# Use saved database for prediction
python predict_face.py --mode predict --image "query.jpg" --load_db "face_database.npy"
```

### Real-time Face Recognition

Run face recognition using your webcam:

```bash
# Basic usage
python realtime_recognition.py

# With custom threshold
python realtime_recognition.py --threshold 0.85

# Use Euclidean distance instead of cosine similarity
python realtime_recognition.py --use_euclidean --threshold 6.0

# Specify camera (if multiple cameras)
python realtime_recognition.py --camera 1
```

**Controls during real-time recognition:**
- `q` - Quit
- `+` / `-` - Increase/Decrease threshold
- `s` - Save current frame
- `r` - Rebuild face database

### Adding New Faces

Add new people to the training database:

```bash
# Preview what will be added (dry run)
python add_new_faces.py --dry_run

# Add new faces
python add_new_faces.py

# Add and automatically retrain
python add_new_faces.py --retrain
```

### Fine-tuning with New Data

Incrementally train the model with new faces (faster than full retrain):

```bash
python train_face_recognition.py --mode finetune --epochs 10 --new_data_only
```

## Command Options

### predict_face.py

| Option | Default | Description |
|--------|---------|-------------|
| `--mode` | required | `predict`, `verify`, or `build_db` |
| `--image` | - | Query image path (for predict mode) |
| `--image1`, `--image2` | - | Image paths (for verify mode) |
| `--model` | `face_embeddings_model.keras` | Path to trained model |
| `--database_dir` | `Detected Faces` | Folder with known faces |
| `--threshold` | `0.5` | Matching threshold |
| `--use_cosine` | False | Use cosine similarity instead of Euclidean distance |
| `--top_k` | `5` | Number of top matches to show |
| `--save_db` | - | Save embeddings database to file |
| `--load_db` | - | Load pre-computed embeddings |

### train_face_recognition.py

| Option | Default | Description |
|--------|---------|-------------|
| `--mode` | required | `train`, `evaluate`, `finetune`, or `both` |
| `--epochs` | `50` | Number of training epochs |
| `--batch_size` | `32` | Batch size |
| `--learning_rate` | `0.0001` | Learning rate |
| `--threshold` | `1.5` | Distance threshold for evaluation |
| `--new_data_only` | False | Train only on new data (finetune mode) |
| `--freeze_layers` | `100` | Layers to freeze in finetune mode |

### realtime_recognition.py

| Option | Default | Description |
|--------|---------|-------------|
| `--model` | `face_embeddings_model.keras` | Path to trained model |
| `--database_dir` | `Detected Faces` | Folder with known faces |
| `--threshold` | `0.9` | Recognition threshold |
| `--camera` | `0` | Camera device ID |
| `--use_euclidean` | False | Use Euclidean distance instead of cosine |
| `--load_db` | - | Load pre-computed embeddings |

### add_new_faces.py

| Option | Default | Description |
|--------|---------|-------------|
| `--source` | `new` | Folder with new face images |
| `--pairs_per_image` | `10` | Different pairs to create per image |
| `--train_split` | `0.8` | Fraction for training data |
| `--dry_run` | False | Preview without modifying files |
| `--retrain` | False | Auto-start fine-tuning after adding |

## How Matching Works

1. **Embedding**: Each face is converted to a 128-dimensional vector
2. **Comparison**: Query embedding is compared with all database embeddings
3. **Distance/Similarity**: 
   - **Euclidean Distance**: Lower = more similar
   - **Cosine Similarity**: Higher = more similar (use `--use_cosine`)
4. **Threshold**: If distance/similarity meets threshold, face is identified

## Face Naming Convention

Person names are extracted from filenames:
- `John_Doe_0001.jpg` → **John Doe**
- `Jane_Smith_0002.jpg` → **Jane Smith**

## Adding New People to Database

1. Add face images to `Detected Faces/` folder
2. Name format: `FirstName_LastName_XXXX.jpg` (e.g., `John_Doe_0001.jpg`)
3. Run prediction - database rebuilds automatically

Or save the database after adding:
```bash
python predict_face.py --mode build_db --save_db "face_database.npy"
```

## Output Examples

### Prediction Output
```
============================================================
FACE RECOGNITION PREDICTION
============================================================

Query Image: new/unknown_face.jpg
Using: Cosine Similarity

────────────────────────────────────────
✓ IDENTIFIED: John Doe
Distance: 0.9521
Threshold: 0.9

────────────────────────────────────────
Top 5 Matches:
────────────────────────────────────────
✓ 1. John Doe
      Distance: 0.9521 (avg: 0.9234)
      Samples in DB: 3
```

### Verification Output
```
============================================================
FACE VERIFICATION
============================================================

Image 1: face1.jpg
Image 2: face2.jpg

────────────────────────────────────────
✓ SAME PERSON

Euclidean Distance: 5.2341
Cosine Similarity: 0.9456
Threshold: 8.0
```

## Requirements

- Python 3.8+
- TensorFlow 2.x
- NumPy
- Pillow
- tqdm
- pandas

Install dependencies:
```bash
pip install tensorflow numpy pillow tqdm pandas
```

## Tips

1. **Threshold Tuning**: Start with default and adjust based on results
2. **Multiple Images**: Add multiple images per person for better accuracy
3. **Image Quality**: Use clear, well-lit face images
4. **Pre-build Database**: Use `--save_db` for large databases to speed up predictions
