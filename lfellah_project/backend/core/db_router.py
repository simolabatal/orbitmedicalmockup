import logging
from django.db.utils import OperationalError

logger = logging.getLogger('lfellah.router')


class PrimaryReplicaRouter:
    """
    L'Fellah 2.0 — PrimaryReplicaRouter Haute Disponibilite.

    PRIMARY  = `mysql` (XAMPP)  : donnees IoT en production.
    REPLICA  = `default` (SQLite) : tampon permanent, toujours disponible.

    Strategie :
      - db_for_read / db_for_write : route les modeles IoT vers `mysql`,
        tout le reste (auth, admin, sessions) vers `default`.
      - Le basculement automatique MySQL → SQLite est gere dans les vues
        (try/except OperationalError), pas ici (le router Django ne peut pas
        intercepter les erreurs de connexion).
      - allow_migrate : seules les migrations `iot` sont appliquees sur MySQL.
        Toutes les autres applis migrent dans SQLite (default).
    """

    IOT_APPS = {'iot'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.IOT_APPS:
            return 'mysql'         # PRIMARY — lecture IoT sur MySQL
        return 'default'           # REPLICA — auth/admin/sessions sur SQLite

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.IOT_APPS:
            return 'mysql'         # PRIMARY — ecriture IoT sur MySQL
        return 'default'           # REPLICA — auth/admin/sessions sur SQLite

    def allow_relation(self, obj1, obj2, **hints):
        return True                # Les relations cross-DB sont autorisees

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == 'mysql':
            return app_label in self.IOT_APPS  # Seul iot migre sur MySQL
        return True                           # Tout le reste migre sur SQLite

    @staticmethod
    def is_mysql_available():
        """Verifie si MySQL est joignable (sans lever d'exception)."""
        from django.db import connections
        try:
            connections['mysql'].ensure_connection()
            return True
        except OperationalError:
            return False
        except Exception as e:
            logger.debug(f'MySQL check failed: {e}')
            return False
