from functools import wraps
from flask import redirect, render_template, session
from datetime import datetime

def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/welcome")
        return f(*args, **kwargs)
    return decorated_function


# Helper function to convert SQLite DATETIME to Python datetime
def convert_to_datetime(sqlite_datetime):
    return datetime.strptime(sqlite_datetime, '%Y-%m-%d %H:%M:%S')