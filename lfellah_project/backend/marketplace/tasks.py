"""
Tâches asynchrones Celery pour le module marketplace de L'Fellah 2.0.
  - generate_invoice_pdf_task  : Facture PDF conforme norme marocaine (TVA 20%, ICE, RC, IF).
  - send_order_confirmation_email_task : Email automatique avec facture en pièce jointe.
  - process_order_workflow     : Tâche orchestratrice déclenchée à la validation.
"""
try:
    from celery import shared_task
    CELERY_AVAILABLE = True
    _shared_task = shared_task
except ImportError:
    CELERY_AVAILABLE = False
    def _shared_task(**kwargs):
        def decorator(func):
            return func
        return decorator
from decimal import Decimal
import os


# ─── COULEURS CORPORATE L'FELLAH ──────────────────────────────────
LF_GREEN = '#2d6a4f'
LF_GREEN_LIGHT = '#40916c'
LF_ACCENT = '#95d5b2'
LF_BG = '#f0fdf4'
LF_GRAY = '#6b7280'
LF_DARK = '#1b4332'
LF_AMBER = '#d97706'
LF_RED = '#e53e3e'


@_shared_task(bind=True, max_retries=3)
def process_order_workflow(self, order_id):
    result_invoice = generate_invoice_pdf_task.delay(order_id)
    send_order_confirmation_email_task.apply_async(
        args=[order_id],
        countdown=5,
    )
    return f"Workflow commande #{order_id} lance (facture: {result_invoice.id})"


@_shared_task(bind=True, max_retries=3)
def generate_invoice_pdf_task(self, order_id):
    """
    Tâche Celery : Génère une facture PDF conforme à la norme marocaine.
    - Colonnes : Désignation, Qté, P.U. HT, Total HT, TVA 20%, Total TTC.
    - Commission L'Fellah 12% incluse dans le P.U. HT (invisible client).
    - Mentions légales : ICE, RC, IF, Patente, CNSS.
    """
    from marketplace.models import Order, OrderItem
    from django.conf import settings
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors

    try:
        order = Order.objects.select_related('buyer', 'seller', 'promo_code').prefetch_related(
            'items__product'
        ).get(id=order_id)

        societe = getattr(settings, 'LF_SOCIETE', {})

        filename = f"invoice_lfellah_{order.id}.pdf"
        pdf_dir = os.path.join(settings.MEDIA_ROOT, 'invoices')
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_path = os.path.join(pdf_dir, filename)

        c = canvas.Canvas(pdf_path, pagesize=A4)
        w, h = A4
        m = 2 * cm

        # ─── BANDEAU ─────────────────────────────────────────
        c.setFillColor(colors.HexColor(LF_DARK))
        c.rect(0, h - 3*cm, w, 3*cm, fill=True, stroke=False)

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 22)
        c.drawString(m, h - 1.6*cm, "L'FELLAH 2.0")
        c.setFont("Helvetica", 7)
        c.drawString(m, h - 2.3*cm, "AGRICULTURE CONNECTEE  |  MARCHE B2B")

        # Mentions legales a droite
        c.setFont("Helvetica", 6)
        c.setFillColor(colors.HexColor(LF_ACCENT))
        sx, sy = 11*cm, h - 1.3*cm
        for ligne in [
            f"ICE : {societe.get('ice', 'N/A')}",
            f"RC : {societe.get('rc', 'N/A')}  |  IF : {societe.get('if_', 'N/A')}",
            f"Patente : {societe.get('patente', 'N/A')}  |  CNSS : {societe.get('cnss', 'N/A')}",
            f"{societe.get('adresse', '')}",
        ]:
            c.drawString(sx, sy, ligne)
            sy -= 0.35*cm

        # ─── TITRE ───────────────────────────────────────────
        c.setFillColor(colors.HexColor(LF_GREEN))
        c.setFont("Helvetica-Bold", 14)
        c.drawString(m, h - 3.8*cm, f"FACTURE N {order.id}")

        c.setFillColor(colors.HexColor(LF_GRAY))
        c.setFont("Helvetica", 8)
        c.drawString(m, h - 4.4*cm, f"Date d'emission : {order.created_at.strftime('%d/%m/%Y a %H:%M')}")
        c.drawString(m, h - 4.9*cm, f"Statut : {order.get_status_display()}")

        # Destinataire
        c.setFillColor(colors.HexColor(LF_GREEN))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(11*cm, h - 3.8*cm, "DESTINATAIRE")
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 8)
        c.drawString(11*cm, h - 4.4*cm, f"Client : {order.buyer.email}")
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor(LF_GRAY))
        c.drawString(11*cm, h - 4.9*cm, f"Livraison : {order.shipping_address[:55]}")

        # Vendeur
        c.setFillColor(colors.HexColor(LF_GREEN))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(m, h - 5.8*cm, "VENDEUR")
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 8)
        c.drawString(m, h - 6.4*cm, f"Cooperative : {order.seller.email}")
        if order.seller.region:
            c.drawString(m, h - 6.9*cm, f"Region : {order.seller.region}")

        # ─── TABLEAU PRODUITS ────────────────────────────────
        yt = h - 7.8*cm
        c.setFillColor(colors.HexColor(LF_BG))
        c.rect(m - 0.2*cm, yt - 0.55*cm, w - 2*m + 0.4*cm, 0.75*cm, fill=True, stroke=False)
        c.setFillColor(colors.HexColor(LF_DARK))
        c.setFont("Helvetica-Bold", 7)

        col_x = [m, 5.5*cm, 8.5*cm, 11.5*cm, 14.5*cm]
        col_labels = ["DESIGNATION", "QTE", "P.U. HT", "TOTAL HT", f"TVA 20%"]
        for label, x in zip(col_labels, col_x):
            c.drawString(x, yt, label)

        c.setStrokeColor(colors.HexColor(LF_GREEN))
        c.setLineWidth(1)
        y_line = yt - 0.7*cm
        c.line(m, y_line, w - m, y_line)

        # Lignes produits (chaque ligne = commission 12% incluse dans P.U. HT)
        y = y_line - 0.55*cm
        tva_rate_int = int(order.tva_rate * 100)
        for i, item in enumerate(order.items.all()):
            if i % 2 == 0:
                c.setFillColor(colors.HexColor(LF_BG))
                c.rect(m - 0.2*cm, y - 0.3*cm, w - 2*m + 0.4*cm, 0.65*cm, fill=True, stroke=False)

            pu_ht = item.unit_price_final       # Prix unitaire HT (commission 12% incluse)
            total_ligne_ht = item.total_final    # Total ligne HT
            total_ligne_tva = (total_ligne_ht * order.tva_rate).quantize(Decimal('0.01'))

            c.setFillColor(colors.black)
            c.setFont("Helvetica", 8)
            c.drawString(col_x[0], y, item.product.name[:35])
            c.drawString(col_x[1], y, f"{item.quantity} {item.product.unit}")
            c.drawString(col_x[2], y, f"{pu_ht:.2f}")
            c.setFont("Helvetica-Bold", 8)
            c.drawString(col_x[3], y, f"{total_ligne_ht:.2f}")
            c.setFillColor(colors.HexColor(LF_AMBER))
            c.drawString(col_x[4], y, f"{total_ligne_tva:.2f}")
            y -= 0.6*cm

        # ─── RECAPITULATIF ───────────────────────────────────
        y -= 0.5*cm
        c.setStrokeColor(colors.HexColor(LF_ACCENT))
        c.setLineWidth(1.5)
        c.line(m, y + 1*cm, w - m, y + 1*cm)

        ht_net = order.total_ht
        if order.discount_amount:
            ht_net = max(Decimal('0.00'), ht_net - order.discount_amount)
        total_tva_amount = order.total_tva
        total_ttc_amount = order.total_final

        rxl, rxv = 10.5*cm, 14.5*cm

        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor(LF_GRAY))
        c.drawString(rxl, y, "TOTAL HORS TAXES :")
        c.setFillColor(colors.black)
        c.drawString(rxv, y, f"{ht_net:.2f} MAD")

        y -= 0.6*cm
        c.setFillColor(colors.HexColor(LF_GRAY))
        c.drawString(rxl, y, f"TVA ({tva_rate_int}%) :")
        c.setFillColor(colors.HexColor(LF_AMBER))
        c.drawString(rxv, y, f"{total_tva_amount:.2f} MAD")

        if order.discount_amount > 0 and order.promo_code:
            y -= 0.6*cm
            c.setFillColor(colors.HexColor(LF_GRAY))
            c.drawString(rxl, y, f"REMISE ({order.promo_code.code}) :")
            c.setFillColor(colors.HexColor(LF_RED))
            c.drawString(rxv, y, f"-{order.discount_amount:.2f} MAD")

        y -= 0.3*cm
        c.setStrokeColor(colors.HexColor(LF_DARK))
        c.setLineWidth(2)
        c.line(rxl, y, w - m, y)

        y -= 0.7*cm
        c.setFillColor(colors.HexColor(LF_DARK))
        c.setFont("Helvetica-Bold", 11)
        c.drawString(rxl, y, "TOTAL TTC :")
        c.drawString(rxv, y, f"{total_ttc_amount:.2f} MAD")

        # ─── PIED DE PAGE ────────────────────────────────────
        c.setFillColor(colors.HexColor(LF_GRAY))
        c.setFont("Helvetica", 5.5)
        py = 2.3*cm
        for ligne in [
            f"L'Fellah 2.0 - {societe.get('raison_sociale', 'SARL')} au capital de {societe.get('capital', '100 000 MAD')}",
            f"ICE: {societe.get('ice', '')}  |  RC: {societe.get('rc', '')}  |  IF: {societe.get('if_', '')}  |  Patente: {societe.get('patente', '')}  |  CNSS: {societe.get('cnss', '')}",
            f"{societe.get('adresse', '')}  |  {societe.get('telephone', '')}  |  {societe.get('email', '')}  |  {societe.get('site_web', '')}",
            f"Facture generee automatiquement le {order.created_at.strftime('%d/%m/%Y a %H:%M')} - N {order.id}",
        ]:
            c.drawString(m, py, ligne)
            py -= 0.35*cm

        c.setFillColor(colors.HexColor(LF_GREEN))
        c.rect(0, 0, w, 0.25*cm, fill=True, stroke=False)
        c.save()

        order.invoice_pdf.name = f"invoices/{filename}"
        order.save(update_fields=['invoice_pdf'])

        return f"Facture PDF norme marocaine generee pour la commande #{order.id}"

    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


@_shared_task(bind=True, max_retries=3)
def send_order_confirmation_email_task(self, order_id):
    from marketplace.models import Order
    from django.conf import settings
    from django.core.mail import EmailMessage

    try:
        order = Order.objects.select_related('buyer', 'seller').get(id=order_id)

        if not order.invoice_pdf or not order.invoice_pdf.path:
            raise ValueError(f"Facture PDF non disponible pour la commande #{order.id}")

        tva_pct = int(order.tva_rate * 100)
        subject = f"L'Fellah - Confirmation de votre commande N {order.id}"
        body = f"""
Bonjour,

Votre commande N {order.id} a ete confirmee avec succes sur L'Fellah 2.0.

Recapitulatif :
  - Vendeur : {order.seller.email}
  - Produits : {order.items.count()} article(s)
  - Total HT (commission incluse) : {order.total_ht:.2f} MAD
  - TVA ({tva_pct}%) : {order.total_tva:.2f} MAD
  - Total TTC : {order.total_final:.2f} MAD
  - Statut : {order.get_status_display()}
  - Livraison : {order.shipping_address[:100]}

Votre facture conforme (ICE, RC, IF, Patente) est en piece jointe.
Suivez votre commande sur : https://lfellah.ma/mes-commandes/

Cordialement,
L'equipe L'Fellah 2.0
        """.strip()

        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[order.buyer.email],
        )

        with open(order.invoice_pdf.path, 'rb') as pdf_file:
            email.attach(
                f"Facture_LFellah_{order.id}.pdf",
                pdf_file.read(),
                'application/pdf',
            )

        email.send(fail_silently=False)

        return f"Email de confirmation envoye a {order.buyer.email} (commande #{order.id})"

    except Order.DoesNotExist:
        return f"Commande #{order_id} introuvable"
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
