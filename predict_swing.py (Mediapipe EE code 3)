import os
import joblib
from feature_extractor import TennisFeatureExtractor

# Serialized Model Artifact and Target Video Path
MODEL_PATH = "tennis_swing_classifier.pkl"
TEST_VIDEO_PATH = "test_clip_1.mp4"

def predict_single_clip(video_path):
    if not os.path.exists(MODEL_PATH):
        print(f"Error: Trained model '{MODEL_PATH}' not found. Run train_classifier.py first.")
        return

    if not os.path.exists(video_path):
        print(f"Error: Target video file '{video_path}' not found.")
        return

    print(f"Loading model '{MODEL_PATH}'...")
    model = joblib.load(MODEL_PATH)
    
    print(f"Extracting kinematic features from '{video_path}'...")
    extractor = TennisFeatureExtractor()
    features = extractor.extract_clip_features(video_path)

    if features is not None:
        class_names = {0: 'Forehand', 1: 'Backhand', 2: 'Serve'}
        
        prediction = model.predict([features])[0]
        probabilities = model.predict_proba([features])[0]
        confidence = max(probabilities) * 100

        print("\n" + "="*35)
        print(f"INFERENCE RESULT: {class_names[prediction].upper()}")
        print(f"CONFIDENCE SCORE: {confidence:.2f}%")
        print("="*35)
        
        print("\nClass Probability Breakdown:")
        for idx, name in class_names.items():
            print(f" - {name}: {probabilities[idx] * 100:.2f}%")
    else:
        print("Error: Failed to extract pose keypoints from the input clip.")

if __name__ == "__main__":
    predict_single_clip(TEST_VIDEO_PATH)
