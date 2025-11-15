import os

class Config:
    """Конфигурация приложения"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24)
    UPLOAD_FOLDER = 'uploads'
    OUTPUT_FOLDER = 'outputs'
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {'docx', 'pdf'}
    
    # Путь к файлу с полями по умолчанию
    DEFAULT_FIELDS_FILE = 'data/fields.json'


