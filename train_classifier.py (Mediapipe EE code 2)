import os
import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from feature_extractor import TennisFeatureExtractor

DATASET_PATH = "./dataset"
MODEL_OUTPUT_PATH = "tennis_swing_classifier.pkl"

def build_dataset(dataset_path):
    """Iterates through stroke subdirectories to build feature matrix X and label vector y."""
    extractor = TennisFeatureExtractor()
    X, y = [], []
    
    # Class mapping: 0=Forehand, 1=Backhand, 2=Serve
    categories = {'forehand': 0, 'backhand': 1, 'overhand': 2, 'serve': 2}
    
    for category, label in categories.items():
        category_dir = os.path.join(dataset_path, category)
        if not os.path.exists(category_dir):
            continue
            
        print(f"Processing clips for: {category.upper()}..")
        for file_name in os.listdir(category_dir):
            if file_name.endswith(('.mp4', '.avi', '.mov')):
                video_path = os.path.join(category_dir, file_name)
                features = extractor.extract_clip_features(video_path)
                
                if features is not None:
                    X.append(features)
                    y.append(label)
                    
    return np.array(X), np.array(y)

def main():
    # 1. Feature Extraction Pipeline
    X, y = build_dataset(DATASET_PATH)
    print(f"\nDataset Built: {X.shape[0]} samples, {X.shape[1]} features per sample.")

    # 2. Stratified Train / Test Split (80% Train, 20% Test)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    # 3. Train Random Forest Classifier
    clf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    clf.fit(X_train, y_train)

    # 4. Model Evaluation
    y_pred = clf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred) * 100

    print("\n" + "="*40)
    print(f"Overall Model Accuracy: {accuracy:.2f}%")
    print("="*40)
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Forehand', 'Backhand', 'Serve']))

    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    # 5. Serialize Model Artifact
    joblib.dump(clf, MODEL_OUTPUT_PATH)
    print(f"\nModel saved to '{MODEL_OUTPUT_PATH}'")

if __name__ == "__main__":
    main()
