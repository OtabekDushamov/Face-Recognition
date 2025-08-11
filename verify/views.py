from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings
from django.db import models
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from datetime import datetime, timedelta
import json
import logging
import os
import shutil

from .models import Staff, VerificationAttempt
try:
    from .face_recognition_service import face_recognition_service
except ImportError:
    face_recognition_service = None

logger = logging.getLogger(__name__)

def camera_view(request):
    """Render the camera page for face verification."""
    context = {
        'title': 'Face Verification',
        'user_id': request.GET.get('user_id'),
    }
    return render(request, 'camera.html', context)

def get_client_ip(request):
    """Get the client's IP address from the request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@method_decorator(csrf_exempt, name='dispatch')
class FaceVerificationAPI(View):
    """API endpoint for face verification."""
    
    def post(self, request):
        """Handle face verification POST request."""
        try:
            # Get user_id from query parameters
            user_id = request.GET.get('user_id')
            if not user_id:
                return JsonResponse({
                    'success': False,
                    'message': 'user_id parameter is required',
                    'error_code': 'MISSING_USER_ID'
                }, status=400)
            
            # Get the uploaded photo
            if 'photo' not in request.FILES:
                return JsonResponse({
                    'success': False,
                    'message': 'No photo uploaded',
                    'error_code': 'MISSING_PHOTO'
                }, status=400)
            
            uploaded_photo = request.FILES['photo']
            
            # Validate file size (max 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            if uploaded_photo.size > max_size:
                return JsonResponse({
                    'success': False,
                    'message': 'Photo file is too large (max 10MB)',
                    'error_code': 'FILE_TOO_LARGE'
                }, status=400)
            
            # Get staff member
            try:
                staff = Staff.objects.get(staff_id=user_id, is_active=True)
            except Staff.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Staff member not found or inactive',
                    'error_code': 'STAFF_NOT_FOUND'
                }, status=404)
            
            # Check if staff has a photo
            if not staff.photo:
                return JsonResponse({
                    'success': False,
                    'message': 'No reference photo found for this staff member',
                    'error_code': 'NO_REFERENCE_PHOTO'
                }, status=400)
            
            # Perform face verification
            if face_recognition_service is None:
                return JsonResponse({
                    'success': False,
                    'message': 'Face recognition system not available. Please install required dependencies.',
                    'error_code': 'FACE_RECOGNITION_UNAVAILABLE'
                }, status=503)
            
            staff_photo_path = staff.photo.path
            is_match, confidence_score, error_message = face_recognition_service.verify_face(
                staff_photo_path, uploaded_photo
            )
            
            # Determine status
            if error_message:
                if "No face detected" in error_message:
                    status = 'no_face'
                    message = 'No face detected in the uploaded photo'
                else:
                    status = 'error'
                    message = 'Face processing failed'
            elif is_match:
                status = 'success'
                message = f'Face verified successfully! Welcome, {staff.name}!'
            else:
                status = 'failed'
                message = 'Face verification failed - no match found'
            
            # Create verification attempt record
            verification_attempt = VerificationAttempt.objects.create(
                staff=staff,
                status=status,
                confidence_score=confidence_score if confidence_score > 0 else None,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                error_message=error_message
            )
            
            # Save the captured photo
            try:
                # Reset file pointer to beginning
                uploaded_photo.seek(0)
                captured_filename = f'captured_{verification_attempt.id}.jpg'
                verification_attempt.captured_photo.save(
                    captured_filename,
                    ContentFile(uploaded_photo.read()),
                    save=False
                )
            except Exception as e:
                logger.warning(f"Failed to save captured photo: {str(e)}")
            
            # Save a copy of the staff's reference photo
            try:
                if staff.photo:
                    # Copy the staff's current photo as reference
                    with staff.photo.open('rb') as ref_file:
                        reference_filename = f'reference_{verification_attempt.id}.jpg'
                        verification_attempt.reference_photo.save(
                            reference_filename,
                            ContentFile(ref_file.read()),
                            save=False
                        )
            except Exception as e:
                logger.warning(f"Failed to save reference photo: {str(e)}")
            
            # Save the verification attempt with photos
            verification_attempt.save()
            
            # Prepare response
            response_data = {
                'success': is_match and not error_message,
                'message': message,
                'staff_name': staff.name,
                'confidence_score': round(confidence_score, 3) if confidence_score > 0 else None,
                'verification_id': verification_attempt.id,
                'timestamp': verification_attempt.created_at.isoformat()
            }
            
            # Add error details for debugging (only in debug mode)
            if settings.DEBUG and error_message:
                response_data['debug_error'] = error_message
            
            status_code = 200 if not error_message else 422
            return JsonResponse(response_data, status=status_code)
            
        except Exception as e:
            logger.error(f"Unexpected error in face verification: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': 'Internal server error',
                'error_code': 'INTERNAL_ERROR'
            }, status=500)

@require_http_methods(["GET"])
def staff_list_api(request):
    """API endpoint to get list of active staff members."""
    try:
        staff_members = Staff.objects.filter(is_active=True).values(
            'staff_id', 'name', 'email', 'department', 'position'
        )
        
        return JsonResponse({
            'success': True,
            'staff_members': list(staff_members),
            'count': len(staff_members)
        })
    except Exception as e:
        logger.error(f"Error retrieving staff list: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Failed to retrieve staff list',
            'error_code': 'INTERNAL_ERROR'
        }, status=500)

@require_http_methods(["GET"])
def staff_detail_api(request, staff_id):
    """API endpoint to get details of a specific staff member."""
    try:
        staff = get_object_or_404(Staff, staff_id=staff_id, is_active=True)
        
        return JsonResponse({
            'success': True,
            'staff': {
                'staff_id': staff.staff_id,
                'name': staff.name,
                'email': staff.email,
                'department': staff.department,
                'position': staff.position,
                'has_photo': bool(staff.photo),
                'photo_url': staff.photo.url if staff.photo else None,
                'created_at': staff.created_at.isoformat()
            }
        })
    except Exception as e:
        logger.error(f"Error retrieving staff details: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Staff member not found',
            'error_code': 'STAFF_NOT_FOUND'
        }, status=404)

@require_http_methods(["GET"])
def verification_stats_api(request):
    """API endpoint to get verification statistics."""
    try:
        from django.db.models import Count
        
        # Get stats for the last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        stats = VerificationAttempt.objects.filter(
            created_at__gte=thirty_days_ago
        ).aggregate(
            total_attempts=Count('id'),
            successful_attempts=Count('id', filter=models.Q(status='success')),
            failed_attempts=Count('id', filter=models.Q(status='failed')),
            error_attempts=Count('id', filter=models.Q(status='error')),
            no_face_attempts=Count('id', filter=models.Q(status='no_face'))
        )
        
        return JsonResponse({
            'success': True,
            'stats': stats,
            'period': '30 days'
        })
    except Exception as e:
        logger.error(f"Error retrieving verification stats: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Failed to retrieve statistics',
            'error_code': 'INTERNAL_ERROR'
        }, status=500)

@require_http_methods(["GET"])
def verification_attempts_api(request, staff_id=None):
    """API endpoint to get verification attempts for a staff member or all attempts."""
    try:
        from django.db.models import Count
        
        # Base query
        attempts_query = VerificationAttempt.objects.select_related('staff')
        
        # Filter by staff if provided
        if staff_id:
            attempts_query = attempts_query.filter(staff__staff_id=staff_id)
        
        # Get recent attempts (last 50)
        attempts = attempts_query.order_by('-created_at')[:50]
        
        attempts_data = []
        for attempt in attempts:
            attempt_data = {
                'id': attempt.id,
                'staff_id': attempt.staff.staff_id,
                'staff_name': attempt.staff.name,
                'status': attempt.status,
                'confidence_score': attempt.confidence_score,
                'created_at': attempt.created_at.isoformat(),
                'captured_photo_url': attempt.captured_photo.url if attempt.captured_photo else None,
                'reference_photo_url': attempt.reference_photo.url if attempt.reference_photo else None,
                'ip_address': attempt.ip_address,
                'error_message': attempt.error_message
            }
            attempts_data.append(attempt_data)
        
        return JsonResponse({
            'success': True,
            'attempts': attempts_data,
            'count': len(attempts_data)
        })
    except Exception as e:
        logger.error(f"Error retrieving verification attempts: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Failed to retrieve verification attempts',
            'error_code': 'INTERNAL_ERROR'
        }, status=500)

def health_check(request):
    """Simple health check endpoint."""
    return JsonResponse({
        'status': 'healthy',
        'service': 'face-recognition-api',
        'timestamp': datetime.now().isoformat()
    })
