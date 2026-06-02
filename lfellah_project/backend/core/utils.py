"""
Smart Advisor — Alerte email avec analyse de seuils IoT.
L'Fellah 2.0 — core/utils.py
"""
import threading
from django.core.mail import send_mail
from django.core.cache import cache
from django.utils import timezone


# ─── SEUILS ───────────────────────────────────────────────────────
THRESHOLDS = {
    'temperature': (20.0, 30.0, '\u00b0C'),
    'ph': (6.0, 7.0, ''),
    'humidity': (40.0, 70.0, '%'),
    'tds': (500.0, 1200.0, 'ppm'),
}

CACHE_TIMEOUT = 1800  # 30 minutes entre alertes pour le meme capteur

REMEDIATION = {
    'temperature': {
        'low': "Stocker les plantes a l'interieur ou sous serre chauffee. Couvrir le sol avec un paillis.",
        'high': "Activer l'ombriere. Augmenter la ventilation (ouverture laterale). Brumiser les feuilles.",
    },
    'ph': {
        'low': "Ajouter de la chaux (calcaire broye) ou du carbonate de calcium. Retester apres 48h.",
        'high': "Ajouter du soufre elementaire ou un acidifiant organique. Irriguer legerement.",
    },
    'humidity': {
        'low': "Brumiser les plantes 2x/jour. Installer un humidificateur. Reduire la ventilation.",
        'high': "Augmenter la ventilation. Reduire l'arrosage. Installer un deshumidificateur.",
    },
    'tds': {
        'low': "TDS trop bas (<500 ppm). Ajouter de l'engrais ou des nutriments. Verifier la solution nutritive.",
        'high': "TDS trop eleve (>1200 ppm). Diluer la solution nutritive avec de l'eau propre. Rincer le substrat.",
    },
}


def _build_alert_message(sensor, value, unit, direction):
    """Construit le corps de l'email d'alerte."""
    remed = REMEDIATION.get(sensor, {}).get(direction, '')
    return (
        f"[L'Fellah 2.0 — Alerte Smart Advisor]\n\n"
        f"Capteur : {sensor}\n"
        f"Valeur mesuree : {value:.1f}{unit}\n"
        f"Anomalie : {'TROP BAS' if direction == 'low' else 'TROP HAUT'}\n\n"
        f"Conseil : {remed}\n\n"
        f"Horodatage : {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    )


def check_and_notify(data):
    """
    Parcourt les valeurs brutes d'un payload capteur.
    Si un seuil est depasse ET que le dernier email date de plus
    d'une heure (cache Django), envoie un email asynchrone.
    """
    to_email = ['zeuslasauceenpersonne123@gmail.com']
    sent_any = False

    for sensor, (low, high, unit) in THRESHOLDS.items():
        value = data.get(sensor)
        if value is None:
            continue

        direction = None
        if low is not None and value < low:
            direction = 'low'
        elif high is not None and value > high:
            direction = 'high'

        if direction is None:
            continue

        # Rate limit : 1 alerte par capteur par heure
        cache_key = f'alert_{sensor}_{direction}'
        last_sent = cache.get(cache_key)
        if last_sent is not None:
            print(f'[ADVISOR] Alerte {sensor} ({direction}) ignoree — rate limit (dernier envoi il y a <1h)')
            continue

        subject = f"ALERTE {sensor.upper()} {'BAS' if direction == 'low' else 'HAUT'} — L'Fellah 2.0"
        message = _build_alert_message(sensor, value, unit, direction)

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=None,  # utilise DEFAULT_FROM_EMAIL
                recipient_list=to_email,
                fail_silently=False,  # DEBUG : lever l'erreur SMTP reelle
            )
            cache.set(cache_key, timezone.now(), CACHE_TIMEOUT)  # 30 min TTL
            sent_any = True
            print(f'[ADVISOR] EMAIL ENVOYE : {subject} | valeur={value:.1f}{unit}')
        except Exception as e:
            print(f'[ADVISOR] ERREUR SMTP {sensor} : {type(e).__name__}: {e}')

    return sent_any


def async_check_and_notify(data):
    """Appel non-bloquant via thread separe."""
    t = threading.Thread(target=check_and_notify, args=(data,), daemon=True)
    t.start()
    print(f'[ADVISOR] Thread lance (PID cache)')


def test_smtp_connection():
    """
    Test de connexion SMTP brute — valide le handshake Gmail.
    Lance depuis manage.py shell ou un script Django standalone.
    """
    from django.core.mail import get_connection, EmailMessage
    from django.conf import settings

    print(f'[SMTP TEST] EMAIL_BACKEND = {settings.EMAIL_BACKEND}')
    print(f'[SMTP TEST] EMAIL_HOST    = {settings.EMAIL_HOST}')
    print(f'[SMTP TEST] EMAIL_PORT    = {settings.EMAIL_PORT}')
    print(f'[SMTP TEST] EMAIL_USE_TLS = {settings.EMAIL_USE_TLS}')
    print(f'[SMTP TEST] EMAIL_HOST_USER = {settings.EMAIL_HOST_USER}')
    print(f'[SMTP TEST] EMAIL_HOST_PASSWORD = {"***" if settings.EMAIL_HOST_PASSWORD else "VIDE"}')
    print(f'[SMTP TEST] DEFAULT_FROM_EMAIL = {settings.DEFAULT_FROM_EMAIL}')

    if 'console' in settings.EMAIL_BACKEND:
        print('[SMTP TEST] !! BACKEND EST CONSOLE — les emails ne sont PAS envoyes par SMTP !!')
        return False

    try:
        connection = get_connection()
        connection.open()
        print('[SMTP TEST] Connexion SMTP ouverte avec succes')

        msg = EmailMessage(
            subject="[L'Fellah 2.0] TEST SMTP — IGNORER",
            body="Ceci est un test de connexion SMTP. Si vous recevez ceci, le handshake Gmail fonctionne.",
            to=['zeuslasauceenpersonne123@gmail.com'],
        )
        msg.send(fail_silently=False)
        print('[SMTP TEST] Email de test envoye — VERIFIEZ VOTRE BOITE MAIL')
        connection.close()
        return True
    except Exception as e:
        print(f'[SMTP TEST] ECHEC : {type(e).__name__}: {e}')
        return False
