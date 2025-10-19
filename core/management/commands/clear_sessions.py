"""
Management command to clear user sessions - useful for fixing login issues
"""

from django.core.management.base import BaseCommand
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User
from django.utils import timezone

class Command(BaseCommand):
    help = 'Clear user sessions to fix login/redirect issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Clear sessions for specific username (optional)',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Clear all sessions',
        )

    def handle(self, *args, **options):
        username = options.get('username')
        clear_all = options.get('all')
        
        if clear_all:
            count = Session.objects.count()
            Session.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(f'Cleared {count} sessions')
            )
        elif username:
            try:
                user = User.objects.get(username=username)
                active_sessions = Session.objects.filter(expire_date__gt=timezone.now())
                cleared_count = 0
                
                for session in active_sessions:
                    data = session.get_decoded()
                    if str(user.id) == str(data.get('_auth_user_id')):
                        session.delete()
                        cleared_count += 1
                
                self.stdout.write(
                    self.style.SUCCESS(f'Cleared {cleared_count} sessions for user {username}')
                )
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User "{username}" not found')
                )
        else:
            # Clear expired sessions by default
            expired_count = Session.objects.filter(expire_date__lt=timezone.now()).count()
            Session.objects.filter(expire_date__lt=timezone.now()).delete()
            self.stdout.write(
                self.style.SUCCESS(f'Cleared {expired_count} expired sessions')
            )
