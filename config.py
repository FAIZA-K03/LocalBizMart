import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Load environment variables from .env file
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'localbizmart-dev-secret-key-mca-2026'

    # Database configuration for XAMPP MySQL
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
    DB_PORT = os.environ.get('DB_PORT', '3306')
    DB_NAME = os.environ.get('DB_NAME', 'localbizmart')

    if DB_PASSWORD:
        pwd_part = f":{quote_plus(DB_PASSWORD)}"
    else:
        pwd_part = ""

    # Database configuration
    # Supports direct DATABASE_URL, Render cloud auto-detection, SQLite, or MySQL
    if os.environ.get('DATABASE_URL'):
        db_url = os.environ.get('DATABASE_URL')
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = db_url
    elif os.environ.get('USE_SQLITE', '').lower() in ('true', '1', 't') or os.environ.get('RENDER'):
        default_sqlite_path = os.path.join(basedir, 'localbizmart.db')
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{default_sqlite_path}"
    else:
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{DB_USER}{pwd_part}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True
    }

    # Uploads configuration
    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2 MB max file size

    # Feature flags
    REQUIRE_ADMIN_APPROVAL = os.environ.get('REQUIRE_ADMIN_APPROVAL', 'False').lower() in ('true', '1', 't')
    PAYMENT_TRACKING_ENABLED = os.environ.get('PAYMENT_TRACKING_ENABLED', 'True').lower() in ('true', '1', 't')
