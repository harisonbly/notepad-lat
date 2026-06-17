from flask import current_app
from flask_mail import Message
from app import mail
from celery import shared_task
from datetime import datetime

@shared_task
def send_async_email(subject, recipients, text_body, html_body):
    msg = Message(subject, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    mail.send(msg)

def send_verification_email(user):
    token = user.generate_verification_token()
    verification_url = f"{current_app.config['APP_URL']}/auth/verify-email/{token}"
    html_body = f"""<html><body><h2>Welcome to Notepad-LAT!</h2><p>Hi {user.username},</p><p>Please verify your email address by clicking the link below:</p><p><a href="{verification_url}">Verify Email</a></p><p>This link will expire in 24 hours.</p></body></html>"""
    send_async_email.delay(subject='Email Verification - Notepad-LAT', recipients=[user.email], text_body=f'Verify your email: {verification_url}', html_body=html_body)

def send_password_reset_email(user):
    token = user.generate_password_reset_token()
    reset_url = f"{current_app.config['APP_URL']}/auth/reset-password/{token}"
    html_body = f"""<html><body><h2>Password Reset - Notepad-LAT</h2><p>Hi {user.username},</p><p>You requested to reset your password. Click the link below:</p><p><a href="{reset_url}">Reset Password</a></p><p>This link will expire in 1 hour.</p></body></html>"""
    send_async_email.delay(subject='Password Reset - Notepad-LAT', recipients=[user.email], text_body=f'Reset your password: {reset_url}', html_body=html_body)

def send_login_alert_email(user, ip_address, user_agent):
    html_body = f"""<html><body><h2>New Login - Notepad-LAT</h2><p>Hi {user.username},</p><p>A new login to your account was detected:</p><ul><li>IP Address: {ip_address}</li><li>Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</li></ul><p>If this wasn't you, please reset your password immediately.</p></body></html>"""
    send_async_email.delay(subject='New Login Alert - Notepad-LAT', recipients=[user.email], text_body='A new login was detected on your account', html_body=html_body)

def send_2fa_enabled_email(user):
    html_body = f"""<html><body><h2>Two-Factor Authentication Enabled - Notepad-LAT</h2><p>Hi {user.username},</p><p>Two-factor authentication has been successfully enabled on your account.</p><p>You will now need to provide a code from your authenticator app when logging in.</p></body></html>"""
    send_async_email.delay(subject='2FA Enabled - Notepad-LAT', recipients=[user.email], text_body='2FA has been enabled on your account', html_body=html_body)
