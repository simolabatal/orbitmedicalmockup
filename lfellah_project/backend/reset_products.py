"""Script de reinitialisation des produits."""
from marketplace.models import Product
from django.db import connection
import os

count = Product.objects.count()
print(f'Produits avant suppression : {count}')

# 1. Supprimer les fichiers image
for p in Product.objects.all():
    if p.image and os.path.isfile(p.image.path):
        os.remove(p.image.path)

# 2. Supprimer tous les produits
deleted, _ = Product.objects.all().delete()
print(f'Produits supprimes : {deleted}')

# 3. Reinitialiser auto-increment
if 'sqlite3' in connection.vendor:
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='marketplace_product'")
    print('Auto-increment reinitialise (SQLite)')
else:
    print('MySQL: ALTER TABLE marketplace_product AUTO_INCREMENT = 1')
