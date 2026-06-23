import io
import sqlite3
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from models.settings import get_all_settings


def generate_invoice_pdf(trip: sqlite3.Row) -> bytes:
    settings = get_all_settings()
    company_name = settings.get('company_name', 'DispatchIQ Logistics')
    company_address = settings.get('company_address', '')
    company_phone = settings.get('company_phone', '')
    company_gst = settings.get('company_gst', '')

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('title', parent=styles['Heading1'], alignment=TA_CENTER,
                                  fontSize=16, spaceAfter=4)
    sub_style = ParagraphStyle('sub', parent=styles['Normal'], alignment=TA_CENTER,
                                fontSize=9, spaceAfter=2)
    label_style = ParagraphStyle('label', parent=styles['Normal'], fontSize=9,
                                  textColor=colors.grey)
    value_style = ParagraphStyle('value', parent=styles['Normal'], fontSize=10)
    right_style = ParagraphStyle('right', parent=styles['Normal'], fontSize=10,
                                  alignment=TA_RIGHT)

    story.append(Paragraph(company_name, title_style))
    if company_address:
        story.append(Paragraph(company_address, sub_style))
    contact_parts = []
    if company_phone:
        contact_parts.append(f"Ph: {company_phone}")
    if company_gst:
        contact_parts.append(f"GST: {company_gst}")
    if contact_parts:
        story.append(Paragraph("  |  ".join(contact_parts), sub_style))
    story.append(Spacer(1, 0.3*cm))

    heading_style = ParagraphStyle('heading', parent=styles['Heading2'], alignment=TA_CENTER,
                                    fontSize=13, spaceAfter=6,
                                    backColor=colors.HexColor('#1e293b'),
                                    textColor=colors.white)
    story.append(Paragraph("TAX INVOICE", heading_style))
    story.append(Spacer(1, 0.4*cm))

    inv_date = trip['paid_at'] or trip['created_at'] or ''
    if inv_date:
        try:
            dt = datetime.fromisoformat(inv_date[:19])
            inv_date = dt.strftime('%d-%m-%Y')
        except Exception:
            inv_date = str(inv_date)[:10]

    header_data = [
        [Paragraph('<b>Invoice Number</b>', label_style),
         Paragraph(str(trip['invoice_number'] or ''), value_style),
         Paragraph('<b>Date</b>', label_style),
         Paragraph(inv_date, value_style)],
        [Paragraph('<b>LR Number</b>', label_style),
         Paragraph(str(trip['lr_number'] or ''), value_style),
         Paragraph('<b>Reference</b>', label_style),
         Paragraph(f"Trip #{trip['id']}", value_style)],
    ]
    header_table = Table(header_data, colWidths=[3.5*cm, 5.5*cm, 2.5*cm, 5.5*cm])
    header_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#f1f5f9')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.4*cm))

    bill_to_text = f"""<b>Bill To:</b><br/>
    {trip['client_name'] or ''}<br/>
    {trip['client_address'] or ''}<br/>
    GST: {trip['client_gst'] or ''}<br/>
    Ph: {trip['client_phone'] or ''}"""
    story.append(Paragraph(bill_to_text, value_style))
    story.append(Spacer(1, 0.4*cm))

    items_data = [
        [Paragraph('<b>#</b>', label_style),
         Paragraph('<b>Description</b>', label_style),
         Paragraph('<b>From</b>', label_style),
         Paragraph('<b>To</b>', label_style),
         Paragraph('<b>Weight</b>', label_style),
         Paragraph('<b>Amount (₹)</b>', label_style)],
        [Paragraph('1', value_style),
         Paragraph(f"Transportation of goods\n{trip['goods_description'] or ''}", value_style),
         Paragraph(str(trip['from_location'] or ''), value_style),
         Paragraph(str(trip['to_location'] or ''), value_style),
         Paragraph(f"{trip['weight_tons'] or 0} T", value_style),
         Paragraph(f"₹{float(trip['freight_amount'] or 0):,.0f}", right_style)],
    ]
    items_table = Table(items_data, colWidths=[1*cm, 5*cm, 3*cm, 3*cm, 2*cm, 3*cm])
    items_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 0.2*cm))

    total_data = [
        ['', '', '', '', Paragraph('Freight Amount:', label_style),
         Paragraph(f"₹{float(trip['freight_amount'] or 0):,.0f}", right_style)],
        ['', '', '', '', Paragraph('Advance Paid:', label_style),
         Paragraph(f"₹{float(trip['advance_paid'] or 0):,.0f}", right_style)],
        ['', '', '', '', Paragraph('<b>Balance Due:</b>', value_style),
         Paragraph(f"<b>₹{float(trip['balance_amount'] or 0):,.0f}</b>", right_style)],
    ]
    total_table = Table(total_data, colWidths=[1*cm, 5*cm, 3*cm, 3*cm, 3.5*cm, 2.5*cm])
    total_table.setStyle(TableStyle([
        ('LINEABOVE', (4, 2), (-1, 2), 1, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(total_table)
    story.append(Spacer(1, 1*cm))

    story.append(HRFlowable(width='100%', thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 0.4*cm))

    sig_data = [
        [Paragraph('Customer Signature', label_style), '',
         Paragraph(f'For {company_name}', label_style)],
        ['', '', ''],
        [Paragraph('________________________', label_style), '',
         Paragraph('________________________', label_style)],
    ]
    sig_table = Table(sig_data, colWidths=[7*cm, 3*cm, 7*cm])
    sig_table.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(sig_table)

    doc.build(story)
    return buffer.getvalue()
