# Future Enhancement: Adding New Faces to Training

This document explains how to add new faces from the `new/` folder into the training pipeline.

## Current State

```
new/
├── jeevan_0001.jpg
├── jeevan_0002.jpg
├── kushwith_0001.jpg
├── kushwith_0002.jpg
├── mohith_0001.jpg
├── mohith_0002.jpg
├── patil_0001.jpg
├── patil_0002.jpg
├── yashaswi_0001.jpg
└── yashaswi_0002.jpg
```

These images need to be:
1. Added to `Detected Faces/` folder
2. Added to `train.csv` and `test.csv` with appropriate pairs
3. Model retrained with the new data

---

## Step-by-Step Process

### Step 1: Copy Images to Detected Faces

Move/copy all images from `new/` to `Detected Faces/`:

```
new/mohith_0001.jpg  →  Detected Faces/mohith_0001.jpg
new/jeevan_0001.jpg  →  Detected Faces/jeevan_0001.jpg
...
```

### Step 2: Generate Pairs for CSV Files

For each new person, create pairs:

#### Similar Pairs (same person)
If a person has multiple images:
```csv
mohith_0001.jpg,mohith_0002.jpg,similar,Yes
```

#### Different Pairs (different people)
Pair new faces with existing faces:
```csv
mohith_0001.jpg,Adam_Sandler_0001.jpg,different,Yes
jeevan_0001.jpg,Aaron_Peirsol_0001.jpg,different,Yes
```

### Step 3: Update CSV Files

Append new pairs to:
- `train.csv` (80% of new pairs)
- `test.csv` (20% of new pairs)

### Step 4: Retrain Model

```bash
python train_face_recognition.py --mode train --epochs 50 --batch_size 32
```

---

## Proposed Script: `add_new_faces.py`

A script that automates this process:

```
python add_new_faces.py --source new/ --pairs_per_person 10 --train_split 0.8
```

### What the Script Should Do

1. **Scan `new/` folder** for new face images

2. **Copy images** to `Detected Faces/`

3. **Generate similar pairs** (if multiple images of same person exist)

4. **Generate different pairs** by:
   - Randomly selecting existing faces from `Detected Faces/`
   - Creating pairs with new faces
   - Ensuring balanced similar/different ratio

5. **Split pairs** into train (80%) and test (20%)

6. **Append to CSV files** without duplicating existing pairs

7. **Optional: Trigger retraining**

### Script Parameters

| Parameter | Description |
|-----------|-------------|
| `--source` | Folder with new faces (default: `new/`) |
| `--pairs_per_person` | Number of different pairs to create per new face |
| `--train_split` | Fraction for training (default: 0.8) |
| `--retrain` | Automatically start retraining after adding |
| `--dry_run` | Preview changes without modifying files |

### Example Output

```
Found 10 new faces in new/
- jeevan (2 images) ← Can create similar pairs!
- kushwith (2 images) ← Can create similar pairs!
- mohith (2 images) ← Can create similar pairs!
- patil (2 images) ← Can create similar pairs!
- yashaswi (2 images) ← Can create similar pairs!

Copying images to Detected Faces/... Done

Generating pairs:
- Similar pairs: 5 (1 per person with multiple images)
- Different pairs: 50 (10 per new face)

Splitting pairs:
- Train: 44 pairs → train.csv
- Test: 11 pairs → test.csv

Files updated successfully!

To fine-tune the model with new data, run:
python train_face_recognition.py --mode finetune --epochs 10 --new_data_only
```

---

## Handling Edge Cases

### Single Image Per Person
- Cannot create "similar" pairs
- Only "different" pairs with other people
- **Recommendation**: Add at least 2 images per person for better training

### Multiple Images Per Person (Current State)
- Can create "similar" pairs (same person, different images)
- Better training quality
- Model learns facial variations (angles, lighting, expressions)

### Duplicate Detection
- Check if image already exists in `Detected Faces/`
- Check if pair already exists in CSV files
- Skip duplicates, log warnings

### Name Extraction
- Extract person name from filename: `firstname_lastname_XXXX.jpg`
- Handle variations: `John_Doe_0001.jpg` → "John Doe"

---

## CSV Format Reference

```csv
Image1,Image2,class,face_present
mohith_0001.jpg,Adam_Sandler_0001.jpg,different,Yes
mohith_0001.jpg,mohith_0002.jpg,similar,Yes
```

| Column | Values | Description |
|--------|--------|-------------|
| Image1 | filename | First image filename |
| Image2 | filename | Second image filename |
| class | `similar` / `different` | Same or different person |
| face_present | `Yes` / `No` | Whether face is clearly visible |

---

## Retraining Options

### Incremental Training (Recommended)

Continue training the existing model with only the new data. This is faster and preserves what the model has already learned.

```bash
python train_face_recognition.py --mode finetune --epochs 10 --new_data_only
```

#### How Incremental Training Works

1. **Load Existing Model**: Load `face_embeddings_model.keras` with all its learned weights
2. **Freeze Early Layers**: Keep the base feature extraction layers frozen
3. **Train on New Pairs Only**: Only use the newly added pairs from CSV files
4. **Lower Learning Rate**: Use a smaller learning rate (e.g., 0.00001) to avoid overwriting existing knowledge
5. **Save Updated Model**: Overwrite or version the model file

#### Benefits
- **Faster**: Only processes new images, not the entire dataset
- **Preserves Knowledge**: Doesn't forget previously learned faces
- **Less Resources**: Requires less memory and compute time

#### Script Parameters for Fine-tuning

| Parameter | Description |
|-----------|-------------|
| `--mode finetune` | Enable incremental training mode |
| `--epochs` | Number of epochs for fine-tuning (default: 10) |
| `--new_data_only` | Only train on newly added pairs |
| `--lr` | Learning rate (default: 0.00001 for fine-tuning) |
| `--freeze_layers` | Number of base model layers to freeze (default: all except last 10) |

#### Example Workflow

```bash
# Step 1: Add new faces to database
python add_new_faces.py --source new/ --pairs_per_person 10

# Step 2: Fine-tune model with new data only
python train_face_recognition.py --mode finetune --epochs 10 --new_data_only --lr 0.00001
```

#### What Happens Internally

```
┌─────────────────────────────┐
│  Existing Model             │
│  face_embeddings_model.keras│
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Load Weights               │
│  (All learned features)     │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Freeze Base Layers         │
│  (MobileNetV2 early layers) │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Train on New Pairs Only    │
│  - New similar pairs        │
│  - New different pairs      │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Save Updated Model         │
│  face_embeddings_model.keras│
└─────────────────────────────┘
```

#### Tracking New vs Old Data

The script should track which pairs are new:
- Add a `date_added` column to CSV files, OR
- Keep a separate file `new_pairs.csv` for incremental training
- After successful training, merge into main CSV files

---

### Full Retrain (Not Recommended for Updates)

Train from scratch with all data. Only use this if:
- Model is corrupted
- Major architecture changes needed
- Starting fresh

```bash
python train_face_recognition.py --mode train --epochs 50
```

**Warning**: This takes longer and loses any fine-tuned optimizations.

---

## Workflow Summary

```
┌─────────────────┐
│   new/ folder   │
│  (new images)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ add_new_faces.py│
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐  ┌──────────┐
│ Copy  │  │ Generate │
│ to    │  │ pairs    │
│Detected│ │          │
│ Faces │  └────┬─────┘
└───────┘       │
           ┌────┴────┐
           ▼         ▼
      ┌─────────┐ ┌─────────┐
      │train.csv│ │test.csv │
      └────┬────┘ └────┬────┘
           │           │
           └─────┬─────┘
                 ▼
         ┌──────────────┐
         │   Retrain    │
         │    Model     │
         └──────────────┘
                 │
                 ▼
         ┌──────────────┐
         │face_embeddings│
         │_model.keras  │
         └──────────────┘
```

---

## Notes

- **Minimum pairs**: More pairs = better training, aim for 10+ pairs per new person
- **Balance**: Keep similar/different ratio balanced (~50/50)
- **Quality**: Ensure new images are clear, well-lit face photos
- **Backup**: Back up CSV files before modifying
