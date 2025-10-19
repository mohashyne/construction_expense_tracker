from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import AccountActivationRequest
import secrets


class Command(BaseCommand):
    help = 'Create test registration requests for super-owner to manage'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating test registration requests...'))
        
        # Clean up existing test requests
        self.cleanup_test_requests()
        
        # Create test company registration requests
        self.create_company_requests()
        
        # Create test individual registration requests  
        self.create_individual_requests()
        
        self.stdout.write(self.style.SUCCESS('\n✅ Test registration requests created!'))
        self.stdout.write(self.style.SUCCESS('👑 Login as super-owner to manage: http://127.0.0.1:8000/login/'))
        self.stdout.write(self.style.SUCCESS('   Username: msa'))  
        self.stdout.write(self.style.SUCCESS('   Then go to Super Owner → Registration Management'))
    
    def cleanup_test_requests(self):
        """Clean up existing test requests"""
        test_emails = [
            'demo.company@example.com',
            'tecbuild@contractors.com', 
            'alice.builder@example.com',
            'bob.contractor@freelance.com'
        ]
        
        for email in test_emails:
            try:
                requests = AccountActivationRequest.objects.filter(email=email)
                count = requests.count()
                requests.delete()
                if count > 0:
                    self.stdout.write(f'Removed {count} existing requests for {email}')
            except:
                pass
    
    def create_company_requests(self):
        """Create test company registration requests"""
        company_requests = [
            {
                'email': 'demo.company@example.com',
                'first_name': 'Sarah',
                'last_name': 'Wilson',
                'company_name': 'Demo Construction Co',
                'company_description': 'A demo construction company for testing the registration system',
                'company_address': '123 Demo Street, Test City, TC 12345',
                'company_registration_number': 'DEMO-2024-001',
                'company_website': 'https://democonstruction.com',
                'phone': '+1-555-DEMO',
                'status': 'pending'
            },
            {
                'email': 'techbuild@contractors.com',
                'first_name': 'Marcus',
                'last_name': 'Thompson',
                'company_name': 'TechBuild Innovations',
                'company_description': 'Modern construction solutions with advanced technology integration',
                'company_address': '456 Innovation Ave, Tech Valley, TV 54321',
                'company_registration_number': 'TECH-2024-002',
                'company_website': 'https://techbuild-innovations.com',
                'phone': '+1-555-TECH',
                'status': 'under_review'
            }
        ]
        
        for req_data in company_requests:
            request = AccountActivationRequest.objects.create(
                request_type='company_registration',
                email=req_data['email'],
                username=req_data['email'],
                first_name=req_data['first_name'],
                last_name=req_data['last_name'],
                phone=req_data['phone'],
                company_name=req_data['company_name'],
                company_description=req_data['company_description'],
                company_address=req_data['company_address'],
                company_registration_number=req_data['company_registration_number'],
                company_website=req_data['company_website'],
                status=req_data['status'],
                activation_token=secrets.token_urlsafe(32),
                expires_at=timezone.now() + timedelta(days=30),
                created_at=timezone.now() - timedelta(days=2),  # Created 2 days ago
                metadata={
                    'test_data': True,
                    'request_source': 'demo_data'
                }
            )
            self.stdout.write(f'Created company request: {req_data["company_name"]} - {req_data["status"]}')
    
    def create_individual_requests(self):
        """Create test individual registration requests"""
        individual_requests = [
            {
                'email': 'alice.builder@example.com',
                'first_name': 'Alice',
                'last_name': 'Builder',
                'phone': '+1-555-ALICE',
                'status': 'pending',
                'metadata': {
                    'address': '789 Builder Lane, Construction City, CC 67890',
                    'date_of_birth': '1988-05-15',
                    'test_data': True,
                    'request_source': 'demo_data'
                }
            },
            {
                'email': 'bob.contractor@freelance.com',
                'first_name': 'Bob',
                'last_name': 'Contractor',
                'phone': '+1-555-BOB',
                'status': 'documents_required',
                'metadata': {
                    'address': '321 Freelance Street, Independent City, IC 98765',
                    'date_of_birth': '1985-12-03',
                    'test_data': True,
                    'request_source': 'demo_data'
                }
            }
        ]
        
        for req_data in individual_requests:
            request = AccountActivationRequest.objects.create(
                request_type='individual_registration',
                email=req_data['email'],
                username=req_data['email'],
                first_name=req_data['first_name'],
                last_name=req_data['last_name'],
                phone=req_data['phone'],
                status=req_data['status'],
                activation_token=secrets.token_urlsafe(32),
                expires_at=timezone.now() + timedelta(days=30),
                created_at=timezone.now() - timedelta(days=1),  # Created 1 day ago
                metadata=req_data['metadata']
            )
            
            # Add rejection reason for documents_required status
            if req_data['status'] == 'documents_required':
                request.rejection_reason = 'Please provide additional identity verification documents'
                request.save()
            
            self.stdout.write(f'Created individual request: {req_data["first_name"]} {req_data["last_name"]} - {req_data["status"]}')
