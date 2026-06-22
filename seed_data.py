"""
Run this script to populate the database with test data.
Usage: python seed_data.py
"""
import sqlite3
from models.database import init_db, get_db, close_db


def seed() -> None:
    init_db()
    db = get_db()
    try:
        _seed_clients(db)
        _seed_vehicles(db)
        _seed_drivers(db)
        _seed_settings(db)
        _seed_trips(db)
        db.commit()
        print("Seed data inserted successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
        raise
    finally:
        close_db(db)


def _seed_clients(db: sqlite3.Connection) -> None:
    clients = [
        ("Tata Steel Ltd", "9876543210", "steel@tatasteel.com",
         "Tarapur, Maharashtra", "27AAACT2727Q1ZV"),
        ("JSW Steel Ltd", "9876543211", "steel@jsw.com",
         "Kalamboli, Navi Mumbai, Maharashtra", "27AABCJ1234R1ZP"),
        ("BPSL Steel", "9876543212", "info@bpsl.com",
         "Khopoli, Maharashtra", "27AABCP5678S1ZQ"),
        ("Shree Cement Ltd", "9876543213", "cement@shreecement.com",
         "Beawar, Rajasthan", "08AADCS9876T1ZR"),
        ("Ambuja Cements", "9876543214", "info@ambuja.com",
         "Panvel, Maharashtra", "27AAECA1234U1ZS"),
    ]
    db.executemany(
        "INSERT OR IGNORE INTO clients (name, phone, email, address, gst_number) VALUES (?,?,?,?,?)",
        clients,
    )


def _seed_vehicles(db: sqlite3.Connection) -> None:
    vehicles = [
        ("MH-04-AB-1234", "truck", 20.0, "available"),
        ("MH-04-CD-5678", "truck", 16.0, "available"),
        ("MH-04-EF-9012", "trailer", 30.0, "on_trip"),
        ("MH-04-GH-3456", "truck", 20.0, "available"),
        ("MH-04-IJ-7890", "truck", 16.0, "maintenance"),
        ("MH-43-KL-2345", "trailer", 25.0, "available"),
        ("MH-04-MN-6789", "truck", 20.0, "on_trip"),
        ("RJ-14-OP-3456", "truck", 20.0, "available"),
    ]
    db.executemany(
        "INSERT OR IGNORE INTO vehicles (plate_number, vehicle_type, capacity_tons, status) VALUES (?,?,?,?)",
        vehicles,
    )


def _seed_drivers(db: sqlite3.Connection) -> None:
    drivers = [
        ("Ramesh Kumar", "8765432100", "MH0420210001234"),
        ("Suresh Patel", "8765432101", "MH0420190005678"),
        ("Ajay Singh", "8765432102", "RJ1420200009012"),
        ("Vikram Yadav", "8765432103", "MH0420220003456"),
        ("Deepak Sharma", "8765432104", "MH0420180007890"),
        ("Ravi Verma", "8765432105", "MH4320210002345"),
        ("Manoj Tiwari", "8765432106", "MH0420200006789"),
        ("Prakash Jha", "8765432107", "RJ1420190003456"),
    ]
    db.executemany(
        "INSERT OR IGNORE INTO drivers (name, phone, license_number) VALUES (?,?,?)",
        drivers,
    )


def _seed_settings(db: sqlite3.Connection) -> None:
    settings = [
        ("company_name", "MD Movers Pvt Ltd"),
        ("company_address", "Kalamboli, Navi Mumbai, Maharashtra"),
        ("company_phone", "022-27401234"),
        ("company_gst", "27AABCM1234R1ZP"),
        ("whatsapp_owner_phone", ""),
        ("whatsapp_enabled", "false"),
        ("traccar_enabled", "false"),
        ("traccar_url", ""),
        ("daily_summary_time", "08:00"),
    ]
    db.executemany(
        """INSERT INTO settings (key, value) VALUES (?,?)
           ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
        settings,
    )


def _seed_trips(db: sqlite3.Connection) -> None:
    # Fetch IDs inserted above
    clients = {row[0]: row[1] for row in db.execute("SELECT name, id FROM clients").fetchall()}
    vehicles = {row[0]: row[1] for row in db.execute("SELECT plate_number, id FROM vehicles").fetchall()}
    drivers = {row[0]: row[1] for row in db.execute("SELECT name, id FROM drivers").fetchall()}

    # 10 trips across various statuses
    trips = [
        # (client, vehicle, driver, from, to, goods, weight, pkgs, freight, advance, status, lr, invoice, dispatched_at, delivered_at, paid_at)
        (
            clients["Tata Steel Ltd"], vehicles["MH-04-AB-1234"], drivers["Ramesh Kumar"],
            "Tarapur, Maharashtra", "Kalamboli, Navi Mumbai",
            "HR Coils", 18.0, 24, 42000, 20000,
            "paid", "LR-2026-0001", "INV-2026-0001",
            "2026-06-01 08:00:00", "2026-06-02 16:00:00", "2026-06-05 11:00:00",
        ),
        (
            clients["JSW Steel Ltd"], vehicles["MH-04-CD-5678"], drivers["Suresh Patel"],
            "Kalamboli, Navi Mumbai", "Bhiwandi, Thane",
            "Steel Pipes", 14.0, 60, 28000, 15000,
            "paid", "LR-2026-0002", "INV-2026-0002",
            "2026-06-05 09:30:00", "2026-06-06 14:00:00", "2026-06-09 10:00:00",
        ),
        (
            clients["BPSL Steel"], vehicles["MH-04-EF-9012"], drivers["Ajay Singh"],
            "Khopoli, Maharashtra", "Bhiwandi, Thane",
            "TMT Bars", 28.0, 40, 35000, 18000,
            "in_transit", "LR-2026-0003", None,
            "2026-06-18 07:00:00", None, None,
        ),
        (
            clients["Shree Cement Ltd"], vehicles["MH-04-MN-6789"], drivers["Manoj Tiwari"],
            "Beawar, Rajasthan", "Panvel, Maharashtra",
            "Cement Bags", 19.0, 800, 145000, 70000,
            "in_transit", "LR-2026-0004", None,
            "2026-06-20 06:00:00", None, None,
        ),
        (
            clients["Ambuja Cements"], vehicles["MH-43-KL-2345"], drivers["Ravi Verma"],
            "Panvel, Maharashtra", "Tarapur, Maharashtra",
            "Cement Bags", 22.0, 900, 38000, 20000,
            "dispatched", "LR-2026-0005", None,
            "2026-06-21 10:00:00", None, None,
        ),
        (
            clients["Tata Steel Ltd"], vehicles["MH-04-GH-3456"], drivers["Vikram Yadav"],
            "Tarapur, Maharashtra", "Khopoli, Maharashtra",
            "CR Sheets", 17.0, 30, 32000, 15000,
            "assigned", None, None,
            None, None, None,
        ),
        (
            clients["JSW Steel Ltd"], None, None,
            "Kalamboli, Navi Mumbai", "Beawar, Rajasthan",
            "Wire Rods", 15.0, 50, 125000, 60000,
            "created", None, None,
            None, None, None,
        ),
        (
            clients["BPSL Steel"], None, None,
            "Khopoli, Maharashtra", "Kalamboli, Navi Mumbai",
            "Billets", 20.0, 10, 22000, 0,
            "created", None, None,
            None, None, None,
        ),
        (
            clients["Shree Cement Ltd"], vehicles["RJ-14-OP-3456"], drivers["Prakash Jha"],
            "Beawar, Rajasthan", "Bhiwandi, Thane",
            "Cement Bags", 18.0, 720, 138000, 65000,
            "delivered", "LR-2026-0006", None,
            "2026-06-15 07:00:00", "2026-06-17 18:00:00", None,
        ),
        (
            clients["Ambuja Cements"], vehicles["MH-04-AB-1234"], drivers["Deepak Sharma"],
            "Panvel, Maharashtra", "Khopoli, Maharashtra",
            "Cement Clinker", 20.0, 400, 15000, 8000,
            "invoiced", "LR-2026-0007", "INV-2026-0003",
            "2026-06-10 09:00:00", "2026-06-11 15:00:00", None,
        ),
    ]

    for t in trips:
        (client_id, vehicle_id, driver_id, from_loc, to_loc, goods,
         weight, pkgs, freight, advance, status, lr, invoice,
         dispatched_at, delivered_at, paid_at) = t

        balance = freight - advance
        db.execute(
            """INSERT INTO trips
               (client_id, vehicle_id, driver_id, from_location, to_location,
                goods_description, weight_tons, num_packages, freight_amount,
                advance_paid, balance_amount, status, lr_number, invoice_number,
                dispatched_at, delivered_at, paid_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (client_id, vehicle_id, driver_id, from_loc, to_loc, goods,
             weight, pkgs, freight, advance, balance, status, lr, invoice,
             dispatched_at, delivered_at, paid_at),
        )

    # Add activity log entries for seeded trips
    trip_ids = [row[0] for row in db.execute("SELECT id FROM trips ORDER BY id").fetchall()]
    statuses = [t[10] for t in trips]
    actions = {
        'created': 'CREATED', 'assigned': 'ASSIGNED', 'dispatched': 'DISPATCHED',
        'in_transit': 'IN_TRANSIT', 'delivered': 'DELIVERED',
        'invoiced': 'INVOICED', 'paid': 'PAID',
    }
    for trip_id, status in zip(trip_ids, statuses):
        db.execute(
            "INSERT INTO activity_log (trip_id, action, message) VALUES (?,?,?)",
            (trip_id, actions.get(status, status.upper()), f"Seed data: trip in {status} status"),
        )


if __name__ == '__main__':
    seed()
