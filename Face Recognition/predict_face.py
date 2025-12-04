"""
Face Recognition Prediction Script
Uses the trained Siamese Network model to identify/verify faces.
"""

import os
import numpy as np
import tensorflow as tf
from tensorflow import keras
from PIL import Image
import argparse
from collections import defaultdict
from tqdm import tqdm


class FaceRecognizer:
    """Face recognition using trained Siamese Network embeddings."""
    
    def __init__(self, model_path, database_dir, img_size=(160, 160)):
        """
        Initialize the face recognizer.
        
        Args:
            model_path: Path to the trained embedding model (.keras file)
            database_dir: Directory containing face images for the database
            img_size: Input image size for the model
        """
        self.img_size = img_size
        self.model_path = model_path
        self.database_dir = database_dir
        
        # Load the embedding model
        print(f"Loading model from {model_path}...")
        self.model = keras.models.load_model(model_path)
        print("Model loaded successfully!")
        
        # Database to store embeddings
        self.embeddings_db = {}  # {person_name: [list of embeddings]}
        self.image_embeddings = {}  # {image_path: embedding}
        
    def preprocess_image(self, image_path):
        """Load and preprocess an image for the model."""
        try:
            img = Image.open(image_path).convert('RGB')
            img = img.resize(self.img_size)
            img_array = np.array(img) / 255.0
            return img_array
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
            return None
    
    def get_embedding(self, image_path):
        """Get the embedding vector for an image."""
        img = self.preprocess_image(image_path)
        if img is None:
            return None
        
        # Add batch dimension
        img_batch = np.expand_dims(img, axis=0)
        
        # Get embedding
        embedding = self.model.predict(img_batch, verbose=0)
        return embedding[0]
    
    def extract_person_name(self, filename):
        """Extract person name from filename (e.g., 'John_Doe_0001.jpg' -> 'John Doe')."""
        # Remove extension
        name = os.path.splitext(filename)[0]
        # Remove the number suffix (e.g., _0001)
        parts = name.rsplit('_', 1)
        if len(parts) > 1 and parts[1].isdigit():
            name = parts[0]
        # Replace underscores with spaces
        name = name.replace('_', ' ')
        return name
    
    def build_database(self, max_images_per_person=None):
        """
        Build a database of face embeddings from the database directory.
        
        Args:
            max_images_per_person: Maximum number of images to use per person (None for all)
        """
        print(f"\nBuilding face database from {self.database_dir}...")
        
        # Get all image files
        image_files = [f for f in os.listdir(self.database_dir) 
                       if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        # Group images by person
        person_images = defaultdict(list)
        for img_file in image_files:
            person_name = self.extract_person_name(img_file)
            person_images[person_name].append(img_file)
        
        print(f"Found {len(person_images)} unique people with {len(image_files)} total images")
        
        # Build embeddings
        self.embeddings_db = {}
        
        for person_name, images in tqdm(person_images.items(), desc="Processing people"):
            # Limit images if specified
            if max_images_per_person:
                images = images[:max_images_per_person]
            
            embeddings = []
            for img_file in images:
                img_path = os.path.join(self.database_dir, img_file)
                embedding = self.get_embedding(img_path)
                if embedding is not None:
                    embeddings.append(embedding)
                    self.image_embeddings[img_path] = embedding
            
            if embeddings:
                self.embeddings_db[person_name] = embeddings
        
        print(f"Database built with {len(self.embeddings_db)} people")
        return self.embeddings_db
    
    def compute_distance(self, embedding1, embedding2):
        """Compute Euclidean distance between two embeddings."""
        return np.linalg.norm(embedding1 - embedding2)
    
    def compute_cosine_similarity(self, embedding1, embedding2):
        """Compute cosine similarity between two embeddings."""
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        return dot_product / (norm1 * norm2 + 1e-8)
    
    def predict(self, image_path, threshold=1.0, top_k=5, use_cosine=False):
        """
        Predict the identity of a face in an image.
        
        Args:
            image_path: Path to the query image
            threshold: Distance threshold for recognition (lower = stricter)
            top_k: Number of top matches to return
            use_cosine: Use cosine similarity instead of Euclidean distance
            
        Returns:
            Dictionary with prediction results
        """
        # Get embedding for query image
        query_embedding = self.get_embedding(image_path)
        if query_embedding is None:
            return {"error": "Could not process query image"}
        
        if not self.embeddings_db:
            return {"error": "Database is empty. Call build_database() first."}
        
        # Compare with all people in database
        distances = []
        
        for person_name, embeddings in self.embeddings_db.items():
            # Compute distance to all embeddings of this person
            person_distances = []
            for emb in embeddings:
                if use_cosine:
                    # For cosine, higher is better, so negate for sorting
                    dist = -self.compute_cosine_similarity(query_embedding, emb)
                else:
                    dist = self.compute_distance(query_embedding, emb)
                person_distances.append(dist)
            
            # Use minimum distance (closest match)
            min_dist = min(person_distances)
            avg_dist = np.mean(person_distances)
            
            distances.append({
                'name': person_name,
                'min_distance': min_dist if not use_cosine else -min_dist,
                'avg_distance': avg_dist if not use_cosine else -avg_dist,
                'num_samples': len(embeddings)
            })
        
        # Sort by minimum distance (ascending for Euclidean, descending for cosine)
        if use_cosine:
            distances.sort(key=lambda x: x['min_distance'], reverse=True)
        else:
            distances.sort(key=lambda x: x['min_distance'])
        
        # Get top K matches
        top_matches = distances[:top_k]
        
        # Determine if it's a match based on threshold
        best_match = top_matches[0]
        if use_cosine:
            is_match = best_match['min_distance'] >= threshold
        else:
            is_match = best_match['min_distance'] <= threshold
        
        return {
            'query_image': image_path,
            'predicted_name': best_match['name'] if is_match else "Unknown",
            'is_recognized': is_match,
            'confidence_distance': best_match['min_distance'],
            'top_matches': top_matches,
            'threshold_used': threshold
        }
    
    def verify(self, image1_path, image2_path, threshold=1.0):
        """
        Verify if two images are of the same person.
        
        Args:
            image1_path: Path to first image
            image2_path: Path to second image
            threshold: Distance threshold for verification
            
        Returns:
            Dictionary with verification results
        """
        emb1 = self.get_embedding(image1_path)
        emb2 = self.get_embedding(image2_path)
        
        if emb1 is None or emb2 is None:
            return {"error": "Could not process one or both images"}
        
        distance = self.compute_distance(emb1, emb2)
        cosine_sim = self.compute_cosine_similarity(emb1, emb2)
        
        return {
            'image1': image1_path,
            'image2': image2_path,
            'distance': float(distance),
            'cosine_similarity': float(cosine_sim),
            'is_same_person': distance <= threshold,
            'threshold_used': threshold
        }
    
    def save_database(self, save_path):
        """Save the embeddings database to a file."""
        np.save(save_path, {
            'embeddings_db': self.embeddings_db,
            'image_embeddings': self.image_embeddings
        }, allow_pickle=True)
        print(f"Database saved to {save_path}")
    
    def load_database(self, load_path):
        """Load a pre-computed embeddings database."""
        data = np.load(load_path, allow_pickle=True).item()
        self.embeddings_db = data['embeddings_db']
        self.image_embeddings = data.get('image_embeddings', {})
        print(f"Database loaded with {len(self.embeddings_db)} people")


def main():
    parser = argparse.ArgumentParser(description='Face Recognition Prediction')
    parser.add_argument('--mode', type=str, required=True, 
                        choices=['predict', 'verify', 'build_db'],
                        help='Mode: predict (identify face), verify (compare two faces), build_db (create database)')
    parser.add_argument('--image', type=str, help='Path to query image for prediction')
    parser.add_argument('--image1', type=str, help='First image for verification')
    parser.add_argument('--image2', type=str, help='Second image for verification')
    parser.add_argument('--model', type=str, default='face_embeddings_model.keras',
                        help='Path to trained model')
    parser.add_argument('--database_dir', type=str, default='Detected Faces',
                        help='Directory containing face database images')
    parser.add_argument('--threshold', type=float, default=0.5,
                        help='Threshold for recognition (distance or cosine similarity)')
    parser.add_argument('--top_k', type=int, default=5,
                        help='Number of top matches to show')
    parser.add_argument('--use_cosine', action='store_true',
                        help='Use cosine similarity instead of Euclidean distance')
    parser.add_argument('--max_per_person', type=int, default=None,
                        help='Maximum images per person for database')
    parser.add_argument('--save_db', type=str, default=None,
                        help='Path to save embeddings database')
    parser.add_argument('--load_db', type=str, default=None,
                        help='Path to load pre-computed embeddings database')
    
    args = parser.parse_args()
    
    # Get base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(base_dir, args.model) if not os.path.isabs(args.model) else args.model
    database_dir = os.path.join(base_dir, args.database_dir) if not os.path.isabs(args.database_dir) else args.database_dir
    
    # Initialize recognizer
    recognizer = FaceRecognizer(model_path, database_dir)
    
    # Load or build database
    if args.load_db:
        recognizer.load_database(args.load_db)
    elif args.mode in ['predict', 'build_db']:
        recognizer.build_database(max_images_per_person=args.max_per_person)
        
        if args.save_db:
            recognizer.save_database(args.save_db)
    
    # Execute based on mode
    if args.mode == 'predict':
        if not args.image:
            print("Error: --image is required for predict mode")
            return
        
        image_path = os.path.join(base_dir, args.image) if not os.path.isabs(args.image) else args.image
        
        print(f"\n{'='*60}")
        print("FACE RECOGNITION PREDICTION")
        print(f"{'='*60}")
        
        result = recognizer.predict(image_path, threshold=args.threshold, top_k=args.top_k, use_cosine=args.use_cosine)
        
        if 'error' in result:
            print(f"Error: {result['error']}")
            return
        
        print(f"\nQuery Image: {result['query_image']}")
        print(f"Using: {'Cosine Similarity' if args.use_cosine else 'Euclidean Distance'}")
        print(f"\n{'─'*40}")
        
        if result['is_recognized']:
            print(f"✓ IDENTIFIED: {result['predicted_name']}")
        else:
            print(f"✗ UNKNOWN PERSON (no match below threshold)")
        
        print(f"Distance: {result['confidence_distance']:.4f}")
        print(f"Threshold: {result['threshold_used']}")
        
        print(f"\n{'─'*40}")
        print(f"Top {args.top_k} Matches:")
        print(f"{'─'*40}")
        
        for i, match in enumerate(result['top_matches'], 1):
            status = "✓" if (i == 1 and result['is_recognized']) else " "
            print(f"{status} {i}. {match['name']}")
            print(f"      Distance: {match['min_distance']:.4f} (avg: {match['avg_distance']:.4f})")
            print(f"      Samples in DB: {match['num_samples']}")
        
    elif args.mode == 'verify':
        if not args.image1 or not args.image2:
            print("Error: --image1 and --image2 are required for verify mode")
            return
        
        image1_path = os.path.join(base_dir, args.image1) if not os.path.isabs(args.image1) else args.image1
        image2_path = os.path.join(base_dir, args.image2) if not os.path.isabs(args.image2) else args.image2
        
        print(f"\n{'='*60}")
        print("FACE VERIFICATION")
        print(f"{'='*60}")
        
        result = recognizer.verify(image1_path, image2_path, threshold=args.threshold)
        
        if 'error' in result:
            print(f"Error: {result['error']}")
            return
        
        print(f"\nImage 1: {result['image1']}")
        print(f"Image 2: {result['image2']}")
        print(f"\n{'─'*40}")
        
        if result['is_same_person']:
            print("✓ SAME PERSON")
        else:
            print("✗ DIFFERENT PEOPLE")
        
        print(f"\nEuclidean Distance: {result['distance']:.4f}")
        print(f"Cosine Similarity: {result['cosine_similarity']:.4f}")
        print(f"Threshold: {result['threshold_used']}")
        
    elif args.mode == 'build_db':
        print("\nDatabase built successfully!")
        print(f"Total people: {len(recognizer.embeddings_db)}")
        
        # Show some statistics
        total_embeddings = sum(len(embs) for embs in recognizer.embeddings_db.values())
        print(f"Total embeddings: {total_embeddings}")
        
        if args.save_db:
            print(f"Database saved to: {args.save_db}")


if __name__ == '__main__':
    main()
