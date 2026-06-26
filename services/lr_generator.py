import io
import os
import sqlite3
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from models.settings import get_all_settings


def generate_lr_pdf(trip: sqlite3.Row) -> bytes:
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
                                    fontSize=13, spaceAfter=6, borderPad=4,
                                    backColor=colors.HexColor('#1e293b'),
                                    textColor=colors.white)
    story.append(Paragraph("LORRY RECEIPT (LR / BILTI)", heading_style))
    story.append(Spacer(1, 0.4*cm))

    lr_date = trip['dispatched_at'] or trip['created_at'] or ''
    if lr_date:
        try:
            dt = datetime.fromisoformat(lr_date[:19])
            lr_date = dt.strftime('%d-%m-%Y')
        except Exception:
            lr_date = str(lr_date)[:10]

    header_data = [
        [Paragraph('<b>LR Number</b>', label_style), Paragraph(str(trip['lr_number'] or ''), value_style),
         Paragraph('<b>Date</b>', label_style), Paragraph(lr_date, value_style)],
    ]
    header_table = Table(header_data, colWidths=[3.5*cm, 5.5*cm, 2.5*cm, 5.5*cm])
    header_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#f1f5f9')),
        ('BACKGROUND', (2, 0), (2, 0), colors.HexColor('#f1f5f9')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.4*cm))

    consignor_data = [
        [Paragraph('<b>Consignor (From)</b>', label_style), Paragraph('<b>Consignee (To)</b>', label_style)],
        [Paragraph(str(trip['client_name'] or ''), value_style),
         Paragraph(str(trip['to_location'] or ''), value_style)],
        [Paragraph(str(trip['client_address'] or ''), label_style),
         Paragraph('', label_style)],
        [Paragraph(f"GST: {trip['client_gst'] or ''}", label_style),
         Paragraph('', label_style)],
    ]
    consignor_table = Table(consignor_data, colWidths=[8.5*cm, 8.5*cm])
    consignor_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(consignor_table)
    story.append(Spacer(1, 0.4*cm))

    # Vehicle & driver details (4 columns: vehicle no., vehicle type, driver name, driver phone+license)
    driver_info = str(trip['driver_name'] or '')
    if trip['driver_phone']:
        driver_info += f"\nPh: {trip['driver_phone']}"
    if trip['driver_license']:
        driver_info += f"\nLic: {trip['driver_license']}"

    route_data = [
        [Paragraph('<b>From</b>', label_style), Paragraph('<b>To</b>', label_style),
         Paragraph('<b>Vehicle No.</b>', label_style), Paragraph('<b>Driver Details</b>', label_style)],
        [Paragraph(str(trip['from_location'] or ''), value_style),
         Paragraph(str(trip['to_location'] or ''), value_style),
         Paragraph(f"{trip['plate_number'] or ''}\n{trip['vehicle_type'] or ''}", value_style),
         Paragraph(driver_info, value_style)],
    ]
    route_table = Table(route_data, colWidths=[4.25*cm, 4.25*cm, 4.25*cm, 4.25*cm])
    route_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(route_table)
    story.append(Spacer(1, 0.4*cm))

    goods_data = [
        [Paragraph('<b>Goods Description</b>', label_style),
         Paragraph('<b>Weight (MT)</b>', label_style),
         Paragraph('<b>Packages</b>', label_style),
         Paragraph('<b>Freight (₹)</b>', label_style)],
        [Paragraph(str(trip['goods_description'] or ''), value_style),
         Paragraph(f"{trip['weight_tons'] or 0} MT", value_style),
         Paragraph(str(trip['num_packages'] or ''), value_style),
         Paragraph(f"₹{float(trip['freight_amount'] or 0):,.0f}", value_style)],
    ]
    goods_table = Table(goods_data, colWidths=[7*cm, 3*cm, 3*cm, 4*cm])
    goods_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(goods_table)
    story.append(Spacer(1, 0.4*cm))

    balance = float(trip['balance_amount'] or 0)
    payment_mode = 'To Pay' if balance > 0 else 'Paid'

    payment_data = [
        [Paragraph('<b>Freight Amount</b>', label_style),
         Paragraph('<b>Advance Paid</b>', label_style),
         Paragraph('<b>Balance Due</b>', label_style),
         Paragraph('<b>Payment Mode</b>', label_style)],
        [Paragraph(f"₹{float(trip['freight_amount'] or 0):,.0f}", value_style),
         Paragraph(f"₹{float(trip['advance_paid'] or 0):,.0f}", value_style),
         Paragraph(f"₹{balance:,.0f}", value_style),
         Paragraph(payment_mode, value_style)],
    ]
    payment_table = Table(payment_data, colWidths=[4.25*cm, 4.25*cm, 4.25*cm, 4.25*cm])
    payment_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(payment_table)
    story.append(Spacer(1, 1*cm))

    sig_data = [
        [Paragraph('Consignor Signature', label_style), Paragraph('', label_style),
         Paragraph(f'For {company_name}', label_style)],
        [Paragraph('', value_style), Paragraph('', value_style), Paragraph('', value_style)],
        [Paragraph('________________________', label_style), Paragraph('', label_style),
         Paragraph('________________________', label_style)],
        [Paragraph('', label_style), Paragraph('', label_style),
         Paragraph('Authorised Signatory', label_style)],
    ]
    sig_table = Table(sig_data, colWidths=[5.67*cm, 5.67*cm, 5.67*cm])
    sig_table.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(sig_table)
    story.append(Spacer(1, 0.5*cm))

    footer_style = ParagraphStyle('footer', parent=styles['Normal'], alignment=TA_CENTER,
                                   fontSize=8, textColor=colors.grey)
    story.append(Paragraph("This is a computer generated document.", footer_style))
    story.append(Paragraph(company_name, footer_style))

    doc.build(story)
    return buffer.getvalue()


def generate_lr(trip_id: int) -> str:
    from models import trip as trip_model
    from models import document as document_model

    trip = trip_model.get_trip_by_id(trip_id)
    if not trip:
        raise ValueError(f"Trip {trip_id} not found")
    if not trip['lr_number']:
        raise ValueError(f"Trip {trip_id} has no LR number — cannot generate LR PDF")

    pdf_bytes = generate_lr_pdf(trip)

    out_dir = os.path.join('static', 'documents', 'lr')
    os.makedirs(out_dir, exist_ok=True)
    file_path = os.path.join(out_dir, f"{trip['lr_number']}.pdf")

    with open(file_path, 'wb') as f:
        f.write(pdf_bytes)

    document_model.save_document(trip_id, 'lr', file_path)
    return file_path
