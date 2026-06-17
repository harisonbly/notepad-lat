from flask import Blueprint, request, jsonify
from app import db
from app.models import User, Note
from app.utils.auth import token_required, generate_jwt_token
from app.utils.encryption import encrypt_data, decrypt_data
from datetime import datetime

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

@api_bp.route('/auth/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401
    if not user.email_verified or not user.is_active:
        return jsonify({'error': 'Account not active'}), 401
    token = generate_jwt_token(user.id)
    return jsonify({
        'token': token,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email
        }
    })

@api_bp.route('/notes', methods=['GET'])
@token_required
def get_notes(user):
    page = request.args.get('page', 1, type=int)
    per_page = 20
    notes = Note.query.filter_by(user_id=user.id, is_archived=False).order_by(
        Note.updated_at.desc()
    ).paginate(page=page, per_page=per_page)
    return jsonify({
        'notes': [note.to_dict() for note in notes.items],
        'total': notes.total,
        'pages': notes.pages
    })

@api_bp.route('/notes/<int:note_id>', methods=['GET'])
@token_required
def get_note(user, note_id):
    note = Note.query.get_or_404(note_id)
    if note.user_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    return jsonify(note.to_dict(include_content=True))

@api_bp.route('/notes', methods=['POST'])
@token_required
def create_note_api(user):
    data = request.get_json()
    title = data.get('title', 'Untitled')
    content = data.get('content', '')
    color = data.get('color', '#FFFFFF')
    tags = data.get('tags', [])
    encrypted_content = encrypt_data(content, user.password_hash)
    note = Note(
        user_id=user.id,
        title=title,
        content=encrypted_content,
        color=color,
        tags=tags
    )
    db.session.add(note)
    db.session.commit()
    return jsonify(note.to_dict()), 201

@api_bp.route('/notes/<int:note_id>', methods=['PUT'])
@token_required
def update_note_api(user, note_id):
    note = Note.query.get_or_404(note_id)
    if note.user_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json()
    note.title = data.get('title', note.title)
    if 'content' in data:
        note.content = encrypt_data(data['content'], user.password_hash)
    note.color = data.get('color', note.color)
    note.tags = data.get('tags', note.tags)
    note.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(note.to_dict())

@api_bp.route('/notes/<int:note_id>', methods=['DELETE'])
@token_required
def delete_note_api(user, note_id):
    note = Note.query.get_or_404(note_id)
    if note.user_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    db.session.delete(note)
    db.session.commit()
    return jsonify({'success': True})
