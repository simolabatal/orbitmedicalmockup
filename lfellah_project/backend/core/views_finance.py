from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, FileResponse
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import csv
import os

from .models import PlantScan, Report
from .serializers import ReportSerializer
from .tasks import generate_report_pdf_task
from .views_auth import is_saas_staff, is_finance_staff, is_iot_staff


@login_required
@user_passes_test(is_iot_staff, login_url='/', redirect_field_name=None)
def dashboard(request):
    """Dashboard IoT reserve IOT/Agronome. Finance redirige vers /dashboard-finance/."""
    if request.user.groups.filter(name='Finance').exists():
        return redirect('/dashboard-finance/')
    if request.user.force_password_change:
        return redirect('/accounts/change-password/?force=true')

    recent_scans = PlantScan.objects.select_related('device').order_by('-scanned_at')[:20]
    latest_scan = recent_scans.first()
    return render(request, 'api/index.html', {
        'history': recent_scans,
        'scan': latest_scan,
    })


@login_required
@user_passes_test(is_finance_staff, login_url='/', redirect_field_name=None)
def finance_dashboard(request):
    """Dashboard Finance — acces strictement reserve au groupe Finance."""
    from marketplace.models import Order, Product, ProductCategory, OrderItem
    from django.db.models.functions import TruncDate

    periode = request.GET.get('periode', 'month')
    now = timezone.now()

    if periode == 'year':
        debut = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        debut = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # ─── DIAGNOSTIC DATA ──────────────────────────────────────
    print(f'[FINANCE] Periode: {periode}, debut: {debut}')
    total_orders = Order.objects.count()
    delivered_orders = Order.objects.filter(status='delivered').count()
    filtered_orders = Order.objects.filter(status='delivered', created_at__gte=debut).count()
    print(f'[FINANCE] Orders total={total_orders} delivered={delivered_orders} filtered={filtered_orders}')

    try:
        commandes = Order.objects.filter(status='delivered', created_at__gte=debut)
        if not commandes.exists():
            print('[FINANCE] Aucune commande livree sur la periode. Verifiez marketplace.')
    except Exception as e:
        print(f'[FINANCE] ERREUR requete Order: {type(e).__name__}: {e}')
        commandes = Order.objects.none()

    try:
        ca_brut = sum((o.total_ht for o in commandes), Decimal('0.00'))
        commission = sum((o.total_commission for o in commandes), Decimal('0.00'))
        net_agriculteurs = ca_brut - commission
        print(f'[FINANCE] CA brut={ca_brut} commission={commission} net={net_agriculteurs}')
    except Exception as e:
        print(f'[FINANCE] ERREUR calcul financier: {type(e).__name__}: {e}')
        ca_brut = commission = net_agriculteurs = Decimal('0.00')

    try:
        categories_stats = []
        for cat in ProductCategory.objects.filter(is_active=True):
            items = OrderItem.objects.filter(
                order__in=commandes,
                product__category=cat
            ).select_related('product')
            qte_vendue = sum((i.quantity for i in items), Decimal('0.00'))
            comm_cat = sum((i.total_commission for i in items), Decimal('0.00'))
            if qte_vendue > 0:
                categories_stats.append({
                    'nom': cat.name_fr,
                    'qte_vendue': qte_vendue,
                    'commission': comm_cat,
                })
        categories_stats.sort(key=lambda x: x['commission'], reverse=True)
        print(f'[FINANCE] Categories actives: {len(categories_stats)}')
    except Exception as e:
        print(f'[FINANCE] ERREUR categories: {type(e).__name__}: {e}')
        categories_stats = []

    try:
        jours_labels = []
        ca_journalier = []
        for i in range(29, -1, -1):
            jour = now.date() - timedelta(days=i)
            jours_labels.append(jour.strftime('%d/%m'))
            ca_j = sum(
                (o.total_ht for o in commandes if o.created_at.date() == jour),
                Decimal('0.00')
            )
            ca_journalier.append(float(ca_j))
    except Exception as e:
        print(f'[FINANCE] ERREUR journalier: {type(e).__name__}: {e}')
        jours_labels, ca_journalier = [], []

    context = {
        'ca_brut': ca_brut,
        'commission': commission,
        'net_agriculteurs': net_agriculteurs,
        'categories_stats': categories_stats,
        'jours_labels': jours_labels,
        'ca_journalier': ca_journalier,
        'periode': periode,
        'total_commandes': commandes.count(),
    }
    return render(request, 'core/finance_dashboard.html', context)


@login_required
def dashboard_redirect(request):
    """Redirige vers le dashboard correspondant au groupe."""
    if request.user.groups.filter(name='Finance').exists():
        return redirect('/dashboard-finance/')
    if request.user.role == 'farmer':
        return redirect('/vendeur/dashboard/')
    return redirect('/dashboard-iot/')


class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Report.objects.filter(generated_by=self.request.user).order_by('-week_start')


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def generate_report_api(request):
    end = timezone.now().date()
    start = end - timedelta(days=7)
    task = generate_report_pdf_task.delay(request.user.id, start.isoformat(), end.isoformat())
    return Response({
        'status': 'processing',
        'task_id': task.id,
        'message': 'Rapport en cours de generation. Vous serez notifie quand il sera pret.',
    })


@login_required
@user_passes_test(is_finance_staff, login_url='/', redirect_field_name=None)
def export_finance_pdf(request):
    from marketplace.models import Order, ProductCategory, OrderItem
    from django.conf import settings as s

    now = timezone.now()
    periode = request.GET.get('periode', 'month')
    if periode == 'year':
        debut = now.replace(month=1, day=1)
    else:
        debut = now.replace(day=1)

    commandes = Order.objects.filter(status='delivered', created_at__gte=debut)
    ca_brut = sum((o.total_ht for o in commandes), Decimal('0.00'))
    commission = sum((o.total_commission for o in commandes), Decimal('0.00'))
    net_agriculteurs = ca_brut - commission

    categories_stats = []
    for cat in ProductCategory.objects.filter(is_active=True):
        items = OrderItem.objects.filter(order__in=commandes, product__category=cat)
        qte = sum((i.quantity for i in items), Decimal('0.00'))
        comm = sum((i.total_commission for i in items), Decimal('0.00'))
        if qte > 0:
            categories_stats.append({'nom': cat.name_fr, 'qte_vendue': qte, 'commission': comm})
    categories_stats.sort(key=lambda x: x['commission'], reverse=True)

    societe = getattr(s, 'LF_SOCIETE', {})
    filename = f"rapport_finance_{now.strftime('%Y%m%d')}.pdf"
    pdf_dir = os.path.join(s.MEDIA_ROOT, 'invoices')
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, filename)

    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors

    c = canvas.Canvas(pdf_path, pagesize=A4)
    w, h = A4
    m = 2 * cm
    LF_DARK, LF_GREEN, LF_BG, LF_GRAY, LF_AMBER = '#1b4332', '#2d6a4f', '#f0fdf4', '#6b7280', '#d97706'

    logo_path = os.path.join(s.MEDIA_ROOT, 'logo.png')
    if os.path.exists(logo_path):
        try:
            c.drawImage(logo_path, m, h - 2.2*cm, width=1.8*cm, height=1.8*cm, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    c.setFillColor(colors.HexColor(LF_DARK))
    c.rect(0, h - 2.5*cm, w, 2.5*cm, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(m + 2.2*cm, h - 1.5*cm, "L'FELLAH 2.0 - RAPPORT FINANCE")
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor('#95d5b2'))
    c.drawString(m, h - 2.2*cm, f"Periode: {debut.strftime('%d/%m/%Y')} - {now.strftime('%d/%m/%Y')} | ICE: {societe.get('ice','')}")

    c.setFillColor(colors.HexColor(LF_GREEN))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(m, h - 3.5*cm, "SYNTHESE FINANCIERE")
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    y = h - 4.3*cm
    for label, val in [("Chiffre d'Affaires Brut", f"{ca_brut:.2f} MAD"), ("Commission L'Fellah (12%)", f"{commission:.2f} MAD"), ("Revenu Net Agriculteurs", f"{net_agriculteurs:.2f} MAD"), ("Commandes livrees", str(commandes.count()))]:
        c.drawString(m, y, f"{label}: {val}")
        y -= 0.7*cm

    if categories_stats:
        y -= 0.5*cm
        c.setFillColor(colors.HexColor(LF_GREEN))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(m, y, "VENTES PAR CATEGORIE")
        y -= 0.6*cm
        c.setFillColor(colors.HexColor(LF_BG))
        c.rect(m-0.2*cm, y-0.5*cm, w-2*m+0.4*cm, 0.7*cm, fill=True, stroke=False)
        c.setFillColor(colors.HexColor(LF_DARK))
        c.setFont("Helvetica-Bold", 7)
        for label, x in [("CATEGORIE", m), ("QTE VENDUE", 9*cm), ("COMMISSION", 14*cm)]:
            c.drawString(x, y, label)
        y -= 0.7*cm
        for i, cat in enumerate(categories_stats):
            if i % 2 == 0:
                c.setFillColor(colors.HexColor(LF_BG))
                c.rect(m-0.2*cm, y-0.25*cm, w-2*m+0.4*cm, 0.55*cm, fill=True, stroke=False)
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 8)
            c.drawString(m, y, cat['nom'][:30])
            c.drawString(9*cm, y, str(cat['qte_vendue']))
            c.setFillColor(colors.HexColor(LF_AMBER))
            c.drawString(14*cm, y, f"{cat['commission']:.2f} MAD")
            y -= 0.55*cm

    c.setFillColor(colors.HexColor(LF_GRAY))
    c.setFont("Helvetica", 5)
    py = 1.5*cm
    raison = societe.get('raison_sociale', "L'FELLAH SARL")
    ice = societe.get('ice', '')
    rc = societe.get('rc', '')
    for ligne in [f"{raison} | ICE:{ice} | RC:{rc}",
                  f"Rapport genere le {now.strftime('%d/%m/%Y')}"]:
        c.drawString(m, py, ligne)
        py -= 0.3*cm
    c.setFillColor(colors.HexColor(LF_GREEN))
    c.rect(0, 0, w, 0.2*cm, fill=True, stroke=False)
    c.save()

    return FileResponse(open(pdf_path, 'rb'), content_type='application/pdf',
                        as_attachment=True, filename=filename)
