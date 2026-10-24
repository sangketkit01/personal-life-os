from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.accounts.models import InviteCode

User = get_user_model()


class Command(BaseCommand):
    help = 'Create initial superuser and master invite code'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='admin')
        parser.add_argument('--password', type=str, default='admin1234')
        parser.add_argument('--email', type=str, default='admin@personal-life-os.local')

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        email = options['email']

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'[OK] Superuser created: {username} / password: {password}'))
        else:
            self.stdout.write(self.style.WARNING(f'[INFO] User {username} already exists'))

        # Create Master Invite Code if not exists (1 Invite Code = 1 User)
        invite_code = 'LIFE-FOUNDER-2026'
        invite, inv_created = InviteCode.objects.get_or_create(
            code=invite_code,
            defaults={
                'created_by': user,
                'max_uses': 1,
                'is_active': True
            }
        )
        if inv_created:
            self.stdout.write(self.style.SUCCESS(f'[OK] Master Invite Code created: {invite_code}'))
        else:
            self.stdout.write(self.style.WARNING(f'[INFO] Master Invite Code {invite_code} already exists'))
