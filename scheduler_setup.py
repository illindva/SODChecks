from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from models import db, HealthCheck, CheckResult
import runners
import json

scheduler = BackgroundScheduler()

def run_health_check_job(app, check_id):
    """Job function that executes a single health check."""
    with app.app_context():
        check = HealthCheck.query.get(check_id)
        if not check or not check.is_active:
            return
            
        status, message, metrics = runners.execute_check(check)
        
        # Save result
        result = CheckResult(
            check_id=check.id,
            status=status,
            message=message,
            metrics_json=json.dumps(metrics) if metrics else None
        )
        db.session.add(result)
        db.session.commit()

def sync_scheduler(app):
    """Synchronizes the database check schedules with APScheduler."""
    # Clear existing jobs
    scheduler.remove_all_jobs()
    
    with app.app_context():
        checks = HealthCheck.query.filter_by(is_active=True, is_scheduled=True).all()
        for check in checks:
            job_id = f"check_{check.id}"
            
            trigger = None
            if check.schedule_type == 'hourly':
                trigger = CronTrigger(minute='0')
            elif check.schedule_type == 'daily':
                trigger = CronTrigger(hour='0', minute='0')
            elif check.schedule_type == 'weekly':
                trigger = CronTrigger(day_of_week='sun', hour='0', minute='0')
            elif check.schedule_type == 'custom_cron' and check.cron_expression:
                try:
                    trigger = CronTrigger.from_crontab(check.cron_expression)
                except Exception as e:
                    print(f"Invalid cron expression for check {check.id}: {e}")
                    continue
                    
            if trigger:
                scheduler.add_job(
                    func=run_health_check_job,
                    trigger=trigger,
                    args=[app, check.id],
                    id=job_id,
                    replace_existing=True
                )

def init_scheduler(app):
    """Initializes and starts the scheduler."""
    if not scheduler.running:
        scheduler.start()
    sync_scheduler(app)
