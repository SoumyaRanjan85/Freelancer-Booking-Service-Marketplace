from functools import wraps
from flask import session, redirect, url_for, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db

def hash_password(password: str) -> str:
    """Hash a password using Werkzeug's default PBKDF2/SHA256."""
    return generate_password_hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plain password against its hash."""
    return check_password_hash(password_hash, password)

def login_required(f):
    """Decorator to require user login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(roles):
    """Decorator to require specific role(s) ('client', 'freelancer', 'admin')."""
    if isinstance(roles, str):
        roles = [roles]
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for('login'))
            if session.get('role') not in roles:
                flash("You do not have permission to access that resource.", "danger")
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_current_user():
    """Retrieve the current user from database based on session user_id."""
    if 'user_id' not in session:
        return None
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE user_id = ?", (session['user_id'],)).fetchone()
    db.close()
    return user
