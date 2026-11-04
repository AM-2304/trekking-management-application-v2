"""Trekker (user) API routes: browsing, booking, history and the CSV export."""

from datetime import date

from flask import Blueprint, current_app, jsonify, request, send_file
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from . import cache
from .auth import current_user, login_required, role_required
from .models import Booking, Trek, db

user_bp = Blueprint("user", __name__, url_prefix="/api")


# --------------------------------------------------------------------------
# Browsing treks
# --------------------------------------------------------------------------

@user_bp.get("/treks")
@login_required
def browse_treks():
    """Search and filter open treks. Cached briefly; the key includes every filter."""
    q = (request.args.get("q") or "").strip()
    difficulty = (request.args.get("difficulty") or "").strip()
    location = (request.args.get("location") or "").strip()
    duration = request.args.get("duration", type=int)
    page = request.args.get("page", 1, type=int)

    key = cache.make_key(
        "treks", q=q, difficulty=difficulty, location=location, duration=duration, page=page
    )
    cached = cache.get_json(key)
    if cached:
        return jsonify(cached)

    query = Trek.query.filter(Trek.status == "Open")

    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Trek.name.ilike(like), Trek.location.ilike(like)))
    if difficulty:
        query = query.filter(Trek.difficulty == difficulty)
    if location:
        query = query.filter(Trek.location.ilike(f"%{location}%"))
    if duration:
        query = query.filter(Trek.duration_days <= duration)

    pagination = query.order_by(Trek.start_date).paginate(
        page=page, per_page=current_app.config["PAGE_SIZE"], error_out=False
    )

    payload = {
        "items": [t.to_dict() for t in pagination.items],
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        # Fills the Location dropdown.
        "locations": [
            row[0]
            for row in db.session.query(Trek.location)
            .filter(Trek.status == "Open")
            .distinct()
            .order_by(Trek.location)
            .all()
        ],
    }
    cache.set_json(key, payload, current_app.config["CACHE_TTL_TREKS"])
    return jsonify(payload)


# --------------------------------------------------------------------------
# Booking
# --------------------------------------------------------------------------

@user_bp.post("/bookings")
@role_required("user")
def create_booking():
    """Book a trek.

    Two people clicking "Book Now" at once must not both get the last seat. The guard
    is the conditional UPDATE below: SQLite applies it atomically, so exactly one of
    two racing requests gets rowcount == 1.

    Reading the count, checking it in Python, then writing does NOT work: under WAL a
    read-to-write lock upgrade fails instantly with "database is locked" and
    busy_timeout cannot retry out of it.
    """
    user = current_user()
    data = request.get_json(silent=True) or {}
    trek_id = data.get("trek_id")

    trek = db.session.get(Trek, trek_id) if trek_id else None
    if trek is None:
        return jsonify({"error": "Trek not found"}), 404
    if trek.status != "Open":
        return jsonify({"error": "This trek is not open for booking"}), 400

    # Friendly message for the common case; the unique index is the real guarantee.
    existing = Booking.query.filter_by(
        user_id=user.id, trek_id=trek.id, status="Booked"
    ).first()
    if existing:
        return jsonify({"error": "You have already booked this trek"}), 409

    # Take a seat atomically. No row matched => it filled up or closed just now.
    taken = db.session.execute(
        update(Trek)
        .where(Trek.id == trek.id, Trek.available_slots > 0, Trek.status == "Open")
        .values(available_slots=Trek.available_slots - 1)
    ).rowcount

    if taken == 0:
        db.session.rollback()
        return jsonify({"error": "Sorry, this trek is now full"}), 409

    booking = Booking(user_id=user.id, trek_id=trek.id, status="Booked")
    db.session.add(booking)

    try:
        db.session.commit()
    except IntegrityError:
        # Two identical requests raced; the unique index caught it. Give the seat back.
        db.session.rollback()
        return jsonify({"error": "You have already booked this trek"}), 409

    cache.invalidate()
    return jsonify(booking.to_dict()), 201


@user_bp.put("/bookings/<int:booking_id>/cancel")
@role_required("user")
def cancel_booking(booking_id):
    """Cancel one of my bookings and hand the seat back."""
    user = current_user()
    booking = db.session.get(Booking, booking_id)

    if booking is None or booking.user_id != user.id:
        return jsonify({"error": "Booking not found"}), 404
    if booking.status != "Booked":
        return jsonify({"error": f"This booking is already {booking.status.lower()}"}), 400
    if booking.trek.start_date <= date.today():
        return jsonify({"error": "A trek cannot be cancelled once it has started"}), 400

    booking.status = "Cancelled"

    # Give the seat back, never exceeding capacity.
    db.session.execute(
        update(Trek)
        .where(Trek.id == booking.trek_id, Trek.available_slots < Trek.total_slots)
        .values(available_slots=Trek.available_slots + 1)
    )

    db.session.commit()
    cache.invalidate()
    return jsonify(booking.to_dict())


@user_bp.get("/my/bookings")
@role_required("user")
def my_bookings():
    """Active bookings, plus history (everything completed or cancelled)."""
    user = current_user()
    bookings = (
        Booking.query.filter_by(user_id=user.id).order_by(Booking.id.desc()).all()
    )
    return jsonify(
        {
            "active": [b.to_dict() for b in bookings if b.status == "Booked"],
            "history": [b.to_dict() for b in bookings if b.status != "Booked"],
        }
    )


# --------------------------------------------------------------------------
# CSV export (asynchronous)
# --------------------------------------------------------------------------

@user_bp.post("/export")
@role_required("user")
def start_export():
    """Queue the CSV export and immediately return a task id to poll."""
    from .tasks import export_bookings_csv

    user = current_user()
    task = export_bookings_csv.delay(user.id)
    return jsonify({"task_id": task.id, "status": "queued"}), 202


@user_bp.get("/export/<task_id>")
@role_required("user")
def export_status(task_id):
    """Poll an export; returns the filename once done."""
    from .tasks import celery

    result = celery.AsyncResult(task_id)
    if result.successful():
        return jsonify({"status": "done", "filename": result.result})
    if result.failed():
        return jsonify({"status": "failed", "error": "The export could not be generated"})
    return jsonify({"status": "pending"})


@user_bp.get("/export/download/<path:filename>")
@role_required("user")
def download_export(filename):
    """Serve a finished export file."""
    import os

    # Strip any directory part so a crafted name can't escape the folder.
    safe_name = os.path.basename(filename)
    path = os.path.join(current_app.config["EXPORT_DIR"], safe_name)

    if not os.path.exists(path):
        return jsonify({"error": "That export is no longer available"}), 404

    # Filenames start with the user id, so this blocks other people's exports.
    if not safe_name.startswith(f"bookings_user{current_user().id}_"):
        return jsonify({"error": "That export does not belong to you"}), 403

    return send_file(path, as_attachment=True, download_name=safe_name)
