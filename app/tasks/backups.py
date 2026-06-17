from app import celery, db
from app.models import User, Note, NoteBackup
from datetime import datetime, timedelta

@celery.task
def backup_user_notes(user_id):
    user = User.query.get(user_id)
    if not user:
        return
    notes = Note.query.filter_by(user_id=user_id).all()
    backup_data = {'user_id': user_id, 'username': user.username, 'timestamp': datetime.utcnow().isoformat(), 'notes': []}
    for note in notes:
        backup_data['notes'].append({'id': note.id, 'title': note.title, 'tags': note.tags, 'created_at': note.created_at.isoformat(), 'updated_at': note.updated_at.isoformat()})
    return {'success': True, 'backed_up': len(notes)}

@celery.task
def backup_all_users():
    users = User.query.all()
    for user in users:
        backup_user_notes.delay(user.id)
    return {'success': True, 'users_backed_up': len(users)}

@celery.task
def cleanup_old_backups(days=30):
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    NoteBackup.query.filter(NoteBackup.created_at < cutoff_date).delete()
    db.session.commit()
    return {'success': True}
