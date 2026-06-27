import json
from google import genai
from models.settings import get_setting
from models.database import get_db, close_db

SYSTEM_PROMPT = """You are a logistics assistant for an Indian transport company.
Parse the user message into trip details.
Respond ONLY in valid JSON. No markdown. No backticks. No explanation.
Format:
{
  "client_name": "company name",
  "from_location": "pickup location",
  "to_location": "delivery location",
  "weight_tons": number,
  "goods_description": "what goods",
  "num_packages": number or null,
  "freight_amount": number or null
}
If you cannot parse, respond: {"error": "Could not understand"}"""


def _print_tokens(label: str, response) -> None:
    u = response.usage_metadata
    total = u.total_token_count
    print("═══════════════════════════════════════")
    print(f"🤖 GEMINI API CALL — {label}")
    print("═══════════════════════════════════════")
    print(f"📥 Input tokens:  {u.prompt_token_count}")
    print(f"📤 Output tokens: {u.candidates_token_count}")
    print(f"📊 Total tokens:  {total}")
    print(f"💰 Est. cost:     ${total * 0.0000004:.6f}")
    print("═══════════════════════════════════════")


def _find_client(name: str) -> dict | None:
    db = get_db()
    try:
        row = db.execute(
            "SELECT id, name FROM clients WHERE LOWER(name) LIKE LOWER(?)",
            (f'%{name}%',),
        ).fetchone()
        return dict(row) if row else None
    finally:
        close_db(db)


def parse_trip_from_text(text: str) -> dict | None:
    api_key = get_setting('gemini_api_key', '')
    if not api_key:
        print("⚠️ Gemini API key not configured")
        return None
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"{SYSTEM_PROMPT}\n\nUser message: {text}",
        )
        _print_tokens("Trip Parsing", response)
        print(f"📝 User message:  {text[:50]}...")

        raw = response.text.strip().strip('`')
        if raw.startswith('json'):
            raw = raw[4:].strip()
        data = json.loads(raw)

        if 'error' in data:
            return {'error': data['error']}

        client = _find_client(data.get('client_name', ''))
        data['client_id'] = client['id'] if client else None
        data['client_match'] = client['name'] if client else None
        return data
    except Exception as e:
        print(f"⚠️ Gemini parse error: {e}")
        return None
