"""The three Celery jobs.

  a. daily_reminders         - 08:00 daily
  b. monthly_activity_report - 1st of the month
  c. export_bookings_csv     - triggered by a user

Celery runs in its own process with no Flask app context, so FlaskTask gives each task
one. All three can also be run on demand from the admin Reports screen.
"""

import csv
import os
from collections import Counter
from datetime import date, datetime, timedelta

from celery import Celery, Task
from celery.schedules import crontab

from .models import Booking, Trek, User, db

celery = Celery(__name__)


def init_celery(app):
    """Point Celery at Redis and give each task an app context."""

    class FlaskTask(Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = FlaskTask
    celery.conf.update(
        broker_url=app.config["CELERY_BROKER_URL"],
        result_backend=app.config["CELERY_RESULT_BACKEND"],
        timezone="Asia/Kolkata",
        beat_schedule={
            "daily-reminders": {
                "task": "app.tasks.daily_reminders",
                "schedule": crontab(hour=8, minute=0),
            },
            "monthly-activity-report": {
                "task": "app.tasks.monthly_activity_report",
                "schedule": crontab(day_of_month=1, hour=9, minute=0),
            },
        },
    )
    return celery


# --------------------------------------------------------------------------
# a. Daily reminders
# --------------------------------------------------------------------------

@celery.task(name="app.tasks.daily_reminders")
def daily_reminders():
    """Remind trekkers whose trek starts within three days."""
    from .mailer import send_mail

    today = date.today()
    window_end = today + timedelta(days=3)

    bookings = (
        Booking.query.join(Trek)
        .filter(
            Booking.status == "Booked",
            Trek.start_date >= today,
            Trek.start_date <= window_end,
        )
        .all()
    )

    for booking in bookings:
        trek = booking.trek
        days_away = (trek.start_date - today).days
        when = "today" if days_away == 0 else f"in {days_away} day(s)"

        send_mail(
            to=booking.user.email,
            subject=f"Reminder: {trek.name} starts {when}",
            html=(
                f"<p>Hello {booking.user.full_name},</p>"
                f"<p>Your trek <b>{trek.name}</b> at {trek.location} starts "
                f"<b>{when}</b>, on {trek.start_date}.</p>"
                f"<p>Difficulty: {trek.difficulty}<br>"
                f"Duration: {trek.duration_days} day(s)<br>"
                f"Ends: {trek.end_date}</p>"
                f"<p><b>Instructions:</b><br>"
                f"{trek.instructions or 'Carry warm clothing, water and your ID.'}</p>"
                f"<p>Happy trekking!</p>"
            ),
        )

    return f"Sent {len(bookings)} reminder(s)"


# --------------------------------------------------------------------------
# b. Monthly activity report
# --------------------------------------------------------------------------

@celery.task(name="app.tasks.monthly_activity_report")
def monthly_activity_report():
    """Email the admin an HTML summary of last month."""
    from .mailer import send_mail

    today = date.today()
    this_month_start = today.replace(day=1)
    last_month_end = this_month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    label = last_month_start.strftime("%B %Y")

    treks_conducted = Trek.query.filter(
        Trek.status == "Completed",
        Trek.end_date >= last_month_start,
        Trek.end_date <= last_month_end,
    ).all()

    bookings = (
        Booking.query.join(Trek)
        .filter(
            Trek.start_date >= last_month_start,
            Trek.start_date <= last_month_end,
            Booking.status.in_(("Booked", "Completed")),
        )
        .all()
    )

    participants = {b.user_id for b in bookings}
    popular = Counter(b.trek.name for b in bookings).most_common(5)

    rows = "".join(
        f"<tr><td>{name}</td><td align='right'>{count}</td></tr>"
        for name, count in popular
    ) or "<tr><td colspan='2'>No bookings in this period.</td></tr>"

    html = (
        f"<h2>Trekking activity report - {label}</h2>"
        f"<ul>"
        f"<li>Treks conducted: <b>{len(treks_conducted)}</b></li>"
        f"<li>Users participated: <b>{len(participants)}</b></li>"
        f"<li>Total bookings: <b>{len(bookings)}</b></li>"
        f"</ul>"
        f"<h3>Most popular treks</h3>"
        f"<table border='1' cellpadding='6' cellspacing='0'>"
        f"<tr><th align='left'>Trek</th><th>Bookings</th></tr>{rows}</table>"
    )

    admin = User.query.filter_by(role="admin").first()
    if admin:
        send_mail(admin.email, f"TMA monthly activity report - {label}", html)

    return f"Report generated for {label}"


# --------------------------------------------------------------------------
# c. CSV export, triggered by the user
# --------------------------------------------------------------------------

@celery.task(name="app.tasks.export_bookings_csv")
def export_bookings_csv(user_id):
    """Write the user's booking history to a CSV and return the filename."""
    from flask import current_app

    user = db.session.get(User, user_id)
    if user is None:
        raise ValueError("User not found")

    bookings = Booking.query.filter_by(user_id=user_id).order_by(Booking.id).all()

    export_dir = current_app.config["EXPORT_DIR"]
    os.makedirs(export_dir, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"bookings_user{user_id}_{stamp}.csv"
    path = os.path.join(export_dir, filename)

    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "User ID",
                "Trek Name",
                "Location",
                "Booking Status",
                "Start Date",
                "End Date",
                "Booking Date",
            ]
        )
        for booking in bookings:
            trek = booking.trek
            writer.writerow(
                [
                    user_id,
                    trek.name,
                    trek.location,
                    booking.status,
                    trek.start_date,
                    trek.end_date,
                    booking.booking_date.strftime("%Y-%m-%d %H:%M"),
                ]
            )

    return filename
