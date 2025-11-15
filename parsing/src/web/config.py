import os
from pathlib import Path

class Config:
    """Конфигурация приложения"""
    BASE_DIR = Path(__file__).parent.absolute()
    MODELS_DIR = BASE_DIR / "models"


    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24)
    UPLOAD_FOLDER = 'uploads'
    OUTPUT_FOLDER = 'outputs'
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {'docx', 'pdf'}

    # Путь к файлу с полями по умолчанию
    DEFAULT_FIELDS_FILE = 'data/fields.json'

    # для NuExtract
    NUEXTRACT_PATH = MODELS_DIR / "NuExtract-2.0-8B"


config = Config()