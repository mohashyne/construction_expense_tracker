"""
Debug command to check user login status and permissions
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import SuperOwner, UserProfile, CompanyMembership
from django.contrib.sessions.models import Session
from django.contrib.auth import get_user_model
from django.utils import timezone
import json

class Command(BaseCommand):
    help = 'Debug user login and permission issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Username to check (optional)',
        )

    def handle(self, *args, **options):
        username = options.get('username')
        
        if username:
            try:
                user = User.objects.get(username=username)
                self.debug_user(user)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User "{username}" not found')
                )
        else:
            self.stdout.write(
                self.style.SUCCESS('=== All Super Owners ===')
            )
            super_owners = User.objects.filter(super_owner_profile__isnull=False)
            for user in super_owners:
                self.debug_user(user)
                self.stdout.write('-' * 50)

    def debug_user(self, user):
        self.stdout.write(f'User: {user.username} (ID: {user.id})')
        self.stdout.write(f'  Name: {user.get_full_name()}')
        self.stdout.write(f'  Email: {user.email}')
        self.stdout.write(f'  Active: {user.is_active}')
        self.stdout.write(f'  Staff: {user.is_staff}')
        self.stdout.write(f'  Superuser: {user.is_superuser}')
        
        # Check UserProfile
        try:
            profile = user.userprofile
            self.stdout.write(f'  UserProfile:')
            self.stdout.write(f'    Account Type: {profile.account_type}')
            self.stdout.write(f'    Account Active: {profile.is_account_active}')
            self.stdout.write(f'    Is Super Owner: {profile.is_super_owner()}')
            self.stdout.write(f'    Last Company: {profile.last_company}')
        except UserProfile.DoesNotExist:
            self.stdout.write(f'  UserProfile: NOT FOUND')

        # Check SuperOwner
        try:
            super_owner = user.super_owner_profile
            self.stdout.write(f'  SuperOwner:')
            self.stdout.write(f'    Primary: {super_owner.is_primary_owner}')
            self.stdout.write(f'    Level: {super_owner.delegation_level}')
            self.stdout.write(f'    Can Activate: {super_owner.can_activate_accounts}')
            self.stdout.write(f'    Can Manage Companies: {super_owner.can_manage_companies}')
        except:
            self.stdout.write(f'  SuperOwner: NOT FOUND')

        # Check Company Memberships
        memberships = CompanyMembership.objects.filter(user=user, status='active')
        self.stdout.write(f'  Active Memberships: {memberships.count()}')
        for membership in memberships:
            self.stdout.write(f'    - {membership.company.name} ({membership.role})')

        # Check Sessions
        active_sessions = Session.objects.filter(expire_date__gt=timezone.now())
        user_sessions = []
        for session in active_sessions:
            data = session.get_decoded()
            if str(user.id) == str(data.get('_auth_user_id')):
                user_sessions.append(session.session_key)
        
        self.stdout.write(f'  Active Sessions: {len(user_sessions)}')

