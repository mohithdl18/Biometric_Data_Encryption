"""
Add New Faces Script
Automates adding new face images to the training pipeline.
"""

import os
import shutil
import random
import argparse
import pandas as pd
from collections import defaultdict
from datetime import datetime


class AddNewFaces:
    """Handles adding new faces to the dataset and generating training pairs."""
    
    def __init__(self, source_dir, detected_faces_dir, train_csv, test_csv):
        self.source_dir = source_dir
        self.detected_faces_dir = detected_faces_dir
        self.train_csv = train_csv
        self.test_csv = test_csv
        
        # Track new pairs for incremental training
        self.new_pairs_file = os.path.join(os.path.dirname(train_csv), 'new_pairs.csv')
        
    def extract_person_name(self, filename):
        """Extract person name from filename (e.g., 'John_Doe_0001.jpg' -> 'John_Doe')."""
        name = os.path.splitext(filename)[0]
        parts = name.rsplit('_', 1)
        if len(parts) > 1 and parts[1].isdigit():
            name = parts[0]
        return name
    
    def scan_new_images(self):
        """Scan source folder for new face images."""
        if not os.path.exists(self.source_dir):
            raise FileNotFoundError(f"Source directory not found: {self.source_dir}")
        
        image_extensions = ('.jpg', '.jpeg', '.png', '.bmp')
        images = [f for f in os.listdir(self.source_dir) 
                  if f.lower().endswith(image_extensions)]
        
        if not images:
            raise ValueError(f"No images found in {self.source_dir}")
        
        # Group by person
        person_images = defaultdict(list)
        for img in images:
            person_name = self.extract_person_name(img)
            person_images[person_name].append(img)
        
        return dict(person_images)
    
    def get_existing_images(self):
        """Get list of existing images in Detected Faces folder."""
        if not os.path.exists(self.detected_faces_dir):
            raise FileNotFoundError(f"Detected Faces directory not found: {self.detected_faces_dir}")
        
        image_extensions = ('.jpg', '.jpeg', '.png', '.bmp')
        return [f for f in os.listdir(self.detected_faces_dir) 
                if f.lower().endswith(image_extensions)]
    
    def get_existing_pairs(self):
        """Load existing pairs from CSV files."""
        existing_pairs = set()
        
        for csv_file in [self.train_csv, self.test_csv]:
            if os.path.exists(csv_file):
                try:
                    df = pd.read_csv(csv_file)
                    for _, row in df.iterrows():
                        # Store both orderings to avoid duplicates
                        pair1 = (row['Image1'], row['Image2'])
                        pair2 = (row['Image2'], row['Image1'])
                        existing_pairs.add(pair1)
                        existing_pairs.add(pair2)
                except Exception as e:
                    print(f"Warning: Could not read {csv_file}: {e}")
        
        return existing_pairs
    
    def copy_images(self, person_images, dry_run=False):
        """Copy images from source to Detected Faces folder."""
        copied = []
        skipped = []
        errors = []
        
        existing_images = set(self.get_existing_images())
        
        for person, images in person_images.items():
            for img in images:
                src_path = os.path.join(self.source_dir, img)
                dst_path = os.path.join(self.detected_faces_dir, img)
                
                if img in existing_images:
                    skipped.append(img)
                    continue
                
                if dry_run:
                    copied.append(img)
                else:
                    try:
                        shutil.copy2(src_path, dst_path)
                        copied.append(img)
                    except Exception as e:
                        errors.append((img, str(e)))
        
        return copied, skipped, errors
    
    def generate_similar_pairs(self, person_images):
        """Generate similar pairs (same person, different images)."""
        similar_pairs = []
        
        for person, images in person_images.items():
            if len(images) < 2:
                continue
            
            # Create pairs from all combinations
            for i in range(len(images)):
                for j in range(i + 1, len(images)):
                    similar_pairs.append({
                        'Image1': images[i],
                        'Image2': images[j],
                        'class': 'similar',
                        'face_present': 'Yes'
                    })
        
        return similar_pairs
    
    def generate_different_pairs(self, person_images, pairs_per_image=10):
        """Generate different pairs (different people)."""
        different_pairs = []
        existing_pairs = self.get_existing_pairs()
        
        # Get all existing images for pairing
        all_existing = self.get_existing_images()
        
        # Get new image filenames
        new_images = []
        for images in person_images.values():
            new_images.extend(images)
        
        # Remove new images from existing pool to avoid self-pairing
        existing_pool = [img for img in all_existing if img not in new_images]
        
        if not existing_pool:
            print("Warning: No existing images to pair with. Using new images for different pairs.")
            # Pair new people with each other
            all_new_people = list(person_images.keys())
            for person, images in person_images.items():
                other_people = [p for p in all_new_people if p != person]
                for img in images:
                    pairs_created = 0
                    random.shuffle(other_people)
                    for other_person in other_people:
                        if pairs_created >= pairs_per_image:
                            break
                        other_img = random.choice(person_images[other_person])
                        pair = (img, other_img)
                        if pair not in existing_pairs and (other_img, img) not in existing_pairs:
                            different_pairs.append({
                                'Image1': img,
                                'Image2': other_img,
                                'class': 'different',
                                'face_present': 'Yes'
                            })
                            existing_pairs.add(pair)
                            pairs_created += 1
            return different_pairs
        
        # Generate pairs with existing images
        for person, images in person_images.items():
            for img in images:
                pairs_created = 0
                attempts = 0
                max_attempts = pairs_per_image * 3
                
                while pairs_created < pairs_per_image and attempts < max_attempts:
                    attempts += 1
                    other_img = random.choice(existing_pool)
                    
                    # Check it's not the same person
                    other_person = self.extract_person_name(other_img)
                    if other_person == person:
                        continue
                    
                    # Check pair doesn't already exist
                    pair = (img, other_img)
                    if pair in existing_pairs or (other_img, img) in existing_pairs:
                        continue
                    
                    different_pairs.append({
                        'Image1': img,
                        'Image2': other_img,
                        'class': 'different',
                        'face_present': 'Yes'
                    })
                    existing_pairs.add(pair)
                    pairs_created += 1
        
        return different_pairs
    
    def split_pairs(self, pairs, train_split=0.8):
        """Split pairs into train and test sets."""
        random.shuffle(pairs)
        split_idx = int(len(pairs) * train_split)
        return pairs[:split_idx], pairs[split_idx:]
    
    def append_to_csv(self, pairs, csv_file, dry_run=False):
        """Append pairs to CSV file."""
        if not pairs:
            return 0
        
        new_df = pd.DataFrame(pairs)
        
        if dry_run:
            return len(pairs)
        
        try:
            if os.path.exists(csv_file):
                # Append to existing file
                existing_df = pd.read_csv(csv_file)
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                combined_df.to_csv(csv_file, index=False)
            else:
                # Create new file
                new_df.to_csv(csv_file, index=False)
            
            return len(pairs)
        except Exception as e:
            raise IOError(f"Failed to write to {csv_file}: {e}")
    
    def save_new_pairs(self, pairs, dry_run=False):
        """Save new pairs to separate file for incremental training."""
        if not pairs or dry_run:
            return
        
        new_df = pd.DataFrame(pairs)
        new_df['date_added'] = datetime.now().isoformat()
        
        try:
            if os.path.exists(self.new_pairs_file):
                existing_df = pd.read_csv(self.new_pairs_file)
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                combined_df.to_csv(self.new_pairs_file, index=False)
            else:
                new_df.to_csv(self.new_pairs_file, index=False)
        except Exception as e:
            print(f"Warning: Could not save new pairs file: {e}")
    
    def run(self, pairs_per_image=10, train_split=0.8, dry_run=False):
        """Execute the full process of adding new faces."""
        results = {
            'success': False,
            'new_people': [],
            'images_copied': 0,
            'images_skipped': 0,
            'similar_pairs': 0,
            'different_pairs': 0,
            'train_pairs': 0,
            'test_pairs': 0,
            'errors': []
        }
        
        try:
            # Step 1: Scan new images
            print(f"\nScanning {self.source_dir} for new images...")
            person_images = self.scan_new_images()
            
            total_images = sum(len(imgs) for imgs in person_images.values())
            print(f"Found {total_images} images of {len(person_images)} people:")
            
            for person, images in person_images.items():
                can_similar = "← Can create similar pairs!" if len(images) >= 2 else ""
                print(f"  - {person} ({len(images)} images) {can_similar}")
                results['new_people'].append({
                    'name': person,
                    'images': len(images),
                    'can_create_similar': len(images) >= 2
                })
            
            # Step 2: Copy images
            print(f"\n{'[DRY RUN] ' if dry_run else ''}Copying images to {self.detected_faces_dir}...")
            copied, skipped, copy_errors = self.copy_images(person_images, dry_run)
            
            results['images_copied'] = len(copied)
            results['images_skipped'] = len(skipped)
            
            if copied:
                print(f"  Copied: {len(copied)} images")
            if skipped:
                print(f"  Skipped (already exist): {len(skipped)} images")
            if copy_errors:
                for img, err in copy_errors:
                    print(f"  Error copying {img}: {err}")
                    results['errors'].append(f"Copy error - {img}: {err}")
            
            # Step 3: Generate pairs
            print(f"\n{'[DRY RUN] ' if dry_run else ''}Generating pairs...")
            
            similar_pairs = self.generate_similar_pairs(person_images)
            different_pairs = self.generate_different_pairs(person_images, pairs_per_image)
            
            results['similar_pairs'] = len(similar_pairs)
            results['different_pairs'] = len(different_pairs)
            
            print(f"  Similar pairs: {len(similar_pairs)}")
            print(f"  Different pairs: {len(different_pairs)}")
            
            all_pairs = similar_pairs + different_pairs
            
            if not all_pairs:
                print("\nNo new pairs to add.")
                results['success'] = True
                return results
            
            # Step 4: Split and save
            train_pairs, test_pairs = self.split_pairs(all_pairs, train_split)
            
            print(f"\n{'[DRY RUN] ' if dry_run else ''}Updating CSV files...")
            print(f"  Train pairs: {len(train_pairs)} → {self.train_csv}")
            print(f"  Test pairs: {len(test_pairs)} → {self.test_csv}")
            
            results['train_pairs'] = self.append_to_csv(train_pairs, self.train_csv, dry_run)
            results['test_pairs'] = self.append_to_csv(test_pairs, self.test_csv, dry_run)
            
            # Save new pairs for incremental training
            self.save_new_pairs(all_pairs, dry_run)
            
            results['success'] = True
            
            if not dry_run:
                print(f"\n✓ Files updated successfully!")
                print(f"\nNew pairs saved to: {self.new_pairs_file}")
                print(f"\nTo fine-tune the model with new data, run:")
                print(f"  python train_face_recognition.py --mode finetune --epochs 10")
            else:
                print(f"\n[DRY RUN] No files were modified.")
            
        except FileNotFoundError as e:
            results['errors'].append(str(e))
            print(f"\nError: {e}")
        except ValueError as e:
            results['errors'].append(str(e))
            print(f"\nError: {e}")
        except IOError as e:
            results['errors'].append(str(e))
            print(f"\nError: {e}")
        except Exception as e:
            results['errors'].append(f"Unexpected error: {e}")
            print(f"\nUnexpected error: {e}")
        
        return results


def main():
    parser = argparse.ArgumentParser(description='Add new faces to training dataset')
    parser.add_argument('--source', type=str, default='new',
                        help='Source folder containing new face images (default: new)')
    parser.add_argument('--detected_faces', type=str, default='Detected Faces',
                        help='Detected Faces folder (default: Detected Faces)')
    parser.add_argument('--train_csv', type=str, default='train.csv',
                        help='Training CSV file (default: train.csv)')
    parser.add_argument('--test_csv', type=str, default='test.csv',
                        help='Test CSV file (default: test.csv)')
    parser.add_argument('--pairs_per_image', type=int, default=10,
                        help='Number of different pairs to create per new image (default: 10)')
    parser.add_argument('--train_split', type=float, default=0.8,
                        help='Fraction of pairs for training (default: 0.8)')
    parser.add_argument('--dry_run', action='store_true',
                        help='Preview changes without modifying files')
    parser.add_argument('--retrain', action='store_true',
                        help='Automatically start fine-tuning after adding')
    
    args = parser.parse_args()
    
    # Get base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Resolve paths
    source_dir = os.path.join(base_dir, args.source) if not os.path.isabs(args.source) else args.source
    detected_faces_dir = os.path.join(base_dir, args.detected_faces) if not os.path.isabs(args.detected_faces) else args.detected_faces
    train_csv = os.path.join(base_dir, args.train_csv) if not os.path.isabs(args.train_csv) else args.train_csv
    test_csv = os.path.join(base_dir, args.test_csv) if not os.path.isabs(args.test_csv) else args.test_csv
    
    print("=" * 60)
    print("ADD NEW FACES TO TRAINING DATASET")
    print("=" * 60)
    
    if args.dry_run:
        print("\n*** DRY RUN MODE - No files will be modified ***\n")
    
    # Run the process
    adder = AddNewFaces(source_dir, detected_faces_dir, train_csv, test_csv)
    results = adder.run(
        pairs_per_image=args.pairs_per_image,
        train_split=args.train_split,
        dry_run=args.dry_run
    )
    
    # Trigger retraining if requested
    if args.retrain and results['success'] and not args.dry_run:
        print("\n" + "=" * 60)
        print("STARTING FINE-TUNING")
        print("=" * 60)
        
        import subprocess
        train_script = os.path.join(base_dir, 'train_face_recognition.py')
        subprocess.run(['python', train_script, '--mode', 'finetune', '--epochs', '10'])
    
    return 0 if results['success'] else 1


if __name__ == '__main__':
    exit(main())
