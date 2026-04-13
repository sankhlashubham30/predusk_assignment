import os
import uuid
from typing import BinaryIO
from app.storage.base import BaseStorage
from app.core.config import settings


class LocalFileStorage(BaseStorage):
    """Local disk storage implementation."""

    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or settings.UPLOAD_DIR
        os.makedirs(self.base_dir, exist_ok=True)

    def save(self, file_obj: BinaryIO, filename: str, subfolder: str = "") -> str:
        ext = os.path.splitext(filename)[1].lower()
        unique_name = f"{uuid.uuid4().hex}{ext}"
        target_dir = os.path.join(self.base_dir, subfolder) if subfolder else self.base_dir
        os.makedirs(target_dir, exist_ok=True)
        file_path = os.path.join(target_dir, unique_name)
        with open(file_path, "wb") as f:
            content = file_obj.read()
            f.write(content)
        return file_path

    def get_path(self, stored_path: str) -> str:
        return stored_path

    def delete(self, stored_path: str) -> bool:
        try:
            if os.path.exists(stored_path):
                os.remove(stored_path)
                return True
            return False
        except OSError:
            return False

    def exists(self, stored_path: str) -> bool:
        return os.path.exists(stored_path)


# Singleton instance used across the app
storage = LocalFileStorage()