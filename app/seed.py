"""Database creation and demo data.

    flask --app run.py init-db   # tables only
    flask --app run.py seed      # tables, the admin, and demo data

The one admin is created here and nowhere else.
"""

from datetime import date, timedelta

import click

from .auth import hash_password
from .models import Booking, Trek, User, db


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Create all tables from the models."""
        db.create_all()
        click.echo("Tables created.")

    @app.cli.command("seed")
    @click.option("--reset", is_flag=True, help="Drop every table first.")
    def seed(reset):
        """Create the tables, the admin, and demo data."""
        if reset:
            db.drop_all()
            click.echo("Dropped all tables.")

        db.create_all()

        # --- The one administrator ---
        admin_email = app.config["ADMIN_EMAIL"]
        admin = User.query.filter_by(role="admin").first()
        if admin is None:
            admin = User(
                email=admin_email,
                password_hash=hash_password(app.config["ADMIN_PASSWORD"]),
                full_name="System Administrator",
                role="admin",
            )
            db.session.add(admin)
            db.session.commit()
            click.echo(f"Admin created: {admin_email} / {app.config['ADMIN_PASSWORD']}")
        else:
            click.echo(f"Admin already exists: {admin.email}")

        # Demo data below; skipped if treks already exist.
        if Trek.query.count() > 0:
            click.echo("Demo data already present - nothing else to do.")
            return

        # --- Trek staff ---
        staff_rows = [
            ("vikram@tma.local", "Vikram Singh", "9876543210", "8 years", "High Altitude"),
            ("neha@tma.local", "Neha Joshi", "9123456780", "5 years", "First Aid"),
            ("arjun@tma.local", "Arjun Mehta", "9988776655", "3 years", "Navigation"),
        ]
        staff = []
        for email, name, phone, experience, specialization in staff_rows:
            member = User(
                email=email,
                password_hash=hash_password("staff123"),
                full_name=name,
                contact_number=phone,
                role="staff",
                experience=experience,
                specialization=specialization,
            )
            db.session.add(member)
            staff.append(member)
        db.session.commit()

        # --- Trekkers ---
        user_rows = [
            ("amit@tma.local", "Amit Sharma", "9876543210"),
            ("priya@tma.local", "Priya Patel", "9123456780"),
            ("rahul@tma.local", "Rahul Verma", "9966776655"),
            ("sneha@tma.local", "Sneha Iyer", "9123898765"),
        ]
        users = []
        for email, name, phone in user_rows:
            trekker = User(
                email=email,
                password_hash=hash_password("user123"),
                full_name=name,
                contact_number=phone,
                role="user",
            )
            db.session.add(trekker)
            users.append(trekker)
        db.session.commit()

        # --- Treks ---
        today = date.today()
        trek_rows = [
            # name, location, difficulty, slots, status, starts in, length, staff, image
            ("Everest Base Camp", "Nepal", "Hard", 10, "Open", 16, 12, 0,
             "https://images.unsplash.com/photo-1551632811-561732d1e306?w=600"),
            ("Roopkund Trek", "Uttarakhand", "Moderate", 15, "Open", 27, 7, 1,
             "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=600"),
            ("Kedarkantha Trek", "Uttarakhand", "Easy", 20, "Closed", 45, 6, 1,
             "https://images.unsplash.com/photo-1519904981063-b0cf448d479e?w=600"),
            ("Hampta Pass", "Himachal", "Moderate", 12, "Open", 38, 5, 2,
             "https://images.unsplash.com/photo-1486911278844-a81c5267e227?w=600"),
            ("Valley of Flowers", "Uttarakhand", "Easy", 18, "Open", 2, 4, 0,
             "https://images.unsplash.com/photo-1470770841072-f978cf4d019e?w=600"),
            ("Kuari Pass", "Uttarakhand", "Moderate", 14, "Completed", -30, 6, 2,
             "https://images.unsplash.com/photo-1454496522488-7a8e488e8606?w=600"),
        ]

        treks = []
        for name, loc, diff, slots, status, offset, length, staff_idx, image in trek_rows:
            start = today + timedelta(days=offset)
            trek = Trek(
                name=name,
                location=loc,
                difficulty=diff,
                duration_days=length,
                total_slots=slots,
                available_slots=slots,
                status=status,
                start_date=start,
                end_date=start + timedelta(days=length - 1),
                image_url=image,
                instructions="Carry warm layers, 2L of water, and a valid photo ID.",
                assigned_staff_id=staff[staff_idx].id,
            )
            db.session.add(trek)
            treks.append(trek)
        db.session.commit()

        # --- Bookings: (trekker index, trek index, status) ---
        booking_rows = [
            (0, 0, "Booked"),
            (0, 4, "Booked"),   # starts in 2 days, so the reminder job has output
            (1, 4, "Booked"),
            (0, 5, "Completed"),
            (1, 1, "Booked"),
            (2, 0, "Booked"),
            (2, 5, "Completed"),
            (3, 3, "Cancelled"),
        ]
        for user_idx, trek_idx, status in booking_rows:
            db.session.add(
                Booking(
                    user_id=users[user_idx].id,
                    trek_id=treks[trek_idx].id,
                    status=status,
                )
            )
            if status == "Booked":
                treks[trek_idx].available_slots -= 1
        db.session.commit()

        click.echo(
            f"Seeded {len(staff)} staff, {len(users)} trekkers, "
            f"{len(treks)} treks, {len(booking_rows)} bookings."
        )
        click.echo("Staff password: staff123   Trekker password: user123")
