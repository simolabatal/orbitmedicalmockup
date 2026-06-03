"""
Management command: Initialise les groupes RBAC de L'Fellah 2.0.
Usage: python manage.py init_groups
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission


GROUPS = [
    'Admin',
    'Finance',
    'Marketing',
    'Farmer',
    'Buyer',
    'Agronomist',
]


class Command(BaseCommand):
    help = 'Initialise les groupes RBAC (Admin, Finance, Marketing, Farmer, Buyer, Agronomist).'

    def handle(self, *args, **options):
        created = []
        existing = []

        for name in GROUPS:
            group, was_created = Group.objects.get_or_create(name=name)
            if was_created:
                created.append(name)
                self.stdout.write(self.style.SUCCESS('  + Groupe cree : %s' % name))
            else:
                existing.append(name)
                self.stdout.write('  ~ Groupe existant : %s' % name)

        # Admin recoit les permissions de base (utilisateurs, groupes, produits, commandes)
        admin_group = Group.objects.get(name='Admin')
        admin_perms = Permission.objects.filter(
            content_type__app_label__in=('accounts', 'marketplace', 'iot', 'core')
        )
        admin_group.permissions.set(admin_perms)
        self.stdout.write('  -> %d permissions attribuees au groupe Admin' % admin_perms.count())

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            'Termine : %d cree(s), %d existant(s).' % (len(created), len(existing))
        ))
