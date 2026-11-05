import re
import os
from werkzeug.utils import secure_filename
from config import Config

def is_valid_email(email: str) -> bool:
    """Validate standard email format."""
    if not email or len(email) > 120:
        return False
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(pattern, email.strip()))

def is_valid_password(password: str) -> bool:
    """Password must be at least 6 characters."""
    return bool(password and len(password) >= 6)

def allowed_file(filename: str) -> bool:
    """Check if uploaded file has allowed extension."""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in Config.ALLOWED_EXTENSIONS

def save_uploaded_file(file_obj, subfolder: str = 'profiles') -> str:
    """Save uploaded file securely and return relative web path."""
    if not file_obj or not file_obj.filename:
        return ''
    if not allowed_file(file_obj.filename):
        return ''
    
    filename = secure_filename(file_obj.filename)
    # Add unique prefix to avoid collisions
    import time
    unique_name = f"{int(time.time())}_{filename}"
    folder_path = os.path.join(Config.UPLOAD_FOLDER, subfolder)
    os.makedirs(folder_path, exist_ok=True)
    full_path = os.path.join(folder_path, unique_name)
    file_obj.save(full_path)
    return f"/static/uploads/{subfolder}/{unique_name}"
