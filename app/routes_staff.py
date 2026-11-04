"""Trek staff API. Every route goes through _own_trek(), so staff can only touch
treks assigned to them."""

from flask import Blueprint, jsonify, request

from . import cache
from .auth import current_user, role_required
from .models import Booking, Trek, db

staff_bp = Blueprint("staff", __name__, url_prefix="/api/staff")


def _own_trek(trek_id):
    """(trek, None) if it belongs to the current staff member, else (None, error)."""
    trek = db.session.get(Trek, trek_id)
    if trek is None:
        return None, (jsonify({"error": "Trek not found"}), 404)
    if trek.assigned_staff_id != current_user().id:
        return None, (jsonify({"error": "You are not assigned to this trek"}), 403)
    return trek, None


@staff_bp.get("/treks")
@role_required("staff")
def my_treks():
    """Assigned treks with participant counts."""
    user = current_user()
    treks = (
        Trek.query.filter_by(assigned_staff_id=user.id).order_by(Trek.start_date).all()
    )

    items = []
    for trek in treks:
        data = trek.to_dict()
        data["participants"] = Booking.query.filter_by(
            trek_id=trek.id, status="Booked"
        ).count()
        items.append(data)

    return jsonify(
        {
            "items": items,
            "assigned_count": len(items),
            "total_participants": sum(i["participants"] for i in items),
            "ongoing_count": sum(1 for i in items if i["status"] == "Open"),
        }
    )


@staff_bp.get("/treks/<int:trek_id>/participants")
@role_required("staff")
def participants(trek_id):
    """Trekkers registered for one of my treks."""
    trek, error = _own_trek(trek_id)
    if error:
        return error

    bookings = (
        Booking.query.filter_by(trek_id=trek.id).order_by(Booking.id).all()
    )
    return jsonify(
        {"trek": trek.to_dict(), "items": [b.to_dict() for b in bookings]}
    )


@staff_bp.put("/treks/<int:trek_id>")
@role_required("staff")
def update_trek(trek_id):
    """Update slots or status. Completing a trek also completes its active bookings."""
    trek, error = _own_trek(trek_id)
    if error:
        return error

    data = request.get_json(silent=True) or {}

    # Staff set what's left, never the capacity.
    if "available_slots" in data:
        slots = data.get("available_slots")
        if not isinstance(slots, int) or slots < 0:
            return jsonify({"error": "Available slots must be zero or more"}), 400
        if slots > trek.total_slots:
            return jsonify(
                {"error": f"Available slots cannot exceed the capacity of {trek.total_slots}"}
            ), 400
        trek.available_slots = slots

    if "status" in data:
        status = data.get("status")
        if status not in ("Open", "Closed", "Completed"):
            return jsonify({"error": "Staff may set the status to Open, Closed or Completed"}), 400

        if status == "Completed" and trek.status != "Completed":
            Booking.query.filter_by(trek_id=trek.id, status="Booked").update(
                {"status": "Completed"}, synchronize_session=False
            )
        trek.status = status

    db.session.commit()
    cache.invalidate()
    return jsonify(trek.to_dict())
