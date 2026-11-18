from functools import wraps
from flask import session, redirect, url_for, flash, abort, g, request
from app.models import User

def get_current_user():
    """Returns the currently logged-in user or None."""
    if 'user_id' not in session:
        return None
    if not hasattr(g, 'current_user'):
        from app.extensions import db
        user = db.session.get(User, session['user_id'])
        if user and user.is_active_account:
            g.current_user = user
        else:
            session.clear()
            g.current_user = None
    return g.current_user


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def customer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            flash("Please log in to continue.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        if not user.is_customer:
            flash("Access denied: Customer account required.", "danger")
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def owner_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            flash("Please log in to access business management.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        if not user.is_owner:
            flash("Access denied: Business Owner account required.", "danger")
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            flash("Please log in with administrator credentials.", "warning")
            return redirect(url_for('auth.admin_login', next=request.url))
        if not user.is_admin:
            flash("Access denied: Administrator privileges required.", "danger")
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
