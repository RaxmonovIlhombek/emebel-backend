"""
contract_pdf.py — Shartnoma PDF generatsiyasi
"""
import io


def generate_contract_pdf(contract) -> bytes:
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

    order  = contract.order
    client = order.client
    buf    = io.BytesIO()

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm,   bottomMargin=2*cm,
    )

    ORANGE = colors.HexColor('#f97316')
    DARK   = colors.HexColor('#1e293b')
    GRAY   = colors.HexColor('#64748b')
    LIGHT  = colors.HexColor('#f8fafc')
    LINE   = colors.HexColor('#e2e8f0')

    S = lambda name, **kw: ParagraphStyle(name, **kw)
    story = []

    # ── Sarlavha ──────────────────────────────────────────────────────
    story.append(Paragraph(
        "e-MEBEL CRM",
        S('comp', fontSize=10, textColor=GRAY, alignment=TA_CENTER)
    ))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"XARID-SOTISH SHARTNOMASI",
        S('title', fontSize=18, fontName='Helvetica-Bold', textColor=DARK, alignment=TA_CENTER)
    ))
    story.append(Paragraph(
        f"№ {contract.contract_number}",
        S('num', fontSize=13, fontName='Helvetica-Bold', textColor=ORANGE, alignment=TA_CENTER, spaceAfter=4)
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=ORANGE, spaceAfter=12))

    # ── Sana va joy ───────────────────────────────────────────────────
    date_str = contract.signed_date.strftime('%d.%m.%Y') if contract.signed_date else '___.____.______'

    # ── Tomonlar ──────────────────────────────────────────────────────
    LB = S('lb', fontSize=10, fontName='Helvetica-Bold', textColor=DARK)
    VL = S('vl', fontSize=10, textColor=GRAY)
    JU = S('ju', fontSize=10, textColor=DARK, leading=14)

    story.append(Paragraph("1. TOMONLAR HAQIDA MA'LUMOT", S('h1', fontSize=11, fontName='Helvetica-Bold', textColor=DARK, spaceBefore=8, spaceAfter=6)))

    seller_info = (
        "<b>\"E-MEBEL\" MCHJ</b>, bundan keyin \"Sotuvchi\" deb yuritiladi. <br/>"
        "Manzil: Toshkent shahri, Yunusobod tumani, 19-kvartal, 12-uy. <br/>"
        "STIR (INN): 305123456, MFO: 01020 <br/>"
        "H/R: 20208000105345678001 <br/>"
        "Bank: \"ATB QISHLOQ QURILISH BANK\" ATB Toshkent shahar filiali. <br/>"
        "Direktor: <b>Raxmonov Ilhombek Valijon o'g'li</b>"
    )

    sides_data = [
        [Paragraph("SOTUVCHI:", LB), Paragraph(seller_info, JU)],
        [Paragraph("XARIDOR:", LB), Paragraph(
            f"<b>{client.name}</b>, bundan keyin \"Xaridor\" deb yuritiladi. <br/>"
            f"Tel: {client.phone} <br/>" +
            (f"Manzil: {client.address or client.city or ''}" if hasattr(client, 'address') else f"Manzil: {client.city or ''} {client.region or ''}").strip(', '),
            JU
        )],
    ]
    sides_table = Table(sides_data, colWidths=[3.5*cm, 13*cm])
    sides_table.setStyle(TableStyle([
        ('TOPPADDING',    (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('BACKGROUND',    (0,0), (0,-1),  LIGHT),
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
        ('GRID',          (0,0), (-1,-1), 0.5, LINE),
    ]))
    story.append(sides_table)
    story.append(Spacer(1, 0.4*cm))

    # ── Buyurtma tafsilotlari ─────────────────────────────────────────
    story.append(Paragraph("2. SHARTNOMA PREDMETI", S('h1', fontSize=11, fontName='Helvetica-Bold', textColor=DARK, spaceBefore=8, spaceAfter=6)))
    story.append(Paragraph(
        f"2.1. Sotuvchi ushbu shartnoma asosida Xaridorga quyidagi mahsulotlarni yetkazib berish majburiyatini oladi "
        f"(Buyurtma #{order.order_number}):",
        S('ju', fontSize=10, textColor=DARK, leading=14, spaceAfter=8)
    ))

    # Mahsulotlar jadvali
    hdr_s = S('hh', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white)
    row_s = S('rr', fontSize=9, textColor=DARK)
    items_data = [[
        Paragraph('#', hdr_s),
        Paragraph('Mahsulot nomi va tavsifi', hdr_s),
        Paragraph('Miqdor', hdr_s),
        Paragraph('Narx', hdr_s),
        Paragraph('Jami (so\'m)', hdr_s),
    ]]
    for i, item in enumerate(order.items.select_related('product').all(), 1):
        items_data.append([
            Paragraph(str(i), row_s),
            Paragraph(f"<b>{item.product.name}</b><br/><font size=8 color=gray>{item.product.material or ''}</font>", row_s),
            Paragraph(str(item.quantity), S('rc', fontSize=9, alignment=TA_CENTER)),
            Paragraph(f"{item.price:,.0f}", S('rr2', fontSize=9, alignment=TA_RIGHT)),
            Paragraph(f"{item.subtotal:,.0f}", S('rb', fontSize=9, alignment=TA_RIGHT, fontName='Helvetica-Bold')),
        ])

    items_t = Table(items_data, colWidths=[1*cm, 8.5*cm, 2*cm, 3*cm, 3.5*cm])
    items_t.setStyle(TableStyle([
        ('BACKGROUND',     (0,0), (-1,0),  DARK),
        ('FONTSIZE',       (0,0), (-1,-1), 9),
        ('GRID',           (0,0), (-1,-1), 0.5, LINE),
        ('BOTTOMPADDING',  (0,0), (-1,-1), 6),
        ('TOPPADDING',     (0,0), (-1,-1), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LIGHT]),
    ]))
    story.append(items_t)
    story.append(Spacer(1, 0.3*cm))

    # Jami
    fin_data = [
        [Paragraph("Jami summa:", LB),    Paragraph(f"<b>{order.total_amount:,.0f} so'm</b>", S('fr', fontSize=11, alignment=TA_RIGHT))],
        [Paragraph("To'lanishi kerak:", S('fl', fontSize=11, fontName='Helvetica-Bold', textColor=ORANGE)),
         Paragraph(f"<b>{order.remaining_amount:,.0f} so'm</b>", S('ftotal', fontSize=13, alignment=TA_RIGHT, fontName='Helvetica-Bold', textColor=ORANGE))],
    ]
    fin_t = Table(fin_data, colWidths=[5*cm, 6*cm])
    fin_t.setStyle(TableStyle([
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LINEABOVE',     (0,-1), (-1,-1), 1.5, ORANGE),
    ]))
    story.append(fin_t)
    story.append(Spacer(1, 0.5*cm))

    # ── Yetkazib berish ───────────────────────────────────────────────
    story.append(Paragraph("3. YETKAZIB BERISH VA KAFOLAT", S('h1', fontSize=11, fontName='Helvetica-Bold', textColor=DARK, spaceBefore=8, spaceAfter=6)))
    addr = order.full_delivery_address or "Kelishiladi"
    date_d = order.delivery_date.strftime('%d.%m.%Y') if order.delivery_date else "15 ish kuni ichida"

    delivery_data = [
        [Paragraph("Etkazib berish manzili:", LB), Paragraph(addr, VL)],
        [Paragraph("Etkazib berish muddati:", LB), Paragraph(date_d, VL)],
        [Paragraph("Kafolat muddati:", LB),       Paragraph("12 (o'n ikki) oy", VL)],
    ]
    d_t = Table(delivery_data, colWidths=[4.5*cm, 12*cm])
    d_t.setStyle(TableStyle([
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING',    (0,0), (-1,-1), 4),
        ('BACKGROUND',    (0,0), (0,-1),  LIGHT),
        ('GRID',          (0,0), (-1,-1), 0.5, LINE),
    ]))
    story.append(d_t)
    story.append(Spacer(1, 0.4*cm))

    # ── Shartnoma shartlari ───────────────────────────────────────────
    story.append(Paragraph("4. TOMONLARNING MAJBURIYATLARI", S('h1', fontSize=11, fontName='Helvetica-Bold', textColor=DARK, spaceBefore=8, spaceAfter=6)))
    default_terms = contract.terms or (
        "4.1. Sotuvchi mahsulotni sifatli va belgilangan muddatda yetkazib berishga majburdir.\n"
        "4.2. Xaridor buyurtma summasining 40% miqdorida oldindan to'lovni amalga oshiradi.\n"
        "4.3. Qolgan 60% qismi mahsulot yetkazib berilganidan so'ng 3 kun ichida to'lanadi.\n"
        "4.4. Mahsulot o'rnatilganidan so'ng Xaridor tomonidan qabul qilish dalolatnomasi imzolanadi.\n"
        "4.5. Kelishmovchiliklar O'zbekiston Respublikasi qonunchiligi asosida hal etiladi."
    )
    for line in default_terms.split('\n'):
        if line.strip():
            story.append(Paragraph(line.strip(), S('term', fontSize=9, textColor=DARK, leading=13, spaceAfter=3)))
    story.append(Spacer(1, 0.6*cm))

    # ── Imzolar ───────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=LINE, spaceAfter=12))
    story.append(Paragraph("5. TOMONLARNING IMZOLARI", S('h1', fontSize=11, fontName='Helvetica-Bold', textColor=DARK, spaceAfter=10)))

    sign_data = [
        [Paragraph("<b>SOTUVCHI:</b>", S('sl', fontSize=10)),
         Paragraph("<b>XARIDOR:</b>", S('sl', fontSize=10))],
        [Paragraph("<b>\"E-MEBEL\" MCHJ</b>", S('sv', fontSize=10, textColor=DARK)),
         Paragraph(f"<b>{client.name}</b>", S('sv', fontSize=10, textColor=DARK))],
        [Paragraph(f"Direktor: ___________________ <br/><font size=8>Raxmonov I.V.</font>", S('si', fontSize=10, spaceBefore=10)),
         Paragraph(f"___________________ <br/><font size=8>(imzo)</font>", S('si', fontSize=10, spaceBefore=10))],
        [Spacer(1, 1*cm), Spacer(1, 1*cm)],
        [Paragraph("M.P. ___________________", S('si', fontSize=9)),
         Paragraph(f"Sana: {date_str}", S('si', fontSize=9, textColor=GRAY))],
    ]
    sign_t = Table(sign_data, colWidths=[8.5*cm, 8.5*cm])
    sign_t.setStyle(TableStyle([
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LINEAFTER',     (0,0), (0,-1),  0.5, LINE),
    ]))
    story.append(sign_t)

    # ── Footer ────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.5*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=LINE))
    story.append(Paragraph(
        f"e-Mebel CRM  •  Shartnoma #{contract.contract_number}  •  {date_str} holatiga",
        S('ft', fontSize=8, textColor=GRAY, alignment=TA_CENTER, spaceBefore=6)
    ))

    doc.build(story)
    return buf.getvalue()