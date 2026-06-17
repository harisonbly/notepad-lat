from app import db
from datetime import datetime
import hashlib

class Note(db.Model):
    __tablename__ = 'notes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.LargeBinary, nullable=False)
    content_hash = db.Column(db.String(64), nullable=False)
    is_pinned = db.Column(db.Boolean, default=False)
    is_archived = db.Column(db.Boolean, default=False)
    tags = db.Column(db.JSON, default=list)
    color = db.Column(db.String(7), default='#FFFFFF')
    encryption_iv = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    is_shared = db.Column(db.Boolean, default=False)
    shared_with = db.Column(db.JSON, default=list)
    share_token = db.Column(db.String(255), unique=True, nullable=True)
    
    def encrypt_content(self, plaintext, key):
        from cryptography.fernet import Fernet
        cipher_suite = Fernet(key)
        encrypted = cipher_suite.encrypt(plaintext.encode())
        self.content = encrypted
        self.content_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    
    def decrypt_content(self, key):
        from cryptography.fernet import Fernet
        cipher_suite = Fernet(key)
        decrypted = cipher_suite.decrypt(self.content).decode()
        if hashlib.sha256(decrypted.encode()).hexdigest() != self.content_hash:
            raise ValueError('Content integrity check failed')
        return decrypted
    
    def generate_share_token(self):
        import uuid
        self.share_token = str(uuid.uuid4())
        return self.share_token
    
    def add_shared_user(self, user_id):
        if user_id not in self.shared_with:
            self.shared_with.append(user_id)
    
    def remove_shared_user(self, user_id):
        if user_id in self.shared_with:
            self.shared_with.remove(user_id)
    
    def to_dict(self, include_content=False):
        data = {'id': self.id, 'title': self.title, 'tags': self.tags, 'color': self.color, 'is_pinned': self.is_pinned, 'is_archived': self.is_archived, 'is_shared': self.is_shared, 'created_at': self.created_at.isoformat(), 'updated_at': self.updated_at.isoformat()}
        if include_content:
            data['content'] = self.content
        return data
    
    def __repr__(self):
        return f'<Note {self.title}>'

class NoteBackup(db.Model):
    __tablename__ = 'note_backups'
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('notes.id'), nullable=False, index=True)
    content = db.Column(db.LargeBinary, nullable=False)
    content_hash = db.Column(db.String(64), nullable=False)
    version = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<NoteBackup Note:{self.note_id} v{self.version}>'
