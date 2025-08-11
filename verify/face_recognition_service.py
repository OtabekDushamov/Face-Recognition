"""
Face recognition service for comparing uploaded photos with staff photos.
"""

try:
    import face_recognition
    import numpy as np
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    face_recognition = None
    np = None

from PIL import Image
import io
import logging
from typing import Tuple, Optional, List, Any
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.conf import settings

logger = logging.getLogger(__name__)

class FaceRecognitionService:
    """Service class for handling face recognition operations."""
    
    # Recognition threshold - lower values are more strict
    RECOGNITION_THRESHOLD = 0.6
    
    def __init__(self):
        """Initialize the face recognition service."""
        if not FACE_RECOGNITION_AVAILABLE:
            logger.warning("Face recognition libraries not available. Please install them.")
        self.encoding_model = getattr(settings, 'FACE_RECOGNITION_MODEL', 'large')
        
    def extract_face_encoding(self, image_file) -> Tuple[Optional[Any], str]:
        """
        Extract face encoding from an image file.
        
        Args:
            image_file: Image file (can be UploadedFile or file path)
            
        Returns:
            Tuple of (face_encoding or None, error_message)
        """
        if not FACE_RECOGNITION_AVAILABLE:
            return None, "Face recognition libraries not installed"
            
        try:
            # Load image
            if isinstance(image_file, InMemoryUploadedFile):
                # Handle uploaded file
                image_data = image_file.read()
                image = Image.open(io.BytesIO(image_data))
                # Convert RGBA to RGB if necessary
                if image.mode == 'RGBA':
                    image = image.convert('RGB')
                image_array = np.array(image)
            else:
                # Handle file path
                image_array = face_recognition.load_image_file(image_file)
            
            # Find face locations
            face_locations = face_recognition.face_locations(
                image_array, 
                model=self.encoding_model
            )
            
            if not face_locations:
                return None, "No face detected in the image"
            
            if len(face_locations) > 1:
                logger.warning(f"Multiple faces detected ({len(face_locations)}), using the first one")
            
            # Extract face encodings
            face_encodings = face_recognition.face_encodings(
                image_array, 
                face_locations,
                model=self.encoding_model
            )
            
            if not face_encodings:
                return None, "Could not generate face encoding"
            
            return face_encodings[0], ""
            
        except Exception as e:
            error_msg = f"Error processing image: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def compare_faces(self, known_encoding: Any, unknown_encoding: Any) -> Tuple[bool, float]:
        """
        Compare two face encodings.
        
        Args:
            known_encoding: Reference face encoding
            unknown_encoding: Face encoding to compare
            
        Returns:
            Tuple of (is_match, confidence_score)
        """
        try:
            # Calculate face distance
            face_distance = face_recognition.face_distance([known_encoding], unknown_encoding)[0]
            
            # Convert distance to confidence score (0-1, higher is better)
            confidence_score = 1 - face_distance
            
            # Determine if it's a match based on threshold
            is_match = face_distance <= self.RECOGNITION_THRESHOLD
            
            logger.info(f"Face comparison: distance={face_distance:.3f}, confidence={confidence_score:.3f}, match={is_match}")
            
            return is_match, float(confidence_score)
            
        except Exception as e:
            error_msg = f"Error comparing faces: {str(e)}"
            logger.error(error_msg)
            return False, 0.0
    
    def verify_face(self, staff_photo_path: str, uploaded_photo) -> Tuple[bool, float, str]:
        """
        Verify if an uploaded photo matches a staff member's photo.
        
        Args:
            staff_photo_path: Path to the staff member's reference photo
            uploaded_photo: Uploaded photo file
            
        Returns:
            Tuple of (is_match, confidence_score, error_message)
        """
        try:
            # Extract encodings from both images
            staff_encoding, staff_error = self.extract_face_encoding(staff_photo_path)
            if staff_encoding is None:
                return False, 0.0, f"Staff photo error: {staff_error}"
            
            uploaded_encoding, uploaded_error = self.extract_face_encoding(uploaded_photo)
            if uploaded_encoding is None:
                return False, 0.0, f"Uploaded photo error: {uploaded_error}"
            
            # Compare the faces
            is_match, confidence_score = self.compare_faces(staff_encoding, uploaded_encoding)
            
            return is_match, confidence_score, ""
            
        except Exception as e:
            error_msg = f"Face verification failed: {str(e)}"
            logger.error(error_msg)
            return False, 0.0, error_msg
    
    def batch_verify_faces(self, staff_encodings: List[Tuple[str, Any]], uploaded_photo) -> List[Tuple[str, bool, float]]:
        """
        Verify an uploaded photo against multiple staff members.
        
        Args:
            staff_encodings: List of (staff_id, face_encoding) tuples
            uploaded_photo: Uploaded photo file
            
        Returns:
            List of (staff_id, is_match, confidence_score) tuples
        """
        results = []
        
        # Extract encoding from uploaded photo
        uploaded_encoding, error = self.extract_face_encoding(uploaded_photo)
        if uploaded_encoding is None:
            return [(staff_id, False, 0.0) for staff_id, _ in staff_encodings]
        
        # Compare against all staff encodings
        for staff_id, staff_encoding in staff_encodings:
            try:
                is_match, confidence = self.compare_faces(staff_encoding, uploaded_encoding)
                results.append((staff_id, is_match, confidence))
            except Exception as e:
                logger.error(f"Error comparing with staff {staff_id}: {str(e)}")
                results.append((staff_id, False, 0.0))
        
        return results
    
    def get_face_locations(self, image_file) -> List[Tuple[int, int, int, int]]:
        """
        Get face locations in an image.
        
        Args:
            image_file: Image file
            
        Returns:
            List of face location tuples (top, right, bottom, left)
        """
        try:
            if isinstance(image_file, InMemoryUploadedFile):
                image_data = image_file.read()
                image = Image.open(io.BytesIO(image_data))
                if image.mode == 'RGBA':
                    image = image.convert('RGB')
                image_array = np.array(image)
            else:
                image_array = face_recognition.load_image_file(image_file)
            
            return face_recognition.face_locations(image_array, model=self.encoding_model)
            
        except Exception as e:
            logger.error(f"Error getting face locations: {str(e)}")
            return []

# Global service instance
face_recognition_service = FaceRecognitionService()
