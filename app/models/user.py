from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import jwt

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    email_verified = db.Column(db.Boolean, default=False)
    two_fa_enabled = db.Column(db.Boolean, default=False)
    two_fa_secret = db.Column(db.String(32), nullable=True)
    backup_codes = db.Column(db.JSON, default=list)
    first_name = db.Column(db.String(120))
    last_name = db.Column(db.String(120))
    avatar_url = db.Column(db.String(255))
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    password_changed_at = db.Column(db.DateTime)
    last_ip = db.Column(db.String(45))
    last_user_agent = db.Column(db.String(255))
    notes = db.relationship('Note', backref='author', lazy=True, cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True, cascade='all, delete-orphan')
    sessions = db.relationship('UserSession', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        self.password_changed_at = datetime.utcnow()
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_verification_token(self, expires_in=86400):
        from config import Config
        payload = {'user_id': self.id, 'exp': datetime.utcnow() + timedelta(seconds=expires_in), 'iat': datetime.utcnow(), 'type': 'email_verification'}
        return jwt.encode(payload, Config.SECRET_KEY, algorithm='HS256')
    
    def generate_password_reset_token(self, expires_in=3600):
        from config import Config
        payload = {'user_id': self.id, 'exp': datetime.utcnow() + timedelta(seconds=expires_in), 'iat': datetime.utcnow(), 'type': 'password_reset'}
        return jwt.encode(payload, Config.SECRET_KEY, algorithm='HS256')
    
    @staticmethod
    def verify_token(token, token_type='email_verification'):
        from config import Config
        try:
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            if payload.get('type') != token_type:
                return None
            return payload.get('user_id')
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None
    
    def get_backup_codes(self, count=10):
        codes = [os.urandom(4).hex().upper() for _ in range(count)]
        self.backup_codes = codes
        return codes
    
    def use_backup_code(self, code):
        if code in self.backup_codes:
            self.backup_codes.remove(code)
            return True
        return False
    
    def __repr__(self):
        return f'<User {self.username}>'

class UserSession(db.Model):
    __tablename__ = 'user_sessions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<UserSession {self.user_id}>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
