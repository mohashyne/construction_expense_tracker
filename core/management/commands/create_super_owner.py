from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from core.models import SuperOwner, UserProfile
import getpass


class Command(BaseCommand):
    help = 'Create the primary super owner for the application'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Username for the super owner',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email for the super owner',
        )
        parser.add_argument(
            '--first-name',
            type=str,
            help='First name for the super owner',
        )
        parser.add_argument(
            '--last-name',
            type=str,
            help='Last name for the super owner',
        )
        parser.add_argument(
            '--noinput',
            action='store_true',
            help='Do not prompt for input (use default values)',
        )

    def handle(self, *args, **options):
        # Check if primary super owner already exists
        if SuperOwner.objects.filter(is_primary_owner=True).exists():
            primary_owner = SuperOwner.objects.get(is_primary_owner=True)
            self.stdout.write(
                self.style.WARNING(
                    f'Primary super owner already exists: {primary_owner.user.username} ({primary_owner.user.email})'
                )
            )
            return

        # Get user input
        username = options.get('username')
        email = options.get('email')
        first_name = options.get('first_name', '')
        last_name = options.get('last_name', '')
        
        if not options.get('noinput'):
            if not username:
                username = input('Username: ')
            if not email:
                email = input('Email: ')
            if not first_name:
                first_name = input('First name (optional): ')
            if not last_name:
                last_name = input('Last name (optional): ')
        
        if not username:
            raise CommandError('Username is required')
        if not email:
            raise CommandError('Email is required')

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            raise CommandError(f'User with username "{username}" already exists')
        
        if User.objects.filter(email=email).exists():
            raise CommandError(f'User with email "{email}" already exists')

        # Get password
        password = None
        if not options.get('noinput'):
            while not password:
                password = getpass.getpass('Password: ')
                if not password:
                    self.stdout.write('Password cannot be empty')
                    continue
                
                password_confirm = getpass.getpass('Password (again): ')
                if password != password_confirm:
                    self.stdout.write('Passwords do not match')
                    password = None
        else:
            # Generate a random password for non-interactive mode
            import secrets
            import string
            alphabet = string.ascii_letters + string.digits
            password = ''.join(secrets.choice(alphabet) for i in range(12))
            self.stdout.write(f'Generated password: {password}')

        # Create the user and super owner
        try:
            with transaction.atomic():
                # Create user
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    is_staff=True,  # Allow access to admin
                    is_superuser=True,  # Full Django superuser
                )

                # Create user profile
                profile, created = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'is_account_active': True,
                        'activated_at': timezone.now(),
                    }
                )

                # Create super owner profile
                super_owner = SuperOwner.objects.create(
                    user=user,
                    is_primary_owner=True,
                    delegation_level='full',
                    can_manage_companies=True,
                    can_manage_users=True,
                    can_activate_accounts=True,
                    can_access_django_admin=True,
                    can_delegate_permissions=True,
                    can_manage_billing=True,
                    can_view_system_analytics=True,
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created primary super owner: {user.username} ({user.email})'
                    )
                )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        'This user has full access to:\n'
                        '- Django Admin interface\n'
                        '- All companies and users\n'
                        '- Account activation system\n'
                        '- Super owner delegation\n'
                        '- System analytics and billing'
                    )
                )

        except Exception as e:
            raise CommandError(f'Error creating super owner: {str(e)}')
