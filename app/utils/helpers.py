import os
import re
import uuid
from datetime import datetime, timezone, timedelta
from flask import current_app
from werkzeug.utils import secure_filename

IST = timezone(timedelta(hours=5, minutes=30))

def get_current_time() -> datetime:
    """
    Returns current local datetime in Indian Standard Time (IST, UTC+5:30)
    as a naive datetime suitable for MySQL DATETIME columns and strftime.
    """
    return datetime.now(IST).replace(tzinfo=None)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload_file(file_storage, prefix: str = 'file') -> str:
    """
    Saves an uploaded file to the static/uploads directory.
    Validates extension and returns the relative path for static serving: 'uploads/<unique_filename>'.
    Raises ValueError if invalid file.
    """
    if not file_storage or not file_storage.filename:
        return None

    filename = secure_filename(file_storage.filename)
    if not allowed_file(filename):
        raise ValueError("Invalid file format. Allowed formats: PNG, JPG, JPEG, WEBP.")

    ext = filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{prefix}_{uuid.uuid4().hex[:12]}.{ext}"

    upload_folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)

    file_path = os.path.join(upload_folder, unique_filename)
    file_storage.save(file_path)

    # Return relative path for url_for('static', filename=...)
    return f"uploads/{unique_filename}"


def validate_phone(phone: str) -> bool:
    """
    Validates phone number (standard 10-digit mobile or with optional country code).
    """
    if not phone:
        return False
    digits = re.sub(r'[\s\-\+\(\)]', '', phone.strip())
    return bool(re.match(r'^[0-9]{10,14}$', digits))


def validate_upi_id(upi_id: str) -> bool:
    """
    Validates UPI ID format (e.g., username@bank, 9876543210@paytm, etc.).
    """
    if not upi_id:
        return False
    pattern = r'^[a-zA-Z0-9.\-_]{2,}@[a-zA-Z0-9]{2,}$'
    return bool(re.match(pattern, upi_id.strip()))
