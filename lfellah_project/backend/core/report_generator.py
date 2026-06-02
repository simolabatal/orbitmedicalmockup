"""
Générateur de rapports PDF hebdomadaires pour L'Fellah 2.0
Utilise ReportLab pour créer des rapports professionnels avec:
- En-tête brandée
- Statistiques clés
- Tableau des scans critiques
- Résumé des maladies détectées
"""
import os
import io
from datetime import date, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.platypus import KeepTogether
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


def generate_weekly_report_pdf(week_start=None, week_end=None):
    """
    Génère un rapport PDF hebdomadaire.
    Retourne: (pdf_bytes, stats_dict)
    """
    from .models import PlantScan

    if not week_start:
        today = date.today()
        week_start = today - timedelta(days=today.weekday() + 7)
        week_end = week_start + timedelta(days=6)

    scans = PlantScan.objects.filter(
        scanned_at__date__gte=week_start,
        scanned_at__date__lte=week_end
    ).order_by('-scanned_at')

    total = scans.count()
    critical = scans.filter(severity='critical').count()
    warning = scans.filter(severity='warning').count()
    healthy = scans.filter(severity='normal').count()

    # Disease frequency
    disease_freq = {}
    for scan in scans:
        name = scan.disease_name
        disease_freq[name] = disease_freq.get(name, 0) + 1
    top_diseases = sorted(disease_freq.items(), key=lambda x: x[1], reverse=True)[:5]

    # Build PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2.5*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    elements = []

    # ── Header ──────────────────────────────────────────────────────────────
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=22,
        textColor=colors.HexColor('#10b981'),
        spaceAfter=4,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#64748b'),
        alignment=TA_CENTER,
        spaceAfter=2
    )

    elements.append(Paragraph("🌿 L'Fellah 2.0", title_style))
    elements.append(Paragraph("Rapport d'Analyse Agricole Hebdomadaire", subtitle_style))
    elements.append(Paragraph(
        f"Semaine du {week_start.strftime('%d %B %Y')} au {week_end.strftime('%d %B %Y')}",
        subtitle_style
    ))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#10b981')))
    elements.append(Spacer(1, 0.5*cm))

    # ── KPI Summary Table ────────────────────────────────────────────────────
    section_style = ParagraphStyle(
        'Section',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=12,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )
    elements.append(Paragraph("📊 Résumé de la Semaine", section_style))

    kpi_data = [
        ['Métrique', 'Valeur', 'Pourcentage'],
        ['Total des scans', str(total), '100%'],
        ['Plantes saines', str(healthy), f"{round(healthy/total*100 if total else 0)}%"],
        ['Alertes modérées', str(warning), f"{round(warning/total*100 if total else 0)}%"],
        ['Cas critiques', str(critical), f"{round(critical/total*100 if total else 0)}%"],
    ]
    kpi_table = Table(kpi_data, colWidths=[8*cm, 4*cm, 4*cm])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f0fdf4')),
        ('BACKGROUND', (0, 2), (-1, 2), colors.white),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#fffbeb')),
        ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor('#fef2f2')),
        ('TEXTCOLOR', (0, 4), (-1, 4), colors.HexColor('#dc2626')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 0.5*cm))

    # ── Top Diseases ─────────────────────────────────────────────────────────
    if top_diseases:
        elements.append(Paragraph("🦠 Top 5 Maladies Détectées", section_style))
        disease_data = [['Maladie', 'Occurrences', 'Fréquence']]
        for name, count in top_diseases:
            pct = round(count / total * 100 if total else 0)
            disease_data.append([name[:50], str(count), f"{pct}%"])
        disease_table = Table(disease_data, colWidths=[10*cm, 3*cm, 3*cm])
        disease_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ]))
        elements.append(disease_table)
        elements.append(Spacer(1, 0.5*cm))

    # ── Critical Scans Table ─────────────────────────────────────────────────
    critical_scans = scans.filter(severity='critical')[:10]
    if critical_scans.exists():
        elements.append(Paragraph("🚨 Scans Critiques", section_style))
        scan_data = [['ID', 'Date', 'Maladie', 'Confiance']]
        for s in critical_scans:
            scan_data.append([
                f"#{s.id}",
                s.scanned_at.strftime('%d/%m %H:%M'),
                s.disease_name[:40],
                f"{s.confidence:.1f}%"
            ])
        scan_table = Table(scan_data, colWidths=[2*cm, 3.5*cm, 9*cm, 3*cm])
        scan_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#fff5f5'), colors.white]),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ]))
        elements.append(scan_table)
        elements.append(Spacer(1, 0.5*cm))

    # ── Footer ───────────────────────────────────────────────────────────────
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#94a3b8'),
        alignment=TA_CENTER,
        spaceBefore=6
    )
    elements.append(Paragraph(
        f"Rapport généré automatiquement par L'Fellah 2.0 — Agriculture Connectée © 2026",
        footer_style
    ))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    stats = {
        'total': total,
        'critical': critical,
        'warning': warning,
        'healthy': healthy,
        'week_start': week_start,
        'week_end': week_end,
    }
    return pdf_bytes, stats
