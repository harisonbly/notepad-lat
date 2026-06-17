from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, Note, AuditLog
from app.utils.decorators import admin_only
from datetime import datetime, timedelta
import psutil

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@admin_only
def dashboard():
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    verified_users = User.query.filter_by(email_verified=True).count()
    total_notes = Note.query.count()
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_users = User.query.filter(User.created_at > week_ago).count()
    new_notes = Note.query.filter(Note.created_at > week_ago).count()
    logins = AuditLog.query.filter(
        AuditLog.action == 'login',
        AuditLog.status == 'success',
        AuditLog.created_at > week_ago
    ).count()
    stats = {
        'total_users': total_users,
        'active_users': active_users,
        'verified_users': verified_users,
        'total_notes': total_notes,
        'new_users': new_users,
        'new_notes': new_notes,
        'logins': logins
    }
    return render_template('admin/dashboard.html', stats=stats)

@admin_bp.route('/users')
@admin_only
def users():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    users = User.query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page)
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/<int:user_id>/toggle-admin', methods=['POST'])
@admin_only
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()
    return jsonify({'success': True, 'is_admin': user.is_admin})

@admin_bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@admin_only
def toggle_active(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    return jsonify({'success': True, 'is_active': user.is_active})

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_only
def delete_user(user_id):
    if user_id == current_user.id:
        return jsonify({'error': 'Cannot delete yourself'}), 400
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/audit-logs')
@admin_only
def audit_logs():
    page = request.args.get('page', 1, type=int)
    per_page = 100
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=per_page)
    return render_template('admin/audit_logs.html', logs=logs)

@admin_bp.route('/system')
@admin_only
def system():
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    system_info = {
        'cpu_percent': cpu_percent,
        'memory_percent': memory.percent,
        'memory_total': memory.total / (1024**3),
        'disk_percent': disk.percent,
        'disk_total': disk.total / (1024**3)
    }
    return render_template('admin/system.html', system_info=system_info)
