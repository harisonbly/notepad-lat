from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db, limiter
from app.models import User, AuditLog
from app.utils.email import send_verification_email, send_password_reset_email, send_login_alert_email, send_2fa_enabled_email
from app.utils.auth import generate_jwt_token, generate_totp_secret, get_totp_qr_code, verify_totp
from datetime import datetime
import os

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit('5 per hour')
def register():
    if current_user.is_authenticated:
        return redirect(url_for('notes.dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        if not username or len(username) < 3:
            flash('Username must be at least 3 characters', 'error')
            return redirect(url_for('auth.register'))
        if not email or '@' not in email:
            flash('Please provide a valid email', 'error')
            return redirect(url_for('auth.register'))
        if not password or len(password) < 8:
            flash('Password must be at least 8 characters', 'error')
            return redirect(url_for('auth.register'))
        if password != password_confirm:
            flash('Passwords do not match', 'error')
            return redirect(url_for('auth.register'))
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('auth.register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('auth.register'))
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        send_verification_email(user)
        flash('Registration successful! Please verify your email.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per hour')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('notes.dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            audit_log = AuditLog(user_id=user.id if user else None, action='login', status='failed', ip_address=request.remote_addr, user_agent=request.user_agent.string)
            db.session.add(audit_log)
            db.session.commit()
            flash('Invalid username or password', 'error')
            return redirect(url_for('auth.login'))
        if not user.email_verified:
            flash('Please verify your email first', 'error')
            return redirect(url_for('auth.login'))
        if not user.is_active:
            flash('Your account is disabled', 'error')
            return redirect(url_for('auth.login'))
        if user.two_fa_enabled:
            from flask import session
            session_token = os.urandom(32).hex()
            session['2fa_user_id'] = user.id
            session['2fa_token'] = session_token
            return redirect(url_for('auth.verify_2fa'))
        login_user(user, remember=remember)
        user.last_login = datetime.utcnow()
        user.last_ip = request.remote_addr
        user.last_user_agent = request.user_agent.string
        db.session.commit()
        audit_log = AuditLog(user_id=user.id, action='login', status='success', ip_address=request.remote_addr, user_agent=request.user_agent.string)
        db.session.add(audit_log)
        db.session.commit()
        send_login_alert_email(user, request.remote_addr, request.user_agent.string)
        flash('Login successful!', 'success')
        return redirect(url_for('notes.dashboard'))
    return render_template('auth/login.html')

@auth_bp.route('/verify-2fa', methods=['GET', 'POST'])
def verify_2fa():
    from flask import session
    if '2fa_user_id' not in session:
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        use_backup = request.form.get('use_backup', False)
        user = User.query.get(session['2fa_user_id'])
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('auth.login'))
        verified = False
        if use_backup:
            if user.use_backup_code(code):
                verified = True
                db.session.commit()
        else:
            if verify_totp(user.two_fa_secret, code):
                verified = True
        if verified:
            login_user(user)
            user.last_login = datetime.utcnow()
            user.last_ip = request.remote_addr
            db.session.commit()
            audit_log = AuditLog(user_id=user.id, action='2fa_success', status='success', ip_address=request.remote_addr)
            db.session.add(audit_log)
            db.session.commit()
            session.pop('2fa_user_id')
            session.pop('2fa_token')
            flash('Login successful!', 'success')
            return redirect(url_for('notes.dashboard'))
        else:
            flash('Invalid 2FA code', 'error')
    return render_template('auth/verify_2fa.html')

@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    user_id = User.verify_token(token, 'email_verification')
    if not user_id:
        flash('Invalid or expired verification link', 'error')
        return redirect(url_for('auth.login'))
    user = User.query.get(user_id)
    if user.email_verified:
        flash('Email already verified', 'info')
        return redirect(url_for('auth.login'))
    user.email_verified = True
    user.is_active = True
    db.session.commit()
    flash('Email verified successfully! You can now login.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit('5 per hour')
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('notes.dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        user = User.query.filter_by(email=email).first()
        if user:
            send_password_reset_email(user)
        flash('If the email exists, a password reset link has been sent.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('notes.dashboard'))
    user_id = User.verify_token(token, 'password_reset')
    if not user_id:
        flash('Invalid or expired password reset link', 'error')
        return redirect(url_for('auth.login'))
    user = User.query.get(user_id)
    if request.method == 'POST':
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        if len(password) < 8:
            flash('Password must be at least 8 characters', 'error')
            return redirect(url_for('auth.reset_password', token=token))
        if password != password_confirm:
            flash('Passwords do not match', 'error')
            return redirect(url_for('auth.reset_password', token=token))
        user.set_password(password)
        db.session.commit()
        flash('Password reset successful! You can now login.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html')

@auth_bp.route('/logout')
@login_required
def logout():
    audit_log = AuditLog(user_id=current_user.id, action='logout', status='success', ip_address=request.remote_addr)
    db.session.add(audit_log)
    db.session.commit()
    logout_user()
    flash('Logged out successfully', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/setup-2fa', methods=['GET', 'POST'])
@login_required
def setup_2fa():
    if current_user.two_fa_enabled:
        flash('2FA is already enabled', 'info')
        return redirect(url_for('notes.dashboard'))
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        if not verify_totp(current_user.two_fa_secret, code):
            flash('Invalid 2FA code', 'error')
            return redirect(url_for('auth.setup_2fa'))
        current_user.two_fa_enabled = True
        backup_codes = current_user.get_backup_codes()
        db.session.commit()
        send_2fa_enabled_email(current_user)
        flash('2FA enabled successfully!', 'success')
        return redirect(url_for('auth.view_backup_codes', codes=','.join(backup_codes)))
    secret = generate_totp_secret()
    current_user.two_fa_secret = secret
    db.session.commit()
    qr_code = get_totp_qr_code(current_user, secret)
    return render_template('auth/setup_2fa.html', qr_code=qr_code, secret=secret)

@auth_bp.route('/backup-codes')
@login_required
def view_backup_codes():
    codes = request.args.get('codes', '').split(',')
    return render_template('auth/backup_codes.html', codes=codes)
