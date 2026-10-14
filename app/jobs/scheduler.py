from apscheduler.schedulers.background import BackgroundScheduler

from app.jobs.tasks import ( mark_no_show_appointments,send_appointment_reminders,send_follow_up_reminders )


scheduler = BackgroundScheduler()


def start_scheduler() -> None:
    if scheduler.running:
        return

    scheduler.add_job( send_appointment_reminders, trigger="interval",
                       hours=1, id="appointment_reminders", replace_existing=True, max_instances=1, coalesce=True )
    scheduler.add_job( mark_no_show_appointments,trigger="interval",
                       minutes=15,id="mark_no_shows", replace_existing=True,max_instances=1,coalesce=True )
    scheduler.add_job( send_follow_up_reminders,trigger="cron",hour=8,
                       minute=0,id="follow_up_reminders", replace_existing=True,max_instances=1,coalesce=True )
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)