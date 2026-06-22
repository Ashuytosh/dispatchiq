# DispatchIQ — Project Conventions

## Architecture
- Flask app using Application Factory pattern
- MVC: models/ for database, routes/ for endpoints, templates/ for HTML
- Service Layer: all business logic in services/ — routes only call services
- SQLite database — single file dispatchiq.db

## Code Rules
- Python 3.11+
- Use type hints for all function parameters and returns
- Every database query goes in models/ — never write SQL in routes or services
- Use flask blueprints for route organization
- All settings stored in SQLite settings table — no hardcoded config
- Indian formats: DD-MM-YYYY for dates, ₹ for currency

## File Structure
dispatchiq/
├── app.py                    — Flask app factory
├── models/
│   ├── database.py           — SQLite connection + init_db()
│   ├── client.py             — Client model + queries
│   ├── vehicle.py            — Vehicle model + queries
│   ├── driver.py             — Driver model + queries
│   ├── trip.py               — Trip model + queries
│   └── settings.py           — Settings key-value store
├── services/
│   ├── trip_service.py       — Trip lifecycle + state machine
│   ├── lr_generator.py       — LR/Bilti PDF generation
│   ├── invoice_generator.py  — Invoice PDF generation
│   └── notification_service.py — WhatsApp/Telegram sending
├── routes/
│   ├── dashboard_routes.py   — Dashboard + stats
│   ├── trip_routes.py        — Trip CRUD + status changes
│   ├── vehicle_routes.py     — Vehicle CRUD
│   ├── driver_routes.py      — Driver CRUD
│   ├── client_routes.py      — Client CRUD
│   ├── settings_routes.py    — Settings page
│   └── api_routes.py         — JSON API endpoints for external systems
├── templates/
│   ├── base.html             — Layout with nav + Tailwind CDN
│   ├── dashboard.html
│   ├── trips/
│   ├── vehicles/
│   ├── drivers/
│   ├── clients/
│   └── settings.html
├── static/
├── seed_data.py              — Generates test data
├── requirements.txt
└── run.py                    — Entry point

## Database
- SQLite file: dispatchiq.db
- Created automatically on first run via init_db()
- Settings table: key (TEXT UNIQUE), value (TEXT), updated_at (TIMESTAMP)

## Trip State Machine Rules
- CREATED → ASSIGNED (requires vehicle_id and driver_id)
- ASSIGNED → DISPATCHED (generates LR automatically)
- DISPATCHED → IN_TRANSIT (vehicle has started moving)
- IN_TRANSIT → DELIVERED (goods received)
- DELIVERED → INVOICED (generates invoice automatically)
- INVOICED → PAID (payment received)
- Any pre-DISPATCHED status → CANCELLED
- No backward transitions allowed