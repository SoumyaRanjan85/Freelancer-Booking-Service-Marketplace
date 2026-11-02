import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'freelanceconnect-secret-key-2026-prod-demo')
    DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'freelanceconnect.db')
    SCHEMA_PATH = os.path.join(BASE_DIR, 'database', 'schema.sql')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max limit
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif', 'pdf', 'zip'}
