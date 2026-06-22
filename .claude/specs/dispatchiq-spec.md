# DispatchIQ — Product Specification

## 1. What Is This?
A trip management system for small logistics/transport companies.
Manages the full lifecycle: client booking → vehicle assignment → 
LR/Bilti generation → dispatch → tracking → delivery → invoice → payment.

## 2. Core Entities
- CLIENT: Company sending goods (name, phone, address, GST number)
- VEHICLE: Truck/trailer (plate number, type, capacity in tons, status)
- DRIVER: Person driving (name, phone, license number, assigned vehicle)
- TRIP: One shipment from A to B (the MAIN entity everything connects to)
- DOCUMENT: Generated PDFs (LR/Bilti, Invoice) linked to a trip
- ACTIVITY_LOG: Every action on a trip is logged with timestamp
- SETTINGS: Key-value store for all configuration (company info, phones, integrations)

## 3. Trip Lifecycle (State Machine)
CREATED → ASSIGNED → DISPATCHED → IN_TRANSIT → DELIVERED → INVOICED → PAID
Also: Any pre-dispatch trip can be CANCELLED.
Each transition triggers: database update + activity log + optional notification.

## 4. Tech Stack
- Backend: Flask (Python 3.11+)
- Database: SQLite
- Frontend: Jinja2 templates + Tailwind CSS (CDN)
- PDF Generation: ReportLab
- All settings stored in SQLite, configurable via web UI
- No paid APIs required for core functionality