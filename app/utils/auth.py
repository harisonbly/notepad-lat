from flask import current_app, request
from functools import wraps
from flask_login import current_user
import jwt
from datetime import datetime, timedelta
import pyotp

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            try:
                token = request.headers['Authorization'].split(' ')[1]
            except IndexError:
                return {'error': 'Invalid token format'}, 401
        if not token:
            return {'error': 'Token is missing'}, 401
        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            from app.models import User
            user = User.query.get(payload['user_id'])
            if not user:
                return {'error': 'User not found'}, 401
        except jwt.ExpiredSignatureError:
            return {'error': 'Token has expired'}, 401
        except jwt.InvalidTokenError:
            return {'error': 'Invalid token'}, 401
        return f(user, *args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return {'error': 'Admin privileges required'}, 403
        return f(*args, **kwargs)
    return decorated

def generate_jwt_token(user_id, expires_in=None):
    if expires_in is None:
        expires_in = current_app.config.get('JWT_EXPIRATION', 86400)
    payload = {'user_id': user_id, 'exp': datetime.utcnow() + timedelta(seconds=expires_in), 'iat': datetime.utcnow()}
    token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
    return token

def verify_totp(secret, code):
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)

def generate_totp_secret():
    return pyotp.random_base32()

def get_totp_qr_code(user, secret):
    import qrcode
    from io import BytesIO
    import base64
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=user.email, issuer_name=current_app.config['TOTP_ISSUER'])
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return f'data:image/png;base64,{img_str}'
