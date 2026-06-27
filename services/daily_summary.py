from datetime import date
from google import genai
from models.settings import get_setting
from models.database import get_db, close_db
from models import trip as trip_model


def _get_overdue_trips() -> list[dict]:
    db = get_db()
    try:
        rows = db.execute(
            """SELECT id, from_location, to_location, status,
                      CAST(julianday('now') - julianday(dispatched_at) AS INTEGER) as days_out
               FROM trips
               WHERE status IN ('dispatched', 'in_transit')
                 AND dispatched_at IS NOT NULL
                 AND julianday('now') - julianday(dispatched_at) >= 2
               ORDER BY days_out DESC""",
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_db(db)


def _get_today_revenue() -> float:
    db = get_db()
    today = date.today().isoformat()
    try:
        row = db.execute(
            "SELECT COALESCE(SUM(freight_amount), 0) as total FROM trips WHERE DATE(paid_at) = ?",
            (today,),
        ).fetchone()
        return float(row['total']) if row else 0.0
    finally:
        close_db(db)


def generate_daily_summary() -> str:
    api_key = get_setting('gemini_api_key', '')
    if not api_key:
        print("⚠️ Gemini API key not configured — skipping daily summary")
        return ''
    try:
        stats = trip_model.get_trip_stats()
        revenue = _get_today_revenue()
        overdue = _get_overdue_trips()
        company = get_setting('company_name', 'DispatchIQ')

        overdue_text = ', '.join(
            f"Trip #{t['id']} ({t['from_location']}→{t['to_location']}, {t['days_out']}d)"
            for t in overdue
        ) or 'None'

        prompt = f"""You are a fleet manager assistant for {company}, an Indian logistics company.
Generate a daily WhatsApp summary in Hinglish (Hindi + English mix).
Use emojis. Keep under 250 words.

Today's data:
- Total trips: {stats['total']}
- Created today: {stats.get('created', 0)}
- In Transit: {stats.get('in_transit', 0)}
- Delivered: {stats.get('delivered', 0)}
- Paid: {stats.get('paid', 0)}
- Revenue today: ₹{revenue:,.0f}
- Overdue trips (2+ days): {overdue_text}

Include: summary of today's operations, revenue highlight, any attention items, one motivational closing line for the team."""

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )

        u = response.usage_metadata
        print("═══════════════════════════════════════")
        print("🤖 GEMINI API CALL — Daily Summary")
        print("═══════════════════════════════════════")
        print(f"📥 Input tokens:  {u.prompt_token_count}")
        print(f"📤 Output tokens: {u.candidates_token_count}")
        print(f"📊 Total tokens:  {u.total_token_count}")
        print(f"💰 Est. cost:     ${u.total_token_count * 0.0000004:.6f}")
        print("═══════════════════════════════════════")

        return response.text.strip()
    except Exception as e:
        print(f"⚠️ Daily summary generation failed: {e}")
        return ''
