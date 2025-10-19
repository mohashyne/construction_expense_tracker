from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from core.models import (
    Company, UserProfile, CompanyMembership, Role, Permission,
    AccountActivationRequest
)


class Command(BaseCommand):
    help = 'Create test approved company and individual users for dashboard testing'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating test users and data...'))
        
        # Clean up existing test data
        self.cleanup_test_data()
        
        # Create basic permissions first
        self.create_permissions()
        
        # Create test company user
        company_user = self.create_company_user()
        
        # Create test individual user
        individual_user = self.create_individual_user()
        
        self.stdout.write(self.style.SUCCESS('\n=== TEST USERS CREATED ==='))
        self.stdout.write(self.style.SUCCESS('\n🏢 COMPANY USER:'))
        self.stdout.write(f'   Username: {company_user.username}')
        self.stdout.write(f'   Password: company123')
        self.stdout.write(f'   Email: {company_user.email}')
        self.stdout.write(f'   Company: BuildTech Solutions Ltd')
        self.stdout.write(f'   Role: Company Administrator')
        
        self.stdout.write(self.style.SUCCESS('\n👤 INDIVIDUAL USER:'))
        self.stdout.write(f'   Username: {individual_user.username}')
        self.stdout.write(f'   Password: individual123')
        self.stdout.write(f'   Email: {individual_user.email}')
        self.stdout.write(f'   Type: Individual Contractor')
        
        self.stdout.write(self.style.SUCCESS('\n✅ Both users are approved and ready to login!'))
        self.stdout.write(self.style.SUCCESS('🌐 Login at: http://127.0.0.1:8000/login/'))
    
    def cleanup_test_data(self):
        """Clean up existing test data"""
        # Remove test users
        test_usernames = ['buildtech_admin', 'john_contractor']
        for username in test_usernames:
            try:
                user = User.objects.get(username=username)
                user.delete()
                self.stdout.write(f'Removed existing user: {username}')
            except User.DoesNotExist:
                pass
        
        # Remove test company
        try:
            company = Company.objects.get(name='BuildTech Solutions Ltd')
            company.delete()
            self.stdout.write('Removed existing test company')
        except Company.DoesNotExist:
            pass
        
        # Remove test activation requests
        test_tokens = ['buildtech-approved-token', 'john-contractor-approved-token']
        for token in test_tokens:
            try:
                request = AccountActivationRequest.objects.get(activation_token=token)
                request.delete()
                self.stdout.write(f'Removed existing activation request: {token}')
            except AccountActivationRequest.DoesNotExist:
                pass
    
    def create_permissions(self):
        """Permissions will be created when roles are created"""
        # Permissions are created per role, not globally
        pass
    
    def create_company_user(self):
        """Create a test company user with full setup"""
        # Create company user
        user = User.objects.create_user(
            username='buildtech_admin',
            email='admin@buildtech-solutions.com',
            password='company123',
            first_name='Michael',
            last_name='Johnson',
            is_active=True
        )
        
        # Create user profile
        profile = UserProfile.objects.create(
            user=user,
            phone='+1-555-0123',
            date_of_birth='1985-03-15',
            address='456 Business Avenue, Construction City, CC 12345',
            account_type='company'
        )
        
        # Create company
        company = Company.objects.create(
            name='BuildTech Solutions Ltd',
            description='Premium construction and engineering solutions provider',
            address='456 Business Avenue, Construction City, CC 12345',
            phone='+1-555-0123',
            email='contact@buildtech-solutions.com',
            website='https://buildtech-solutions.com',
            registration_number='BTS-2024-001',
            is_active=True
        )
        
        # Update profile with company
        profile.last_company = company
        profile.save()
        
        # Create admin role with all permissions
        admin_role = Role.objects.create(
            company=company,
            name='Company Administrator',
            description='Full access to all company features',
            is_admin=True,
            is_supervisor=False
        )
        
        # Create permissions for admin role
        permissions_data = [
            ('projects', 'view'), ('projects', 'create'), ('projects', 'edit'), ('projects', 'delete'),
            ('expenses', 'view'), ('expenses', 'create'), ('expenses', 'edit'), ('expenses', 'delete'), ('expenses', 'approve'),
            ('contractors', 'view'), ('contractors', 'create'), ('contractors', 'edit'), ('contractors', 'delete'),
            ('reports', 'view'), ('reports', 'export'),
            ('users', 'view'), ('users', 'create'), ('users', 'edit'), ('users', 'delete'),
            ('company', 'view'), ('company', 'edit'),
            ('billing', 'view'), ('billing', 'edit'),
        ]
        
        # Create permissions for this role
        for resource, action in permissions_data:
            Permission.objects.create(
                role=admin_role,
                resource=resource,
                action=action
            )
        
        # Create company membership
        CompanyMembership.objects.create(
            user=user,
            company=company,
            role=admin_role,
            status='active',
            joined_date=timezone.now(),
            invited_by=user
        )
        
        # Create completed activation request
        AccountActivationRequest.objects.create(
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=profile.phone,
            request_type='company_registration',
            status='approved',
            company_name=company.name,
            company_description=company.description,
            company_address=company.address,
            company_registration_number=company.registration_number,
            company_website=company.website,
            activation_token='buildtech-approved-token',
            expires_at=timezone.now() + timedelta(days=30),
            approved_at=timezone.now(),
            metadata={
                'approved': True,
                'payment_completed': True,
                'subscription_type': 'company_premium'
            }
        )
        
        return user
    
    def create_individual_user(self):
        """Create a test individual user"""
        # Create individual user
        user = User.objects.create_user(
            username='john_contractor',
            email='john.smith@contractor.com',
            password='individual123',
            first_name='John',
            last_name='Smith',
            is_active=True
        )
        
        # Create user profile
        profile = UserProfile.objects.create(
            user=user,
            phone='+1-555-0789',
            date_of_birth='1990-07-22',
            address='123 Contractor Lane, Builder City, BC 54321',
            account_type='individual'
        )
        
        # Create completed activation request
        AccountActivationRequest.objects.create(
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=profile.phone,
            request_type='individual_registration',
            status='approved',
            activation_token='john-contractor-approved-token',
            expires_at=timezone.now() + timedelta(days=30),
            approved_at=timezone.now(),
            metadata={
                'approved': True,
                'payment_completed': True,
                'subscription_type': 'individual_pro',
                'address': profile.address,
                'date_of_birth': str(profile.date_of_birth) if profile.date_of_birth else None
            }
        )
        
        return user
