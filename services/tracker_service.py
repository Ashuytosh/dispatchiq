from typing import Optional
import requests
from models.settings import get_setting
from models import vehicle as vehicle_model

TRACCAR_TIMEOUT = 5


def is_traccar_configured() -> bool:
    enabled = get_setting('traccar_enabled') == '1'
    url = get_setting('traccar_url', '') or ''
    username = get_setting('traccar_username', '') or ''
    password = get_setting('traccar_password', '') or ''
    return bool(enabled and url and username and password)


def _login(url: str, username: str, password: str) -> Optional[requests.Session]:
    session = requests.Session()
    try:
        resp = session.post(
            f"{url.rstrip('/')}/api/session",
            data={'email': username, 'password': password},
            timeout=TRACCAR_TIMEOUT,
        )
        if resp.status_code != 200:
            return None
        return session
    except requests.exceptions.RequestException:
        return None


def traccar_login() -> Optional[requests.Session]:
    if not is_traccar_configured():
        return None
    url = get_setting('traccar_url', '') or ''
    username = get_setting('traccar_username', '') or ''
    password = get_setting('traccar_password', '') or ''
    return _login(url, username, password)


def get_all_positions() -> list[dict]:
    if not is_traccar_configured():
        return []
    url = (get_setting('traccar_url', '') or '').rstrip('/')
    session = traccar_login()
    if session is None:
        return []
    try:
        devices_resp = session.get(f"{url}/api/devices", timeout=TRACCAR_TIMEOUT)
        positions_resp = session.get(f"{url}/api/positions", timeout=TRACCAR_TIMEOUT)
        if devices_resp.status_code != 200 or positions_resp.status_code != 200:
            return []
        devices = {d['id']: d for d in devices_resp.json()}
        positions = positions_resp.json()

        result: list[dict] = []
        for pos in positions:
            device = devices.get(pos.get('deviceId'))
            if not device:
                continue
            speed_knots = pos.get('speed') or 0
            result.append({
                'device_name': device.get('name', ''),
                'latitude': pos.get('latitude'),
                'longitude': pos.get('longitude'),
                'speed_kmh': round(speed_knots * 1.852, 1),
                'last_update': pos.get('fixTime') or pos.get('deviceTime'),
            })
        return result
    except requests.exceptions.RequestException:
        return []
    except (ValueError, KeyError):
        return []


def get_vehicle_position(plate_number: str) -> Optional[dict]:
    target = (plate_number or '').strip().upper()
    if not target:
        return None
    for pos in get_all_positions():
        if (pos.get('device_name') or '').strip().upper() == target:
            return pos
    return None


def test_traccar_connection(url: str, username: str, password: str) -> dict:
    if not url or not username or not password:
        return {'success': False, 'error': 'URL, username and password are required.'}
    try:
        session = _login(url, username, password)
        if session is None:
            return {'success': False, 'error': 'Login failed — check URL/credentials.'}
        resp = session.get(f"{url.rstrip('/')}/api/devices", timeout=TRACCAR_TIMEOUT)
        if resp.status_code != 200:
            return {'success': False, 'error': f'Devices request failed ({resp.status_code}).'}
        devices = resp.json()
        device_names = [d.get('name', '') for d in devices]

        vehicles = vehicle_model.get_all_vehicles()
        plate_set = {v['plate_number'].strip().upper() for v in vehicles}
        matched = sorted({
            name for name in device_names
            if name.strip().upper() in plate_set
        })

        return {
            'success': True,
            'devices': len(devices),
            'vehicle_count': len(vehicles),
            'matched_count': len(matched),
            'matched_plates': matched,
        }
    except requests.exceptions.RequestException as e:
        return {'success': False, 'error': f'Connection error: {e}'}
    except ValueError:
        return {'success': False, 'error': 'Traccar returned invalid JSON.'}
