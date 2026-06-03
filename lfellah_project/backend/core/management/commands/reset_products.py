"""
Management command: supprime tous les produits + dependances + reset auto-increment.
Usage: python manage.py reset_products
"""
from django.core.management.base import BaseCommand
from marketplace.models import Product, OrderItem, CartItem
from django.db import connection, transaction
import os


class Command(BaseCommand):
    help = 'Supprime tous les produits, dependances, images et reinitialise les IDs.'

    @transaction.atomic
    def handle(self, *args, **options):
        count = Product.objects.count()
        self.stdout.write(f'Produits avant : {count}')

        # 1. Supprimer les fichiers image du disque
        img_deleted = 0
        for p in Product.objects.all():
            if p.image:
                try:
                    if os.path.isfile(p.image.path):
                        os.remove(p.image.path)
                        img_deleted += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  Image: {e}'))

        # 2. Supprimer les OrderItems (FK PROTECTED bloque la suppression)
        oi = OrderItem.objects.all().delete()

        # 3. Supprimer les CartItems (FK CASCADE mais on nettoie avant)
        ci = CartItem.objects.all().delete()

        # 4. Supprimer tous les produits
        deleted, _ = Product.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(
            f'Supprime: {deleted} produits, {oi[0]} lignes commande, {ci[0]} paniers'
        ))
        self.stdout.write(f'{img_deleted} images nettoyees du disque')

        # 5. Reset auto-increment SQLite
        if 'sqlite3' in connection.vendor:
            with connection.cursor() as cursor:
                for table in ('marketplace_product', 'marketplace_orderitem',
                              'marketplace_cartitem'):
                    cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
            self.stdout.write('Auto-increment reinitialise (SQLite)')
