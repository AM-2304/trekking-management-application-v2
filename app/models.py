"""Database models: User, Trek, Booking.

Everything here is emitted by db.create_all() - the database is never built by hand.
"""

from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, Index, text

db = SQLAlchemy()


def utcnow():
    """UTC now, naive. (datetime.utcnow() is deprecated from Python 3.12.)"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    """Admins, staff and trekkers all live here, separated by `role`."""

    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    contact_number = db.Column(db.String(20))

    # 'admin' | 'staff' | 'user'  ('user' means a trekker)
    role = db.Column(db.String(10), nullable=False, default="user")

    # Blacklisted accounts cannot log in or book.
    is_blacklisted = db.Column(db.Boolean, nullable=False, default=False)

    # Staff only.
    experience = db.Column(db.String(60))
    specialization = db.Column(db.String(80))

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    # A staff member's assigned treks. The foreign key lives on Trek.
    assigned_treks = db.relationship(
        "Trek", back_populates="staff", foreign_keys="Trek.assigned_staff_id"
    )
    bookings = db.relationship("Booking", back_populates="user")

    __table_args__ = (
        CheckConstraint("role IN ('admin','staff','user')", name="ck_user_role"),
    )

    def to_dict(self):
        """JSON for the frontend. Never includes the password hash."""
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "contact_number": self.contact_number,
            "role": self.role,
            "is_blacklisted": self.is_blacklisted,
            "experience": self.experience,
            "specialization": self.specialization,
            # Display codes shown in the wireframe: U001, TS001, B001.
            "code": {"staff": "TS%03d", "admin": "A%03d"}.get(self.role, "U%03d") % self.id,
        }


class Trek(db.Model):
    """A trek. total_slots is capacity, available_slots is what's left."""

    __tablename__ = "trek"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(120), nullable=False)

    # 'Easy' | 'Moderate' | 'Hard'
    difficulty = db.Column(db.String(10), nullable=False)

    # Stored, not derived - it's a search filter.
    duration_days = db.Column(db.Integer, nullable=False)

    total_slots = db.Column(db.Integer, nullable=False)
    available_slots = db.Column(db.Integer, nullable=False)

    # Bookings are only accepted while status is 'Open'.
    status = db.Column(db.String(12), nullable=False, default="Pending")

    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    image_url = db.Column(db.String(300))

    # Free text sent to trekkers by the daily reminder job.
    instructions = db.Column(db.Text)

    assigned_staff_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    staff = db.relationship(
        "User", back_populates="assigned_treks", foreign_keys=[assigned_staff_id]
    )
    bookings = db.relationship("Booking", back_populates="trek")

    __table_args__ = (
        CheckConstraint(
            "difficulty IN ('Easy','Moderate','Hard')", name="ck_trek_difficulty"
        ),
        CheckConstraint(
            "status IN ('Pending','Approved','Open','Closed','Completed')",
            name="ck_trek_status",
        ),
        # Last line of defence against overbooking.
        CheckConstraint("available_slots >= 0", name="ck_trek_slots_non_negative"),
        CheckConstraint("total_slots > 0", name="ck_trek_total_slots_positive"),
        CheckConstraint("end_date >= start_date", name="ck_trek_dates"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "difficulty": self.difficulty,
            "duration_days": self.duration_days,
            "total_slots": self.total_slots,
            "available_slots": self.available_slots,
            "status": self.status,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "image_url": self.image_url,
            "instructions": self.instructions,
            "assigned_staff_id": self.assigned_staff_id,
            "assigned_staff_name": self.staff.full_name if self.staff else None,
        }


class Booking(db.Model):
    """One trekker's booking of one trek."""

    __tablename__ = "booking"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    trek_id = db.Column(db.Integer, db.ForeignKey("trek.id"), nullable=False)
    booking_date = db.Column(db.DateTime, nullable=False, default=utcnow)

    # 'Booked' | 'Cancelled' | 'Completed'
    status = db.Column(db.String(10), nullable=False, default="Booked")

    user = db.relationship("User", back_populates="bookings")
    trek = db.relationship("Trek", back_populates="bookings")

    __table_args__ = (
        CheckConstraint(
            "status IN ('Booked','Cancelled','Completed')", name="ck_booking_status"
        ),
        # One active booking per user per trek. Cancelled rows are excluded,
        # so cancelling and rebooking still works.
        Index(
            "uq_active_booking",
            "user_id",
            "trek_id",
            unique=True,
            sqlite_where=text("status = 'Booked'"),
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "code": "B%03d" % self.id,
            "user_id": self.user_id,
            "user_name": self.user.full_name if self.user else None,
            "user_email": self.user.email if self.user else None,
            "trek_id": self.trek_id,
            "trek_name": self.trek.name if self.trek else None,
            "location": self.trek.location if self.trek else None,
            "start_date": (
                self.trek.start_date.isoformat() if self.trek and self.trek.start_date else None
            ),
            "end_date": (
                self.trek.end_date.isoformat() if self.trek and self.trek.end_date else None
            ),
            "booking_date": self.booking_date.isoformat() if self.booking_date else None,
            "status": self.status,
        }
