from flask import Blueprint
from app.routes.auth import auth_bp
from app.routes.notes import notes_bp
from app.routes.admin import admin_bp
from app.routes.api import api_bp

__all__ = ['auth_bp', 'notes_bp', 'admin_bp', 'api_bp']
