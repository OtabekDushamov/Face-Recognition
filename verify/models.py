from django.db import models
from django.core.exceptions import ValidationError
import os

def validate_image_file_extension(value):
    """Validate that the uploaded file is an image."""
    valid_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
    ext = os.path.splitext(value.name)[1]
    if not ext.lower() in valid_extensions:
        raise ValidationError('Unsupported file extension. Please upload an image file.')

class Staff(models.Model):
    """Model representing staff members for face recognition verification."""
    
    name = models.CharField(
        max_length=100,
        help_text="Full name of the staff member"
    )
    
    email = models.EmailField(
        unique=True,
        help_text="Email address of the staff member"
    )
    
    staff_id = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique identifier for the staff member"
    )
    
    photo = models.ImageField(
        upload_to='staff_photos/',
        validators=[validate_image_file_extension],
        help_text="Profile photo for face recognition"
    )
    
    department = models.CharField(
        max_length=50,
        blank=True,
        help_text="Department or team"
    )
    
    position = models.CharField(
        max_length=100,
        blank=True,
        help_text="Job position or title"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this staff member is currently active"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Staff Member"
        verbose_name_plural = "Staff Members"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.staff_id})"
    
    def clean(self):
        """Validate the model data."""
        super().clean()
        if self.photo and not self.photo.name:
            raise ValidationError('Photo is required for face recognition.')

def verification_photo_path(instance, filename):
    """Generate path for verification attempt photos."""
    return f'verification_attempts/{instance.staff.staff_id}/{instance.created_at.strftime("%Y%m%d_%H%M%S")}_{filename}'

class VerificationAttempt(models.Model):
    """Model to track face verification attempts."""
    
    STATUS_CHOICES = [
        ('success', 'Success - Face Matched'),
        ('failed', 'Failed - Face Not Matched'),
        ('error', 'Error - Processing Failed'),
        ('no_face', 'No Face Detected'),
    ]
    
    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='verification_attempts'
    )
    
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='error'
    )
    
    confidence_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Face recognition confidence score (0.0 to 1.0)"
    )
    
    # Store the captured photo from user
    captured_photo = models.ImageField(
        upload_to=verification_photo_path,
        null=True,
        blank=True,
        help_text="Photo captured during verification attempt"
    )
    
    # Store a copy of the staff's reference photo at time of verification
    reference_photo = models.ImageField(
        upload_to=verification_photo_path,
        null=True,
        blank=True,
        help_text="Staff's reference photo at time of verification"
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the verification request"
    )
    
    user_agent = models.TextField(
        blank=True,
        help_text="Browser/device information"
    )
    
    error_message = models.TextField(
        blank=True,
        help_text="Error details if verification failed"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Verification Attempt"
        verbose_name_plural = "Verification Attempts"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.staff.name} - {self.get_status_display()} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
