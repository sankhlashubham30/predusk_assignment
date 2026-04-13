from abc import ABC, abstractmethod
from typing import BinaryIO, Optional


class BaseStorage(ABC):
    """Abstract storage interface — swap local for S3/GCS without changing service layer."""

    @abstractmethod
    def save(self, file_obj: BinaryIO, filename: str, subfolder: str = "") -> str:
        """Save a file and return its storage path."""
        ...

    @abstractmethod
    def get_path(self, stored_path: str) -> str:
        """Return the full filesystem/URL path for a stored file."""
        ...

    @abstractmethod
    def delete(self, stored_path: str) -> bool:
        """Delete a file. Returns True if successful."""
        ...

    @abstractmethod
    def exists(self, stored_path: str) -> bool:
        """Check if a file exists in storage."""
        ...