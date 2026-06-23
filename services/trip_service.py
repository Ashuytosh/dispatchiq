from datetime import date
from typing import Any
from models import trip as trip_model
from models import vehicle as vehicle_model
from models.database import get_db, close_db


def _log_activity(trip_id: int, action: str, message: str) -> None:
    db = get_db()
    try:
        db.execute(
            "INSERT INTO activity_log (trip_id, action, message) VALUES (?, ?, ?)",
            (trip_id, action, message),
        )
        db.commit()
    finally:
        close_db(db)


def create_new_trip(data: dict[str, Any]) -> int:
    required = ['client_id', 'from_location', 'to_location', 'freight_amount']
    missing = [f for f in required if not data.get(f)]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    trip_id = trip_model.create_trip(
        client_id=int(data['client_id']),
        from_location=data['from_location'],
        to_location=data['to_location'],
        goods_description=data.get('goods_description', ''),
        weight_tons=float(data.get('weight_tons') or 0),
        num_packages=int(data.get('num_packages') or 0),
        freight_amount=float(data['freight_amount']),
        advance_paid=float(data.get('advance_paid') or 0),
    )
    _log_activity(trip_id, 'CREATED', f"Trip created: {data['from_location']} → {data['to_location']}")
    return trip_id


def assign_vehicle_and_driver(trip_id: int, vehicle_id: int, driver_id: int) -> None:
    trip_model.assign_trip(trip_id, vehicle_id, driver_id)
    vehicle_model.update_vehicle_status(vehicle_id, 'on_trip')
    _log_activity(trip_id, 'ASSIGNED', f"Assigned vehicle #{vehicle_id} and driver #{driver_id}")


def advance_trip_status(trip_id: int, new_status: str) -> None:
    trip = trip_model.get_trip_by_id(trip_id)
    if not trip:
        raise ValueError(f"Trip {trip_id} not found")

    trip_model.update_trip_status(trip_id, new_status)

    if new_status == 'dispatched':
        lr_number = trip_model.generate_lr_number()
        trip_model.set_trip_lr_number(trip_id, lr_number)
        _log_activity(trip_id, 'DISPATCHED', f"Trip dispatched. LR generated: {lr_number}")

    elif new_status == 'in_transit':
        _log_activity(trip_id, 'IN_TRANSIT', "Vehicle in transit")

    elif new_status == 'delivered':
        if trip['vehicle_id']:
            vehicle_model.update_vehicle_status(trip['vehicle_id'], 'available')
        _log_activity(trip_id, 'DELIVERED', "Goods delivered at destination")

    elif new_status == 'invoiced':
        invoice_number = trip_model.generate_invoice_number()
        trip_model.set_trip_invoice_number(trip_id, invoice_number)
        _log_activity(trip_id, 'INVOICED', f"Invoice generated: {invoice_number}")

    elif new_status == 'paid':
        _log_activity(trip_id, 'PAID', "Payment received. Trip closed.")

    else:
        _log_activity(trip_id, new_status.upper(), f"Status updated to {new_status}")


def cancel_trip(trip_id: int) -> None:
    trip = trip_model.get_trip_by_id(trip_id)
    if not trip:
        raise ValueError(f"Trip {trip_id} not found")

    trip_model.update_trip_status(trip_id, 'cancelled')

    if trip['vehicle_id'] and trip['status'] in ('assigned',):
        vehicle_model.update_vehicle_status(trip['vehicle_id'], 'available')

    _log_activity(trip_id, 'CANCELLED', "Trip cancelled")


def get_dashboard_stats() -> dict[str, Any]:
    stats = trip_model.get_trip_stats()
    today = date.today().isoformat()
    db = get_db()
    try:
        row = db.execute(
            "SELECT COUNT(*) as cnt FROM trips WHERE DATE(created_at) = ?", (today,)
        ).fetchone()
        today_created = row['cnt'] if row else 0

        row = db.execute(
            "SELECT COUNT(*) as cnt FROM trips WHERE DATE(delivered_at) = ?", (today,)
        ).fetchone()
        today_delivered = row['cnt'] if row else 0

        row = db.execute(
            "SELECT COALESCE(SUM(freight_amount), 0) as total FROM trips WHERE DATE(paid_at) = ?",
            (today,),
        ).fetchone()
        today_revenue = row['total'] if row else 0

        row = db.execute(
            "SELECT COALESCE(SUM(freight_amount), 0) as total FROM trips "
            "WHERE strftime('%Y-%m', paid_at) = strftime('%Y-%m', 'now')"
        ).fetchone()
        month_revenue = row['total'] if row else 0
    finally:
        close_db(db)

    return {
        **stats,
        'today_created': today_created,
        'today_delivered': today_delivered,
        'today_revenue': today_revenue,
        'month_revenue': month_revenue,
        'active': stats.get('assigned', 0) + stats.get('dispatched', 0) + stats.get('in_transit', 0),
    }
