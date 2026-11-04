"""Tests for the booking rules and access control.

    pytest -v
"""

import os
import sys
import threading
from datetime import date, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from app.auth import hash_password  # noqa: E402
from app.config import Config  # noqa: E402
from app.models import Booking, Trek, User, db  # noqa: E402


class TestConfig(Config):
    TESTING = True
    # A real file, not :memory: - the race test uses threads with separate connections.
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "test_tma.db"
    )
    SECRET_KEY = "testing"


@pytest.fixture
def app():
    path = TestConfig.SQLALCHEMY_DATABASE_URI.replace("sqlite:///", "")
    if os.path.exists(path):
        os.remove(path)

    application = create_app(TestConfig)
    with application.app_context():
        db.create_all()
        _seed()
    yield application

    with application.app_context():
        db.session.remove()
        db.drop_all()
    if os.path.exists(path):
        os.remove(path)


def _seed():
    """One admin, two staff, two trekkers, one open trek with three slots."""
    rows = [
        User(email="admin@t.local", password_hash=hash_password("admin123"),
             full_name="Admin", role="admin"),
        User(email="staff1@t.local", password_hash=hash_password("staff123"),
             full_name="Staff One", role="staff"),
        User(email="staff2@t.local", password_hash=hash_password("staff123"),
             full_name="Staff Two", role="staff"),
        User(email="amit@t.local", password_hash=hash_password("user123"),
             full_name="Amit", role="user"),
        User(email="priya@t.local", password_hash=hash_password("user123"),
             full_name="Priya", role="user"),
    ]
    db.session.add_all(rows)
    db.session.commit()

    start = date.today() + timedelta(days=30)
    db.session.add(
        Trek(name="Test Trek", location="Testland", difficulty="Easy",
             duration_days=3, total_slots=3, available_slots=3, status="Open",
             start_date=start, end_date=start + timedelta(days=2),
             assigned_staff_id=rows[1].id)
    )
    db.session.commit()


def login(client, email, password="user123"):
    return client.post("/api/login", json={"email": email, "password": password})


# --------------------------------------------------------------------------
# Booking rules
# --------------------------------------------------------------------------

def test_booking_decrements_available_slots(app):
    client = app.test_client()
    login(client, "amit@t.local")

    response = client.post("/api/bookings", json={"trek_id": 1})
    assert response.status_code == 201

    with app.app_context():
        assert db.session.get(Trek, 1).available_slots == 2


def test_duplicate_booking_is_rejected(app):
    client = app.test_client()
    login(client, "amit@t.local")

    assert client.post("/api/bookings", json={"trek_id": 1}).status_code == 201
    assert client.post("/api/bookings", json={"trek_id": 1}).status_code == 409

    with app.app_context():
        assert db.session.get(Trek, 1).available_slots == 2


def test_cancelling_returns_the_slot_and_allows_rebooking(app):
    client = app.test_client()
    login(client, "amit@t.local")

    booking_id = client.post("/api/bookings", json={"trek_id": 1}).get_json()["id"]
    assert client.put(f"/api/bookings/{booking_id}/cancel").status_code == 200

    with app.app_context():
        assert db.session.get(Trek, 1).available_slots == 3

    # The unique index only covers active bookings, so this is allowed.
    assert client.post("/api/bookings", json={"trek_id": 1}).status_code == 201


def test_cannot_book_a_trek_that_is_not_open(app):
    with app.app_context():
        db.session.get(Trek, 1).status = "Closed"
        db.session.commit()

    client = app.test_client()
    login(client, "amit@t.local")
    assert client.post("/api/bookings", json={"trek_id": 1}).status_code == 400


def test_concurrent_bookings_never_oversell(app):
    """Twelve threads race for three seats: exactly three must win and the counter
    must land on zero. This is what the conditional UPDATE buys us."""
    with app.app_context():
        for i in range(12):
            db.session.add(
                User(email=f"racer{i}@t.local", password_hash=hash_password("user123"),
                     full_name=f"Racer {i}", role="user")
            )
        db.session.commit()

    statuses = []
    lock = threading.Lock()
    barrier = threading.Barrier(12)

    def attempt(i):
        client = app.test_client()
        login(client, f"racer{i}@t.local")
        barrier.wait()
        code = client.post("/api/bookings", json={"trek_id": 1}).status_code
        with lock:
            statuses.append(code)

    threads = [threading.Thread(target=attempt, args=(i,)) for i in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert statuses.count(201) == 3, f"expected 3 winners, got {statuses}"
    assert all(code in (201, 409) for code in statuses), f"unexpected status: {statuses}"

    with app.app_context():
        assert db.session.get(Trek, 1).available_slots == 0
        assert Booking.query.filter_by(trek_id=1, status="Booked").count() == 3


# --------------------------------------------------------------------------
# Access control
# --------------------------------------------------------------------------

def test_trekker_cannot_reach_admin_endpoints(app):
    client = app.test_client()
    login(client, "amit@t.local")
    assert client.get("/api/admin/stats").status_code == 403


def test_anonymous_requests_are_rejected(app):
    assert app.test_client().get("/api/admin/stats").status_code == 401


def test_staff_cannot_manage_another_staff_members_trek(app):
    client = app.test_client()
    login(client, "staff2@t.local", "staff123")  # trek 1 belongs to staff1
    assert client.put("/api/staff/treks/1", json={"status": "Closed"}).status_code == 403


def test_blacklisted_user_is_rejected_immediately(app):
    """Blacklisting must bite on the next request, not at next login."""
    client = app.test_client()
    login(client, "amit@t.local")
    assert client.get("/api/my/bookings").status_code == 200

    with app.app_context():
        User.query.filter_by(email="amit@t.local").first().is_blacklisted = True
        db.session.commit()

    assert client.get("/api/my/bookings").status_code == 401


def test_completing_a_trek_completes_its_bookings(app):
    client = app.test_client()
    login(client, "amit@t.local")
    client.post("/api/bookings", json={"trek_id": 1})

    staff = app.test_client()
    login(staff, "staff1@t.local", "staff123")
    assert staff.put("/api/staff/treks/1", json={"status": "Completed"}).status_code == 200

    with app.app_context():
        assert Booking.query.filter_by(trek_id=1).first().status == "Completed"
