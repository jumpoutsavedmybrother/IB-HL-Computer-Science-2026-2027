import cv2
import numpy as np
import mediapipe as mp

class TennisFeatureExtractor:
    """
    Handles frame-by-frame pose extraction and kinematic 
    feature derivation using MediaPipe BlazePose.
    """
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    @staticmethod
    def calculate_angle(a, b, c):
        """Calculates 3D angle between three spatial joint positions (in degrees)."""
        a, b, c = np.array(a), np.array(b), np.array(c)
        ba = a - b
        bc = c - b
        
        cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
        angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
        return np.degrees(angle)

    def extract_frame_landmarks(self, frame):
        """Extracts raw pose keypoints from a single frame."""
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(image_rgb)
        
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            return landmarks
        return None

    def extract_clip_features(self, video_path):
        """
        Parses a video file frame-by-frame to compute aggregate 
        kinematic joint angles and normalized spatial displacements.
        """
        cap = cv2.VideoCapture(video_path)
        frame_features = []

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            landmarks = self.extract_frame_landmarks(frame)
            if landmarks:
                # Extract joint coordinates (x, y, z)
                r_shoulder = [landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x,
                              landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y,
                              landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value].z]
                r_elbow = [landmarks[self.mp_pose.PoseLandmark.RIGHT_ELBOW.value].x,
                           landmarks[self.mp_pose.PoseLandmark.RIGHT_ELBOW.value].y,
                           landmarks[self.mp_pose.PoseLandmark.RIGHT_ELBOW.value].z]
                r_wrist = [landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST.value].x,
                           landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST.value].y,
                           landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST.value].z]
                r_hip = [landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP.value].x,
                         landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP.value].y,
                         landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP.value].z]
                
                # Derive 3D Kinematic Features
                elbow_angle = self.calculate_angle(r_shoulder, r_elbow, r_wrist)
                shoulder_angle = self.calculate_angle(r_hip, r_shoulder, r_elbow)
                wrist_elevation = r_shoulder[1] - r_wrist[1]  # Vertical spatial delta
                
                frame_features.append([elbow_angle, shoulder_angle, wrist_elevation])

        cap.release()

        if len(frame_features) > 0:
            # Aggregate temporal statistics (Mean, Max, Std per feature)
            mean_feats = np.mean(frame_features, axis=0)
            max_feats = np.max(frame_features, axis=0)
            std_feats = np.std(frame_features, axis=0)
            return np.hstack([mean_feats, max_feats, std_feats])  # 9 continuous features
        return None
