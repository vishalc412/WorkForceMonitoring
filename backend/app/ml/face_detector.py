"""
Face detection and liveness verification using MediaPipe
"""
import cv2
import numpy as np
import mediapipe as mp
from typing import Dict, Tuple, Optional
import base64
from io import BytesIO
from PIL import Image

from app.config import settings


class FaceDetector:
    """Face detection using MediaPipe Face Detection"""

    def __init__(self):
        """Initialize MediaPipe face detection"""
        self.mp_face_detection = mp.solutions.face_detection
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=1,  # 1 for full range, 0 for short range
            min_detection_confidence=settings.FACE_CONFIDENCE_THRESHOLD
        )

    def detect_faces(self, image: np.ndarray) -> Tuple[bool, int, list]:
        """
        Detect faces in image

        Args:
            image: Input image as numpy array (BGR format)

        Returns:
            Tuple of (face_detected, face_count, detection_results)
        """
        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Detect faces
        results = self.face_detection.process(image_rgb)

        if results.detections:
            face_count = len(results.detections)
            return True, face_count, results.detections
        else:
            return False, 0, []

    def process_base64_image(self, base64_image: str) -> Dict[str, any]:
        """
        Process base64 encoded image for face detection

        Args:
            base64_image: Base64 encoded image (with or without data URI prefix)

        Returns:
            Dictionary with detection results
        """
        try:
            # Remove data URI prefix if present
            if "base64," in base64_image:
                base64_image = base64_image.split("base64,")[1]

            # Decode base64 to image
            image_data = base64.b64decode(base64_image)
            image = Image.open(BytesIO(image_data))

            # Convert PIL image to numpy array
            image_np = np.array(image)

            # Convert RGB to BGR for OpenCV
            if len(image_np.shape) == 3 and image_np.shape[2] == 3:
                image_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
            else:
                return {
                    "face_detected": False,
                    "face_count": 0,
                    "error": "Invalid image format",
                    "rejection_reason": "invalid_format"
                }

            # Detect faces
            face_detected, face_count, detections = self.detect_faces(image_bgr)

            # Validate results
            if not face_detected:
                return {
                    "face_detected": False,
                    "face_count": 0,
                    "rejection_reason": "no_face_detected"
                }

            if face_count > 1:
                return {
                    "face_detected": False,
                    "face_count": face_count,
                    "rejection_reason": "multiple_faces"
                }

            # Get face confidence score
            confidence = detections[0].score[0] if detections else 0.0

            return {
                "face_detected": True,
                "face_count": 1,
                "confidence": float(confidence),
                "rejection_reason": None
            }

        except Exception as e:
            return {
                "face_detected": False,
                "face_count": 0,
                "error": str(e),
                "rejection_reason": "processing_error"
            }

    def close(self):
        """Close face detection resources"""
        self.face_detection.close()


class LivenessDetector:
    """Basic liveness detection to prevent spoofing"""

    def __init__(self):
        """Initialize liveness detector"""
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )

    def check_liveness(self, image: np.ndarray) -> Dict[str, any]:
        """
        Perform basic liveness check

        This is a simplified version. Production systems should use:
        - 3D depth analysis
        - Texture analysis
        - Challenge-response (blink detection, head movement)
        - Passive liveness (moiré pattern detection)

        Args:
            image: Input image as numpy array (BGR format)

        Returns:
            Dictionary with liveness results
        """
        try:
            # Convert BGR to RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Process face mesh
            results = self.face_mesh.process(image_rgb)

            if not results.multi_face_landmarks:
                return {
                    "liveness_verified": False,
                    "liveness_score": 0.0,
                    "reason": "no_face_landmarks"
                }

            # Basic checks for liveness
            landmarks = results.multi_face_landmarks[0]

            # Calculate face depth variation (simplified)
            z_coords = [lm.z for lm in landmarks.landmark]
            z_variance = np.var(z_coords)

            # Calculate brightness variance (real faces have more variation)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            brightness_variance = np.var(gray)

            # Normalized liveness score (0-1)
            # Higher z-variance and brightness variance indicate real face
            liveness_score = min(1.0, (z_variance * 100 + brightness_variance / 1000) / 2)

            # Apply threshold
            is_live = liveness_score >= settings.LIVENESS_THRESHOLD

            return {
                "liveness_verified": is_live,
                "liveness_score": float(liveness_score),
                "z_variance": float(z_variance),
                "brightness_variance": float(brightness_variance)
            }

        except Exception as e:
            return {
                "liveness_verified": False,
                "liveness_score": 0.0,
                "error": str(e),
                "reason": "processing_error"
            }

    def process_base64_image(self, base64_image: str) -> Dict[str, any]:
        """
        Process base64 encoded image for liveness detection

        Args:
            base64_image: Base64 encoded image

        Returns:
            Dictionary with liveness results
        """
        try:
            # Remove data URI prefix if present
            if "base64," in base64_image:
                base64_image = base64_image.split("base64,")[1]

            # Decode base64 to image
            image_data = base64.b64decode(base64_image)
            image = Image.open(BytesIO(image_data))

            # Convert to numpy array
            image_np = np.array(image)

            # Convert RGB to BGR for OpenCV
            if len(image_np.shape) == 3 and image_np.shape[2] == 3:
                image_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
            else:
                return {
                    "liveness_verified": False,
                    "liveness_score": 0.0,
                    "reason": "invalid_format"
                }

            return self.check_liveness(image_bgr)

        except Exception as e:
            return {
                "liveness_verified": False,
                "liveness_score": 0.0,
                "error": str(e),
                "reason": "processing_error"
            }

    def close(self):
        """Close liveness detection resources"""
        self.face_mesh.close()


# Global instances (singleton pattern)
_face_detector: Optional[FaceDetector] = None
_liveness_detector: Optional[LivenessDetector] = None


def get_face_detector() -> FaceDetector:
    """Get global face detector instance"""
    global _face_detector
    if _face_detector is None:
        _face_detector = FaceDetector()
    return _face_detector


def get_liveness_detector() -> LivenessDetector:
    """Get global liveness detector instance"""
    global _liveness_detector
    if _liveness_detector is None:
        _liveness_detector = LivenessDetector()
    return _liveness_detector
