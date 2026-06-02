from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError
from iot.models import SensorData


class Command(BaseCommand):
    help = (
        'Synchronise les donnees SensorData du buffer SQLite (default) '
        'vers MySQL (mysql). Supprime les enregistrements transferes '
        'de SQLite une fois le transfert reussi.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche ce qui serait transfere sans ecrire dans MySQL',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # 1. Verifier que MySQL est joignable
        try:
            connections['mysql'].ensure_connection()
            self.stdout.write(self.style.SUCCESS('[SYNC] MySQL : CONNECTE'))
        except OperationalError as e:
            self.stderr.write(self.style.ERROR(
                f'[SYNC] MySQL : INDISPONIBLE — {e}\n'
                '[SYNC] Synchronisation annulee. Les donnees restent dans SQLite.'
            ))
            return

        # 2. Lister les enregistrements dans SQLite (default)
        backup_records = list(
            SensorData.objects.using('default')
            .select_related('device')
            .order_by('recorded_at')
        )

        if not backup_records:
            self.stdout.write('[SYNC] Aucun enregistrement a transferer dans SQLite.')
            return

        self.stdout.write(
            f'[SYNC] {len(backup_records)} enregistrement(s) trouves dans SQLite.'
        )

        if dry_run:
            for sd in backup_records:
                self.stdout.write(
                    f'  [DRY-RUN] id={sd.id} device={sd.device.name} '
                    f'T={sd.temperature} H={sd.humidity} '
                    f'TDS={sd.tds} pH={sd.ph} recorded_at={sd.recorded_at}'
                )
            self.stdout.write(self.style.WARNING('[DRY-RUN] Aucune ecriture reelle effectuee.'))
            return

        # 3. Inserer dans MySQL via bulk_create
        new_objects = []
        for sd in backup_records:
            new_objects.append(SensorData(
                device=sd.device,
                temperature=sd.temperature,
                humidity=sd.humidity,
                tds=sd.tds,
                ph=sd.ph,
                recorded_at=sd.recorded_at,
            ))

        try:
            SensorData.objects.using('mysql').bulk_create(new_objects)
            self.stdout.write(self.style.SUCCESS(
                f'[SYNC] {len(new_objects)} enregistrements inseres dans MySQL.'
            ))
        except OperationalError as e:
            self.stderr.write(self.style.ERROR(
                f'[SYNC] Echec insertion MySQL : {e}\n'
                '[SYNC] Aucune donnee supprimee de SQLite.'
            ))
            return
        except Exception as e:
            self.stderr.write(self.style.ERROR(
                f'[SYNC] Erreur inattendue : {e}\n'
                '[SYNC] Aucune donnee supprimee de SQLite.'
            ))
            return

        # 4. Supprimer les enregistrements transferes de SQLite
        backup_ids = [sd.id for sd in backup_records]
        deleted, _ = SensorData.objects.using('default').filter(id__in=backup_ids).delete()
        self.stdout.write(
            f'[SYNC] {deleted} enregistrement(s) supprimes de SQLite.'
        )
        self.stdout.write(self.style.SUCCESS('[SYNC] Synchronisation terminee.'))
