from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Staff, VerificationAttempt

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('name', 'staff_id', 'email', 'department', 'position', 'is_active', 'photo_preview', 'created_at')
    list_filter = ('is_active', 'department', 'created_at')
    search_fields = ('name', 'staff_id', 'email', 'department', 'position')
    readonly_fields = ('created_at', 'updated_at', 'photo_preview')
    list_editable = ('is_active',)
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('name', 'email', 'staff_id')
        }),
        ('Work Information', {
            'fields': ('department', 'position', 'is_active')
        }),
        ('Photo', {
            'fields': ('photo', 'photo_preview'),
            'description': 'Upload a clear photo showing the person\'s face for accurate recognition.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def photo_preview(self, obj):
        """Display a small preview of the staff photo."""
        if obj.photo:
            return mark_safe(f'<img src="{obj.photo.url}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />')
        return "No photo"
    photo_preview.short_description = "Photo Preview"
    
    def get_queryset(self, request):
        """Optimize queryset for admin list view."""
        return super().get_queryset(request).select_related()

@admin.register(VerificationAttempt)
class VerificationAttemptAdmin(admin.ModelAdmin):
    list_display = ('staff', 'status', 'confidence_score', 'captured_photo_preview', 'reference_photo_preview', 'ip_address', 'created_at')
    list_filter = ('status', 'created_at', 'staff__department')
    search_fields = ('staff__name', 'staff__staff_id', 'ip_address')
    readonly_fields = ('staff', 'status', 'confidence_score', 'captured_photo', 'reference_photo', 'captured_photo_preview', 'reference_photo_preview', 'ip_address', 'user_agent', 'error_message', 'created_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Verification Details', {
            'fields': ('staff', 'status', 'confidence_score')
        }),
        ('Photos', {
            'fields': (('captured_photo', 'captured_photo_preview'), ('reference_photo', 'reference_photo_preview')),
            'description': 'Photos used during the verification attempt'
        }),
        ('Request Information', {
            'fields': ('ip_address', 'user_agent')
        }),
        ('Error Information', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        })
    )
    
    def captured_photo_preview(self, obj):
        """Display a small preview of the captured photo."""
        if obj.captured_photo:
            return mark_safe(f'<img src="{obj.captured_photo.url}" width="60" height="60" style="object-fit: cover; border-radius: 4px;" />')
        return "No photo"
    captured_photo_preview.short_description = "Captured"
    
    def reference_photo_preview(self, obj):
        """Display a small preview of the reference photo."""
        if obj.reference_photo:
            return mark_safe(f'<img src="{obj.reference_photo.url}" width="60" height="60" style="object-fit: cover; border-radius: 4px;" />')
        return "No photo"
    reference_photo_preview.short_description = "Reference"
    
    def has_add_permission(self, request):
        """Disable adding verification attempts through admin."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Make verification attempts read-only."""
        return False
    
    def get_queryset(self, request):
        """Optimize queryset for admin list view."""
        return super().get_queryset(request).select_related('staff')
