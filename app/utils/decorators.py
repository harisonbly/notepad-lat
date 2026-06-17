from functools import wraps
from flask_login import login_required, current_user
from flask import abort, request
from app.models import AuditLog
from app import db
from datetime import datetime

def admin_only(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def audit_action(action, resource_type=None, resource_id=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            result = f(*args, **kwargs)
            if current_user.is_authenticated:
                audit_log = AuditLog(user_id=current_user.id, action=action, resource_type=resource_type, resource_id=resource_id, ip_address=request.remote_addr, user_agent=request.user_agent.string, status='success')
                db.session.add(audit_log)
                db.session.commit()
            return result
        return decorated_function
    return decorator
