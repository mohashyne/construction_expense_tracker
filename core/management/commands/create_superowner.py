from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import transaction
from core.models import SuperOwner, UserProfile
import getpass


class Command(BaseCommand):
    help = 'Create a super owner for the application'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Username for the super owner')
        parser.add_argument('--email', type=str, help='Email for the super owner')
        parser.add_argument('--first-name', type=str, help='First name')
        parser.add_argument('--last-name', type=str, help='Last name')
        parser.add_argument('--primary', action='store_true', help='Make this the primary owner')
        parser.add_argument('--full-access', action='store_true', help='Grant full access permissions')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Create Super Owner ===\n'))

        # Get user information
        username = options.get('username') or input('Username: ')
        email = options.get('email') or input('Email: ')
        first_name = options.get('first_name') or input('First Name: ')
        last_name = options.get('last_name') or input('Last Name: ')

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            raise CommandError(f'User with username "{username}" already exists.')
        
        if User.objects.filter(email=email).exists():
            raise CommandError(f'User with email "{email}" already exists.')

        # Get password
        while True:
            password = getpass.getpass('Password: ')
            password_confirm = getpass.getpass('Confirm Password: ')
            if password == password_confirm:
                break
            self.stdout.write(self.style.ERROR('Passwords do not match. Try again.'))

        # Determine if this should be primary owner
        is_primary = options.get('primary', False)
        if not is_primary:
            existing_primary = SuperOwner.objects.filter(is_primary_owner=True).exists()
            if not existing_primary:
                confirm = input('No primary owner exists. Make this user primary owner? (y/N): ')
                is_primary = confirm.lower().startswith('y')

        # Determine permissions
        full_access = options.get('full_access', False)
        if not full_access:
            self.stdout.write('\nPermissions:')
            can_activate_accounts = self._ask_permission('Activate user accounts')
            can_manage_companies = self._ask_permission('Manage companies')
            can_manage_users = self._ask_permission('Manage users')
            can_access_django_admin = self._ask_permission('Access Django admin')
            can_delegate_permissions = self._ask_permission('Delegate permissions to other super owners')
            can_manage_billing = self._ask_permission('Manage billing and subscriptions')
            can_view_system_analytics = self._ask_permission('View system analytics')
        else:
            can_activate_accounts = True
            can_manage_companies = True
            can_manage_users = True
            can_access_django_admin = True
            can_delegate_permissions = True
            can_manage_billing = True
            can_view_system_analytics = True

        try:
            with transaction.atomic():
                # Create user
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=password,
                    is_staff=True  # Required for Django admin access
                )

                # Create user profile
                profile = UserProfile.objects.create(
                    user=user,
                    account_type='individual',
                    is_verified=True,
                    is_account_active=True,
                    activated_at=user.date_joined
                )

                # Create super owner
                super_owner = SuperOwner.objects.create(
                    user=user,
                    is_primary_owner=is_primary,
                    delegation_level='full' if full_access else 'company_management',
                    can_manage_companies=can_manage_companies,
                    can_manage_users=can_manage_users,
                    can_activate_accounts=can_activate_accounts,
                    can_access_django_admin=can_access_django_admin,
                    can_delegate_permissions=can_delegate_permissions,
                    can_manage_billing=can_manage_billing,
                    can_view_system_analytics=can_view_system_analytics
                )

                self.stdout.write(
                    self.style.SUCCESS(f'\n✅ Super Owner created successfully!')
                )
                self.stdout.write(f'Username: {username}')
                self.stdout.write(f'Email: {email}')
                self.stdout.write(f'Primary Owner: {"Yes" if is_primary else "No"}')
                
                self.stdout.write(f'\n🌐 Access URLs:')
                self.stdout.write(f'  • Super Owner Dashboard: /super-owner/')
                self.stdout.write(f'  • Registration Management: /admin/activation-requests/')
                self.stdout.write(f'  • Django Admin: /admin/')
                
                self.stdout.write(f'\n🔐 Login at: /login/')

        except Exception as e:
            raise CommandError(f'Error creating super owner: {str(e)}')

    def _ask_permission(self, permission_name):
        """Ask user for a specific permission"""
        response = input(f'  Grant "{permission_name}" permission? (Y/n): ')
        return not response.lower().startswith('n')
