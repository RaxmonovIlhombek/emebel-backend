"""
pdf_generator.py — PDF chek generatsiya

reportlab bilan professional PDF
"""
import io
import logging

logger = logging.getLogger(__name__)


def generate_order_pdf(order) -> bytes:
    """
    Buyurtma uchun PDF chek generatsiya qiladi.
    Returns: bytes (PDF content)
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Table, TableStyle,
            Spacer, HRFlowable
        )
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    except ImportError:
        raise ImportError("pip install reportlab")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    # ── Stillar ──────────────────────────────────────────────────────
    ORANGE = colors.HexColor('#f97316')
    DARK   = colors.HexColor('#1E293B')
    GRAY   = colors.HexColor('#64748B')
    LIGHT  = colors.HexColor('#F8FAFC')
    RED    = colors.HexColor('#DC2626')
    GREEN  = colors.HexColor('#16A34A')

    title_style = ParagraphStyle('title', fontSize=22, alignment=TA_CENTER,
                                  fontName='Helvetica-Bold', textColor=DARK, spaceAfter=4)
    sub_style   = ParagraphStyle('sub',   fontSize=13, alignment=TA_CENTER,
                                  fontName='Helvetica-Bold', textColor=ORANGE, spaceAfter=16)
    label_style = ParagraphStyle('label', fontSize=10, fontName='Helvetica-Bold', textColor=DARK)
    value_style = ParagraphStyle('value', fontSize=10, fontName='Helvetica',      textColor=GRAY)
    total_style = ParagraphStyle('total', fontSize=13, fontName='Helvetica-Bold', textColor=DARK, alignment=TA_RIGHT)

    story = []

    # ── Sarlavha ─────────────────────────────────────────────────────
    story.append(Paragraph("e-MEBEL CRM", title_style))
    story.append(Paragraph(f"BUYURTMA #{order.order_number}", sub_style))
    story.append(HRFlowable(width="100%", thickness=2, color=ORANGE, spaceAfter=12))

    # ── Mijoz ma'lumotlari ───────────────────────────────────────────
    info_data = [
        [Paragraph("Buyurtma:", label_style), Paragraph(f"#{order.order_number}", value_style)],
        [Paragraph("Sana:",     label_style), Paragraph(order.created_at.strftime("%d.%m.%Y %H:%M"), value_style)],
        [Paragraph("Mijoz:",    label_style), Paragraph(order.client.name, value_style)],
        [Paragraph("Telefon:",  label_style), Paragraph(order.client.phone or "—", value_style)],
        [Paragraph("Manzil:",   label_style), Paragraph(order.delivery_address or "—", value_style)],
        [Paragraph("Holat:",    label_style), Paragraph(order.get_status_display(), value_style)],
        [Paragraph("To'lov:",   label_style), Paragraph(order.get_payment_status_display(), value_style)],
    ]
    if order.manager:
        info_data.append([
            Paragraph("Menejer:", label_style),
            Paragraph(order.manager.get_full_name() or order.manager.username, value_style)
        ])

    info_table = Table(info_data, colWidths=[4*cm, 13*cm])
    info_table.setStyle(TableStyle([
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BACKGROUND',    (0, 0), (0, -1), LIGHT),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Mahsulotlar jadvali ──────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E2E8F0')))
    story.append(Spacer(1, 0.3*cm))

    items_header = [
        Paragraph("#",         ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white)),
        Paragraph("Mahsulot",  ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white)),
        Paragraph("Miqdor",    ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=TA_CENTER)),
        Paragraph("Narx",      ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=TA_RIGHT)),
        Paragraph("Jami",      ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=TA_RIGHT)),
    ]
    items_data = [items_header]

    for i, item in enumerate(order.items.select_related('product').all(), 1):
        row_style = ParagraphStyle('r', fontSize=9, textColor=DARK)
        items_data.append([
            Paragraph(str(i),                               row_style),
            Paragraph(item.product.name,                    row_style),
            Paragraph(str(item.quantity),                   ParagraphStyle('rc', fontSize=9, alignment=TA_CENTER)),
            Paragraph(f"{item.price:,.0f}",                 ParagraphStyle('rr', fontSize=9, alignment=TA_RIGHT)),
            Paragraph(f"{item.subtotal:,.0f}",              ParagraphStyle('rr', fontSize=9, alignment=TA_RIGHT, fontName='Helvetica-Bold')),
        ])

    items_table = Table(items_data, colWidths=[1*cm, 8.5*cm, 2*cm, 3*cm, 3.5*cm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND',     (0, 0), (-1, 0),  DARK),
        ('FONTNAME',       (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',       (0, 0), (-1, -1), 9),
        ('GRID',           (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('BOTTOMPADDING',  (0, 0), (-1, -1), 6),
        ('TOPPADDING',     (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT]),
        ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 0.4*cm))

    # ── Moliyaviy ma'lumot ───────────────────────────────────────────
    fin_data = [
        [Paragraph("Jami summa:",   label_style), Paragraph(f"{order.total_amount:,.0f} so'm",     ParagraphStyle('fr', fontSize=11, alignment=TA_RIGHT))],
        [Paragraph("To'langan:",    label_style), Paragraph(f"{order.paid_amount:,.0f} so'm",      ParagraphStyle('fg', fontSize=11, alignment=TA_RIGHT, textColor=GREEN))],
        [Paragraph("Qoldiq:",       ParagraphStyle('fl', fontSize=11, fontName='Helvetica-Bold', textColor=RED)),
                                    Paragraph(f"{order.remaining_amount:,.0f} so'm",               ParagraphStyle('fr', fontSize=12, alignment=TA_RIGHT, fontName='Helvetica-Bold', textColor=RED))],
    ]

    fin_table = Table(fin_data, colWidths=[5*cm, 6*cm])
    fin_table.setStyle(TableStyle([
        ('ALIGN',         (0, 0), (-1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('LINEABOVE',     (0, -1), (-1, -1), 1.5, ORANGE),
    ]))
    story.append(fin_table)

    # ── To'lovlar tarixi ─────────────────────────────────────────────
    payments = order.payments.all()
    if payments:
        story.append(Spacer(1, 0.4*cm))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E2E8F0')))
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph("To'lovlar tarixi:", ParagraphStyle('pt', fontName='Helvetica-Bold', fontSize=10, textColor=DARK, spaceAfter=6)))

        pay_header = [
            Paragraph("Sana",     ParagraphStyle('ph', fontName='Helvetica-Bold', fontSize=8, textColor=colors.white)),
            Paragraph("Summa",    ParagraphStyle('ph', fontName='Helvetica-Bold', fontSize=8, textColor=colors.white, alignment=TA_RIGHT)),
            Paragraph("Usul",     ParagraphStyle('ph', fontName='Helvetica-Bold', fontSize=8, textColor=colors.white, alignment=TA_CENTER)),
            Paragraph("Holat",    ParagraphStyle('ph', fontName='Helvetica-Bold', fontSize=8, textColor=colors.white, alignment=TA_CENTER)),
        ]
        pay_data = [pay_header]
        for p in payments:
            confirmed = "✓" if p.is_confirmed else "⏳"
            pay_data.append([
                Paragraph(p.created_at.strftime("%d.%m.%Y"), ParagraphStyle('pr', fontSize=8)),
                Paragraph(f"{p.amount:,.0f}", ParagraphStyle('pr', fontSize=8, alignment=TA_RIGHT)),
                Paragraph(p.get_method_display(), ParagraphStyle('pr', fontSize=8, alignment=TA_CENTER)),
                Paragraph(confirmed, ParagraphStyle('pr', fontSize=8, alignment=TA_CENTER)),
            ])
        pay_table = Table(pay_data, colWidths=[4*cm, 5*cm, 4*cm, 5*cm])
        pay_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), GRAY),
            ('FONTSIZE',   (0, 0), (-1, -1), 8),
            ('GRID',       (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT]),
        ]))
        story.append(pay_table)

    # ── Footer ───────────────────────────────────────────────────────
    story.append(Spacer(1, 0.8*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E2E8F0')))
    footer_style = ParagraphStyle('footer', fontSize=8, textColor=GRAY, alignment=TA_CENTER, spaceBefore=6)
    story.append(Paragraph("e-Mebel CRM • Telegram: @emebel_bot", footer_style))
    story.append(Paragraph(f"Chek sanasi: {order.created_at.strftime('%d.%m.%Y %H:%M')}", footer_style))

    doc.build(story)
    return buf.getvalue()