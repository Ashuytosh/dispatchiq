import io
import os
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
    bank_name = settings.get('bank_name', '')
    bank_account = settings.get('bank_account', '')
    bank_ifsc = settings.get('bank_ifsc', '')

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
    right_bold_style = ParagraphStyle('rightBold', parent=styles['Normal'], fontSize=11,
                                       alignment=TA_RIGHT, fontName='Helvetica-Bold')

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
         Paragraph(f"{trip['weight_tons'] or 0} MT", value_style),
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

    freight = float(trip['freight_amount'] or 0)
    cgst = freight * 0.09
    sgst = freight * 0.09
    total = freight + cgst + sgst
    advance = float(trip['advance_paid'] or 0)
    balance = total - advance

    total_data = [
        ['', '', '', '', Paragraph('Freight Charges:', label_style),
         Paragraph(f"₹{freight:,.0f}", right_style)],
        ['', '', '', '', Paragraph('CGST (9%):', label_style),
         Paragraph(f"₹{cgst:,.0f}", right_style)],
        ['', '', '', '', Paragraph('SGST (9%):', label_style),
         Paragraph(f"₹{sgst:,.0f}", right_style)],
        ['', '', '', '', Paragraph('<b>Total Amount:</b>', value_style),
         Paragraph(f"<b>₹{total:,.0f}</b>", right_bold_style)],
        ['', '', '', '', Paragraph('Advance Received:', label_style),
         Paragraph(f"₹{advance:,.0f}", right_style)],
        ['', '', '', '', Paragraph('<b>Balance Due:</b>', value_style),
         Paragraph(f"<b>₹{balance:,.0f}</b>", right_bold_style)],
    ]
    total_table = Table(total_data, colWidths=[1*cm, 5*cm, 3*cm, 3*cm, 3.5*cm, 2.5*cm])
    total_table.setStyle(TableStyle([
        ('LINEABOVE', (4, 3), (-1, 3), 1, colors.grey),
        ('LINEABOVE', (4, 5), (-1, 5), 1, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(total_table)
    story.append(Spacer(1, 0.8*cm))

    # Payment / bank details
    bank_lines = ['<b>Payment Mode: Bank Transfer</b>']
    if bank_name:
        bank_lines.append(f"Bank: {bank_name}")
    if bank_account:
        bank_lines.append(f"Account No.: {bank_account}")
    if bank_ifsc:
        bank_lines.append(f"IFSC: {bank_ifsc}")
    if not (bank_name or bank_account or bank_ifsc):
        bank_lines.append("Bank details: [Please update in Settings]")

    bank_style = ParagraphStyle('bank', parent=styles['Normal'], fontSize=9,
                                 backColor=colors.HexColor('#f8fafc'), borderPad=6)
    story.append(Paragraph('<br/>'.join(bank_lines), bank_style))
    story.append(Spacer(1, 0.8*cm))

    story.append(HRFlowable(width='100%', thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 0.4*cm))

    sig_data = [
        [Paragraph('Customer Signature', label_style), '',
         Paragraph(f'For {company_name}', label_style)],
        ['', '', ''],
        [Paragraph('________________________', label_style), '',
         Paragraph('________________________', label_style)],
        ['', '', Paragraph('Authorised Signatory', label_style)],
    ]
    sig_table = Table(sig_data, colWidths=[7*cm, 3*cm, 7*cm])
    sig_table.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(sig_table)
    story.append(Spacer(1, 0.5*cm))

    footer_style = ParagraphStyle('footer', parent=styles['Normal'], alignment=TA_CENTER,
                                   fontSize=8, textColor=colors.grey)
    story.append(Paragraph("This is a computer generated invoice.", footer_style))
    story.append(Paragraph(company_name, footer_style))

    doc.build(story)
    return buffer.getvalue()


def generate_invoice(trip_id: int) -> str:
    from models import trip as trip_model
    from models import document as document_model

    trip = trip_model.get_trip_by_id(trip_id)
    if not trip:
        raise ValueError(f"Trip {trip_id} not found")
    if not trip['invoice_number']:
        raise ValueError(f"Trip {trip_id} has no invoice number — cannot generate invoice PDF")

    pdf_bytes = generate_invoice_pdf(trip)

    out_dir = os.path.join('static', 'documents', 'invoices')
    os.makedirs(out_dir, exist_ok=True)
    file_path = os.path.join(out_dir, f"{trip['invoice_number']}.pdf")

    with open(file_path, 'wb') as f:
        f.write(pdf_bytes)

    document_model.save_document(trip_id, 'invoice', file_path)
    return file_path
