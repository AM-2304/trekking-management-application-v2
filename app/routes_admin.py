"""Admin API. Every route is guarded by @role_required("admin")."""

from datetime import date

from flask import Blueprint, current_app, jsonify, request

from . import cache
from .auth import hash_password, role_required
from .models import Booking, Trek, User, db

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _parse_date(value):
    """'YYYY-MM-DD' -> date, or None."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------

@admin_bp.get("/stats")
@role_required("admin")
def stats():
    """Dashboard counts and recent bookings. Cached briefly."""
    key = cache.make_key("admin:stats")
    cached = cache.get_json(key)
    if cached:
        return jsonify(cached)

    payload = {
        "total_treks": Trek.query.count(),
        "total_users": User.query.filter_by(role="user").count(),
        "total_staff": User.query.filter_by(role="staff").count(),
        "total_bookings": Booking.query.count(),
        "recent_bookings": [
            b.to_dict()
            for b in Booking.query.order_by(Booking.id.desc()).limit(5).all()
        ],
    }
    cache.set_json(key, payload, current_app.config["CACHE_TTL_STATS"])
    return jsonify(payload)


# --------------------------------------------------------------------------
# Treks
# --------------------------------------------------------------------------

@admin_bp.get("/treks")
@role_required("admin")
def list_treks():
    """All treks, searchable and paginated."""
    q = (request.args.get("q") or "").strip()
    page = request.args.get("page", 1, type=int)

    query = Trek.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Trek.name.ilike(like), Trek.location.ilike(like)))

    pagination = query.order_by(Trek.id.desc()).paginate(
        page=page, per_page=current_app.config["PAGE_SIZE"], error_out=False
    )
    return jsonify(
        {
            "items": [t.to_dict() for t in pagination.items],
            "page": pagination.page,
            "pages": pagination.pages,
            "total": pagination.total,
        }
    )


@admin_bp.post("/treks")
@role_required("admin")
def create_trek():
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    location = (data.get("location") or "").strip()
    difficulty = data.get("difficulty")
    start_date = _parse_date(data.get("start_date"))
    end_date = _parse_date(data.get("end_date"))
    total_slots = data.get("total_slots")

    # The frontend validates too, but never trust it.
    if not name or not location:
        return jsonify({"error": "Trek name and location are required"}), 400
    if difficulty not in ("Easy", "Moderate", "Hard"):
        return jsonify({"error": "Difficulty must be Easy, Moderate or Hard"}), 400
    if not start_date or not end_date:
        return jsonify({"error": "Valid start and end dates are required"}), 400
    if end_date < start_date:
        return jsonify({"error": "End date cannot be before the start date"}), 400
    if not isinstance(total_slots, int) or total_slots < 1:
        return jsonify({"error": "Total slots must be a positive whole number"}), 400

    trek = Trek(
        name=name,
        location=location,
        difficulty=difficulty,
        duration_days=(end_date - start_date).days + 1,
        total_slots=total_slots,
        available_slots=total_slots,
        status=data.get("status") or "Pending",
        start_date=start_date,
        end_date=end_date,
        image_url=(data.get("image_url") or "").strip() or None,
        instructions=(data.get("instructions") or "").strip() or None,
        assigned_staff_id=data.get("assigned_staff_id") or None,
    )
    db.session.add(trek)
    db.session.commit()
    cache.invalidate()
    return jsonify(trek.to_dict()), 201


@admin_bp.put("/treks/<int:trek_id>")
@role_required("admin")
def update_trek(trek_id):
    trek = db.session.get(Trek, trek_id)
    if trek is None:
        return jsonify({"error": "Trek not found"}), 404

    data = request.get_json(silent=True) or {}

    if "name" in data and (data.get("name") or "").strip():
        trek.name = data["name"].strip()
    if "location" in data and (data.get("location") or "").strip():
        trek.location = data["location"].strip()
    if data.get("difficulty") in ("Easy", "Moderate", "Hard"):
        trek.difficulty = data["difficulty"]
    if data.get("status") in ("Pending", "Approved", "Open", "Closed", "Completed"):
        trek.status = data["status"]
    if "image_url" in data:
        trek.image_url = (data.get("image_url") or "").strip() or None
    if "instructions" in data:
        trek.instructions = (data.get("instructions") or "").strip() or None
    if "assigned_staff_id" in data:
        trek.assigned_staff_id = data.get("assigned_staff_id") or None

    start_date = _parse_date(data.get("start_date")) or trek.start_date
    end_date = _parse_date(data.get("end_date")) or trek.end_date
    if end_date < start_date:
        return jsonify({"error": "End date cannot be before the start date"}), 400
    trek.start_date, trek.end_date = start_date, end_date
    trek.duration_days = (end_date - start_date).days + 1

    # Moving capacity shifts remaining slots by the same amount.
    new_total = data.get("total_slots")
    if isinstance(new_total, int) and new_total > 0:
        booked = Booking.query.filter_by(trek_id=trek.id, status="Booked").count()
        if new_total < booked:
            return jsonify(
                {"error": f"Cannot reduce capacity below {booked} existing bookings"}
            ), 400
        trek.total_slots = new_total
        trek.available_slots = new_total - booked

    db.session.commit()
    cache.invalidate()
    return jsonify(trek.to_dict())


@admin_bp.delete("/treks/<int:trek_id>")
@role_required("admin")
def delete_trek(trek_id):
    trek = db.session.get(Trek, trek_id)
    if trek is None:
        return jsonify({"error": "Trek not found"}), 404

    # Deleting would break the trekking history we have to keep.
    if Booking.query.filter_by(trek_id=trek.id).count() > 0:
        return jsonify(
            {"error": "This trek has bookings and cannot be deleted. Close it instead."}
        ), 400

    db.session.delete(trek)
    db.session.commit()
    cache.invalidate()
    return jsonify({"message": "Trek deleted"})


@admin_bp.put("/treks/<int:trek_id>/assign")
@role_required("admin")
def assign_staff(trek_id):
    """Assign a staff member to a trek."""
    trek = db.session.get(Trek, trek_id)
    if trek is None:
        return jsonify({"error": "Trek not found"}), 404

    data = request.get_json(silent=True) or {}
    staff_id = data.get("staff_id")

    if staff_id is None:
        trek.assigned_staff_id = None
    else:
        staff = db.session.get(User, staff_id)
        if staff is None or staff.role != "staff":
            return jsonify({"error": "That staff member does not exist"}), 400
        trek.assigned_staff_id = staff.id

    db.session.commit()
    cache.invalidate()
    return jsonify(trek.to_dict())


# --------------------------------------------------------------------------
# Staff accounts
# --------------------------------------------------------------------------

@admin_bp.get("/staff")
@role_required("admin")
def list_staff():
    q = (request.args.get("q") or "").strip()
    query = User.query.filter_by(role="staff")
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(User.full_name.ilike(like), User.email.ilike(like)))
    return jsonify({"items": [u.to_dict() for u in query.order_by(User.id).all()]})


@admin_bp.post("/staff")
@role_required("admin")
def create_staff():
    """Create a staff account. Staff never register themselves."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    full_name = (data.get("full_name") or "").strip()

    if not email or not password or not full_name:
        return jsonify({"error": "Name, email and password are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with that email already exists"}), 409

    staff = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        contact_number=(data.get("contact_number") or "").strip() or None,
        role="staff",
        experience=(data.get("experience") or "").strip() or None,
        specialization=(data.get("specialization") or "").strip() or None,
    )
    db.session.add(staff)
    db.session.commit()
    cache.invalidate()

    from .mailer import send_mail

    send_mail(
        to=staff.email,
        subject="Your TMA trek staff account",
        html=(
            f"<p>Hello {staff.full_name},</p>"
            f"<p>A trek staff account has been created for you.</p>"
            f"<p>Email: <b>{staff.email}</b><br>Password: <b>{password}</b></p>"
            f"<p>Please sign in and change your password.</p>"
        ),
    )
    return jsonify(staff.to_dict()), 201


# --------------------------------------------------------------------------
# Trekkers
# --------------------------------------------------------------------------

@admin_bp.get("/users")
@role_required("admin")
def list_users():
    q = (request.args.get("q") or "").strip()
    query = User.query.filter_by(role="user")
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(User.full_name.ilike(like), User.email.ilike(like)))
    return jsonify({"items": [u.to_dict() for u in query.order_by(User.id).all()]})


@admin_bp.put("/users/<int:user_id>/blacklist")
@role_required("admin")
def toggle_blacklist(user_id):
    """Blacklist or whitelist a trekker or staff member."""
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404
    if user.role == "admin":
        return jsonify({"error": "The administrator cannot be blacklisted"}), 400

    data = request.get_json(silent=True) or {}
    # No value supplied means toggle.
    user.is_blacklisted = bool(data.get("is_blacklisted", not user.is_blacklisted))

    db.session.commit()
    cache.invalidate()
    return jsonify(user.to_dict())


# --------------------------------------------------------------------------
# Bookings
# --------------------------------------------------------------------------

@admin_bp.get("/bookings")
@role_required("admin")
def list_bookings():
    """Every booking ever made."""
    page = request.args.get("page", 1, type=int)
    pagination = Booking.query.order_by(Booking.id.desc()).paginate(
        page=page, per_page=current_app.config["PAGE_SIZE"], error_out=False
    )
    return jsonify(
        {
            "items": [b.to_dict() for b in pagination.items],
            "page": pagination.page,
            "pages": pagination.pages,
            "total": pagination.total,
        }
    )


# --------------------------------------------------------------------------
# Running the scheduled jobs on demand
# --------------------------------------------------------------------------

@admin_bp.post("/jobs/<job_name>")
@role_required("admin")
def run_job(job_name):
    """Run a scheduled job now instead of waiting for Celery beat.

    Executed directly rather than queued, so the result comes back in the response.
    """
    from .tasks import daily_reminders, monthly_activity_report

    jobs = {
        "daily-reminders": daily_reminders,
        "monthly-report": monthly_activity_report,
    }
    task = jobs.get(job_name)
    if task is None:
        return jsonify({"error": "Unknown job"}), 404

    try:
        result = task.run()
    except Exception as exc:
        return jsonify({"error": f"The job failed: {exc}"}), 500

    return jsonify({"job": job_name, "result": result})
