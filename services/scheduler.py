from apscheduler.schedulers.background import BackgroundScheduler

_scheduler: BackgroundScheduler | None = None


def _run_daily_summary() -> None:
    try:
        from models.settings import get_setting
        from services.daily_summary import generate_daily_summary
        from services.whatsapp_service import send_whatsapp
        summary = generate_daily_summary()
        if summary:
            owner_phone = get_setting('whatsapp_owner_phone', '')
            if owner_phone:
                send_whatsapp(owner_phone, summary)
                print(f"📅 Daily summary sent to {owner_phone}")
    except Exception as e:
        print(f"⚠️ Scheduler job failed: {e}")


def start_scheduler(app) -> None:
    global _scheduler
    try:
        from models.settings import get_setting
        if get_setting('whatsapp_enabled') != 'true':
            return
        if not get_setting('gemini_api_key', ''):
            return
        time_str = get_setting('daily_summary_time', '08:00') or '08:00'
        hour, minute = (int(x) for x in time_str.split(':'))
        _scheduler = BackgroundScheduler()
        _scheduler.add_job(_run_daily_summary, 'cron', hour=hour, minute=minute)
        _scheduler.start()
        print(f"📅 Daily summary scheduler started — fires at {time_str}")
    except Exception as e:
        print(f"⚠️ Scheduler failed to start: {e}")
