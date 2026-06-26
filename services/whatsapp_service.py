import requests
from typing import Any

_WA_URL = "http://localhost:3001"
_TIMEOUT = 3


def check_whatsapp_status() -> bool:
    try:
        r = requests.get(f"{_WA_URL}/status", timeout=_TIMEOUT)
        return bool(r.json().get('connected'))
    except Exception:
        return False


def send_whatsapp(phone: str, message: str) -> bool:
    try:
        r = requests.post(
            f"{_WA_URL}/send",
            json={"phone": phone, "message": message},
            timeout=_TIMEOUT,
        )
        return bool(r.json().get('success'))
    except Exception:
        return False


def format_trip_alert(trip: Any, status: str, company_name: str) -> str:
    tid = trip['id']
    frm = trip['from_location'] or ''
    to = trip['to_location'] or ''
    plate = trip['plate_number'] or ''
    driver = trip['driver_name'] or ''
    driver_ph = trip['driver_phone'] or ''
    weight = trip['weight_tons'] or 0
    freight = float(trip['freight_amount'] or 0)
    lr = trip['lr_number'] or ''
    inv = trip['invoice_number'] or ''
    total_gst = freight * 1.18

    if status == 'assigned':
        return (
            f"📦 DispatchIQ — {company_name}\n"
            f"Trip #{tid} Assigned\n"
            f"━━━━━━━━━━━━━━\n"
            f"From: {frm}\n"
            f"To: {to}\n"
            f"Vehicle: {plate}\n"
            f"Driver: {driver} ({driver_ph})\n"
            f"Weight: {weight} MT\n"
            f"Freight: ₹{freight:,.0f}"
        )

    if status == 'dispatched':
        return (
            f"🚛 DispatchIQ — {company_name}\n"
            f"Trip #{tid} Dispatched!\n"
            f"━━━━━━━━━━━━━━\n"
            f"LR Number: {lr}\n"
            f"From: {frm}\n"
            f"To: {to}\n"
            f"Vehicle: {plate}\n"
            f"Driver: {driver}"
        )

    if status == 'in_transit':
        return (
            f"🛣️ Vehicle {plate} is in transit\n"
            f"{frm} → {to}"
        )

    if status == 'delivered':
        return (
            f"✅ Delivery Complete!\n"
            f"Trip #{tid} delivered successfully\n"
            f"{frm} → {to}\n"
            f"Vehicle: {plate}"
        )

    if status == 'invoiced':
        return (
            f"🧾 Invoice Generated\n"
            f"Invoice: {inv}\n"
            f"Amount: ₹{total_gst:,.0f}\n"
            f"Trip: {frm} → {to}"
        )

    if status == 'paid':
        return (
            f"💰 Payment Received\n"
            f"Trip #{tid} — ₹{freight:,.0f}\n"
            f"Status: COMPLETED ✅"
        )

    return f"DispatchIQ — Trip #{tid} status: {status}"
