from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import SuperOwner, UserProfile


class Command(BaseCommand):
    help = 'Grant Django admin access to super owner users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username', 
            type=str, 
            help='Username to grant admin access to (if not provided, applies to all super owners)'
        )
        parser.add_argument(
            '--create-superowner', 
            action='store_true',
            help='Create a SuperOwner profile if the user doesn\'t have one'
        )

    def handle(self, *args, **options):
        username = options.get('username')
        create_superowner = options.get('create_superowner', False)

        if username:
            try:
                user = User.objects.get(username=username)
                self.grant_access_to_user(user, create_superowner)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User "{username}" does not exist.')
                )
                return
        else:
            # Grant access to all existing super owners
            super_owners = SuperOwner.objects.all()
            if not super_owners.exists():
                self.stdout.write(
                    self.style.WARNING('No super owners found in the system.')
                )
                return

            for super_owner in super_owners:
                self.grant_access_to_user(super_owner.user, create_superowner)

    def grant_access_to_user(self, user, create_superowner=False):
        """Grant Django admin access to a specific user"""
        
        # Ensure user has a UserProfile
        profile, created = UserProfile.objects.get_or_create(user=user)
        if created:
            self.stdout.write(f'Created UserProfile for {user.username}')

        # Check if user has SuperOwner profile
        if not hasattr(user, 'super_owner_profile'):
            if create_superowner:
                # Create SuperOwner profile
                super_owner = SuperOwner.objects.create(
                    user=user,
                    is_primary_owner=True,  # You might want to adjust this
                    can_access_django_admin=True,
                    can_manage_companies=True,
                    can_manage_users=True,
                    can_activate_accounts=True,
                    can_delegate_permissions=True,
                    can_view_system_analytics=True,
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Created SuperOwner profile for {user.username}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f'User "{user.username}" is not a super owner. '
                        'Use --create-superowner to create the profile.'
                    )
                )
                return

        # Update SuperOwner permissions
        super_owner = user.super_owner_profile
        super_owner.can_access_django_admin = True
        super_owner.save()

        # Make user staff (required for Django admin access)
        if not user.is_staff:
            user.is_staff = True
            user.save()
            self.stdout.write(f'Granted staff status to {user.username}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully granted Django admin access to {user.username}'
            )
        )

        # Show current permissions
        permissions = []
        if super_owner.can_manage_companies:
            permissions.append('Companies')
        if super_owner.can_manage_users:
            permissions.append('Users')
        if super_owner.can_activate_accounts:
            permissions.append('Account Activation')
        if super_owner.can_access_django_admin:
            permissions.append('Django Admin')
        if super_owner.can_delegate_permissions:
            permissions.append('Permission Delegation')
        if super_owner.can_view_system_analytics:
            permissions.append('System Analytics')

        self.stdout.write(
            f'Current permissions for {user.username}: {", ".join(permissions)}'
        )
