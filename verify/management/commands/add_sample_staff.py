"""
Django management command to add sample staff data for testing.
"""

from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from verify.models import Staff
import os

class Command(BaseCommand):
    help = 'Add sample staff data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing staff data before adding samples',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing staff data...')
            Staff.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing staff data cleared.'))

        # Sample staff data
        sample_staff = [
            {
                'name': 'John Doe',
                'email': 'john.doe@company.com',
                'staff_id': 'EMP001',
                'department': 'Engineering',
                'position': 'Software Developer',
            },
            {
                'name': 'Jane Smith',
                'email': 'jane.smith@company.com',
                'staff_id': 'EMP002',
                'department': 'Marketing',
                'position': 'Marketing Manager',
            },
            {
                'name': 'Mike Johnson',
                'email': 'mike.johnson@company.com',
                'staff_id': 'EMP003',
                'department': 'HR',
                'position': 'HR Specialist',
            },
            {
                'name': 'Sarah Wilson',
                'email': 'sarah.wilson@company.com',
                'staff_id': 'EMP004',
                'department': 'Engineering',
                'position': 'Senior Developer',
            },
            {
                'name': 'David Brown',
                'email': 'david.brown@company.com',
                'staff_id': 'EMP005',
                'department': 'Sales',
                'position': 'Sales Representative',
            }
        ]

        created_count = 0
        for staff_data in sample_staff:
            staff, created = Staff.objects.get_or_create(
                staff_id=staff_data['staff_id'],
                defaults=staff_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'Created staff: {staff.name} ({staff.staff_id})')
            else:
                self.stdout.write(f'Staff already exists: {staff.name} ({staff.staff_id})')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully added {created_count} new staff members. '
                f'Total staff: {Staff.objects.count()}'
            )
        )
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write('IMPORTANT NOTES:')
        self.stdout.write('='*50)
        self.stdout.write('1. To test face recognition, you need to:')
        self.stdout.write('   - Go to http://127.0.0.1:8000/admin/')
        self.stdout.write('   - Login with admin credentials')
        self.stdout.write('   - Edit each staff member and upload their photo')
        self.stdout.write('')
        self.stdout.write('2. Test the face recognition at:')
        self.stdout.write('   - http://127.0.0.1:8000/verify/')
        self.stdout.write('   - Select a staff member from the dropdown')
        self.stdout.write('   - Capture your photo and verify')
        self.stdout.write('')
        self.stdout.write('3. Staff IDs for testing:')
        for staff_data in sample_staff:
            self.stdout.write(f'   - {staff_data["staff_id"]}: {staff_data["name"]}')
