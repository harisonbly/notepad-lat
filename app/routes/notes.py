from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Note, AuditLog
from app.utils.decorators import audit_action
from app.utils.encryption import encrypt_data, decrypt_data
from datetime import datetime
import uuid

notes_bp = Blueprint('notes', __name__, url_prefix='/notes')

@notes_bp.route('/')
@login_required
def dashboard():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    notes = Note.query.filter_by(user_id=current_user.id, is_archived=False).order_by(
        Note.is_pinned.desc(),
        Note.updated_at.desc()
    ).paginate(page=page, per_page=per_page)
    return render_template('notes/dashboard.html', notes=notes)

@notes_bp.route('/create', methods=['GET', 'POST'])
@login_required
@audit_action('create_note', 'note')
def create_note():
    if request.method == 'POST':
        title = request.form.get('title', 'Untitled').strip()
        content = request.form.get('content', '').strip()
        color = request.form.get('color', '#FFFFFF')
        tags = request.form.get('tags', '').split(',')
        tags = [tag.strip() for tag in tags if tag.strip()]
        encrypted_content = encrypt_data(content, current_user.password_hash)
        note = Note(
            user_id=current_user.id,
            title=title,
            content=encrypted_content,
            color=color,
            tags=tags
        )
        db.session.add(note)
        db.session.commit()
        flash('Note created successfully!', 'success')
        return redirect(url_for('notes.view_note', note_id=note.id))
    return render_template('notes/create.html')

@notes_bp.route('/<int:note_id>')
@login_required
def view_note(note_id):
    note = Note.query.get_or_404(note_id)
    if note.user_id != current_user.id and current_user.id not in note.shared_with:
        flash('You do not have permission to view this note', 'error')
        return redirect(url_for('notes.dashboard'))
    try:
        decrypted_content = decrypt_data(note.content, current_user.password_hash)
    except:
        decrypted_content = ''
    return render_template('notes/view.html', note=note, content=decrypted_content)

@notes_bp.route('/<int:note_id>/edit', methods=['GET', 'POST'])
@login_required
@audit_action('edit_note', 'note')
def edit_note(note_id):
    note = Note.query.get_or_404(note_id)
    if note.user_id != current_user.id:
        flash('You do not have permission to edit this note', 'error')
        return redirect(url_for('notes.dashboard'))
    if request.method == 'POST':
        note.title = request.form.get('title', note.title).strip()
        content = request.form.get('content', '')
        note.color = request.form.get('color', note.color)
        tags = request.form.get('tags', '').split(',')
        note.tags = [tag.strip() for tag in tags if tag.strip()]
        note.content = encrypt_data(content, current_user.password_hash)
        note.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Note updated successfully!', 'success')
        return redirect(url_for('notes.view_note', note_id=note.id))
    try:
        decrypted_content = decrypt_data(note.content, current_user.password_hash)
    except:
        decrypted_content = ''
    return render_template('notes/edit.html', note=note, content=decrypted_content)

@notes_bp.route('/<int:note_id>/delete', methods=['POST'])
@login_required
@audit_action('delete_note', 'note')
def delete_note(note_id):
    note = Note.query.get_or_404(note_id)
    if note.user_id != current_user.id:
        flash('You do not have permission to delete this note', 'error')
        return redirect(url_for('notes.dashboard'))
    db.session.delete(note)
    db.session.commit()
    flash('Note deleted successfully!', 'success')
    return redirect(url_for('notes.dashboard'))

@notes_bp.route('/<int:note_id>/pin', methods=['POST'])
@login_required
def pin_note(note_id):
    note = Note.query.get_or_404(note_id)
    if note.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    note.is_pinned = not note.is_pinned
    db.session.commit()
    return jsonify({'success': True, 'is_pinned': note.is_pinned})

@notes_bp.route('/<int:note_id>/archive', methods=['POST'])
@login_required
def archive_note(note_id):
    note = Note.query.get_or_404(note_id)
    if note.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    note.is_archived = not note.is_archived
    db.session.commit()
    return jsonify({'success': True, 'is_archived': note.is_archived})

@notes_bp.route('/archived')
@login_required
def archived_notes():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    notes = Note.query.filter_by(user_id=current_user.id, is_archived=True).order_by(
        Note.updated_at.desc()
    ).paginate(page=page, per_page=per_page)
    return render_template('notes/archived.html', notes=notes)
