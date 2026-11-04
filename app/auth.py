"""Session-based login and role checks.

Flask serves the Vue page, so everything is same-origin: no CORS and no tokens.
The user id is kept in Flask's signed session cookie.
"""

from functools import wraps

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from .models import User, db

auth_bp = Blueprint("auth", __name__, url_prefix="/api")


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def hash_password(raw):
    return generate_password_hash(raw)


def current_user():
    """The logged-in user, or None. Re-read each request so a blacklist bites at once."""
    user_id = session.get("user_id")
    if user_id is None:
        return None
    user = db.session.get(User, user_id)
    if user is None or user.is_blacklisted:
        session.clear()
        return None
    return user


def login_required(view):
    """Reject the request unless somebody is logged in."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            return jsonify({"error": "Authentication required"}), 401
        return view(*args, **kwargs)

    return wrapper


def role_required(*roles):
    """Reject the request unless the logged-in user has one of these roles."""

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = current_user()
            if user is None:
                return jsonify({"error": "Authentication required"}), 401
            if user.role not in roles:
                return jsonify({"error": "You do not have access to this resource"}), 403
            return view(*args, **kwargs)

        return wrapper

    return decorator


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------

@auth_bp.post("/register")
def register():
    """Self-registration, trekkers only."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    full_name = (data.get("full_name") or "").strip()
    contact_number = (data.get("contact_number") or "").strip()

    if not email or not password or not full_name:
        return jsonify({"error": "Name, email and password are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with that email already exists"}), 409

    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        contact_number=contact_number or None,
        role="user",
    )
    db.session.add(user)
    db.session.commit()

    session["user_id"] = user.id
    return jsonify(user.to_dict()), 201


@auth_bp.post("/login")
def login():
    """Log in. The same endpoint serves all three roles."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()

    # Same message either way, so this can't be used to find valid accounts.
    if user is None or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password"}), 401

    if user.is_blacklisted:
        return jsonify({"error": "This account has been blacklisted"}), 403

    # The login screen has a role selector; it must match the real account.
    chosen_role = data.get("role")
    if chosen_role and chosen_role != user.role:
        return jsonify({"error": "Invalid email or password"}), 401

    session["user_id"] = user.id
    return jsonify(user.to_dict())


@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})


@auth_bp.get("/me")
def me():
    """Used by the frontend on page load to restore an existing session."""
    user = current_user()
    if user is None:
        return jsonify({"error": "Not logged in"}), 401
    return jsonify(user.to_dict())


@auth_bp.put("/me")
@login_required
def update_me():
    """Let any logged-in user edit their own profile."""
    user = current_user()
    data = request.get_json(silent=True) or {}

    full_name = (data.get("full_name") or "").strip()
    if full_name:
        user.full_name = full_name

    if "contact_number" in data:
        user.contact_number = (data.get("contact_number") or "").strip() or None

    password = data.get("password")
    if password:
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400
        user.password_hash = hash_password(password)

    db.session.commit()
    return jsonify(user.to_dict())
