import calendar
from datetime import date, timedelta
from models import trip as trip_model
from models import payment as payment_model

STATUS_ORDER = ['created', 'assigned', 'dispatched', 'in_transit',
                'delivered', 'invoiced', 'paid', 'cancelled']
STATUS_LABELS = ['Created', 'Assigned', 'Dispatched', 'In Transit',
                 'Delivered', 'Invoiced', 'Paid', 'Cancelled']
STATUS_COLORS = ['#6B7280', '#3B82F6', '#EAB308', '#F97316',
                 '#22C55E', '#A855F7', '#10B981', '#EF4444']

MONTH_ABBR = calendar.month_abbr  # index 1-12


def _last_n_month_keys(n: int, today: date) -> list[tuple[str, str]]:
    keys = []
    y, m = today.year, today.month
    for _ in range(n):
        keys.append((f"{y:04d}-{m:02d}", MONTH_ABBR[m]))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return list(reversed(keys))


def _last_n_day_keys(n: int, today: date) -> list[tuple[str, str]]:
    return [
        ((today - timedelta(days=i)).isoformat(),
         f"{(today - timedelta(days=i)).day:02d}-{MONTH_ABBR[(today - timedelta(days=i)).month]}")
        for i in range(n - 1, -1, -1)
    ]


def get_dashboard_chart_data() -> dict:
    today = date.today()

    month_keys = _last_n_month_keys(6, today)
    revenue_by_ym = {r['ym']: r['total_revenue'] for r in trip_model.get_monthly_revenue_trend(6)}
    monthly_revenue = {
        'labels': [label for _, label in month_keys],
        'data': [revenue_by_ym.get(ym, 0) for ym, _ in month_keys],
    }

    stats = trip_model.get_trip_stats()
    trips_by_status = {
        'labels': STATUS_LABELS,
        'data': [stats[s] for s in STATUS_ORDER],
        'colors': STATUS_COLORS,
    }

    top_rows = payment_model.get_top_clients_by_revenue(5)
    top_clients = {
        'labels': [r['client_name'] for r in top_rows],
        'data': [r['total_freight'] for r in top_rows],
    }

    day_keys = _last_n_day_keys(30, today)
    count_by_day = {r['day']: r['trip_count'] for r in trip_model.get_daily_trip_counts(30)}
    daily_trips = {
        'labels': [label for _, label in day_keys],
        'data': [count_by_day.get(iso, 0) for iso, _ in day_keys],
    }

    return {
        'monthly_revenue': monthly_revenue,
        'trips_by_status': trips_by_status,
        'top_clients': top_clients,
        'daily_trips': daily_trips,
    }
