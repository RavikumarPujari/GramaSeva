import os
import uuid
import hashlib
from io import BytesIO
from typing import Tuple, Optional
from PIL import Image
from fastapi import HTTPException, status
from app.core.config import settings

# Allowed image magic signatures
MAGIC_SIGNATURES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp",  # WebP starts with RIFF....WEBP
}

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

class StorageService:
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = base_path or os.path.abspath(settings.object_storage_local_path)
        self.quarantine_dir = os.path.join(self.base_path, "private", "quarantine")
        self.originals_dir = os.path.join(self.base_path, "private", "originals")
        self.public_dir = os.path.join(self.base_path, "public", "approved")

        for d in [self.quarantine_dir, self.originals_dir, self.public_dir]:
            os.makedirs(d, exist_ok=True)

    def validate_and_inspect_media(self, file_bytes: bytes, filename: str) -> Tuple[str, str, int, str]:
        """
        Validates file size, real magic bytes signature, decodability via Pillow, and returns:
        (detected_mime, file_extension, size_bytes, sha256_hash)
        """
        size_bytes = len(file_bytes)
        if size_bytes == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty (0 bytes)",
            )

        if size_bytes > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024*1024)}MB",
            )

        # 1. Validate magic bytes
        detected_mime = None
        for magic, mime in MAGIC_SIGNATURES.items():
            if file_bytes.startswith(magic):
                if mime == "image/webp":
                    # Extra check for WEBP header
                    if len(file_bytes) >= 12 and file_bytes[8:12] == b"WEBP":
                        detected_mime = mime
                        break
                else:
                    detected_mime = mime
                    break

        if not detected_mime:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file signature. Only JPEG, PNG, and WebP images are permitted.",
            )

        # 2. Validate image decodability and dimensions using Pillow
        try:
            with Image.open(BytesIO(file_bytes)) as img:
                img.verify()  # Verifies file integrity
                width, height = img.size
                if width < 50 or height < 50:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Image resolution too small (minimum 50x50 pixels required)",
                    )
                if width > 8000 or height > 8000:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Image resolution exceeds 8000x8000 pixels limit",
                    )
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Corrupt or non-decodable image file",
            )

        # 3. Calculate SHA-256 checksum
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        # 4. Map extension safely
        ext_map = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
        ext = ext_map.get(detected_mime, ".jpg")

        return detected_mime, ext, size_bytes, file_hash

    def store_private_media(self, file_bytes: bytes, filename: str) -> Tuple[str, str, int, str]:
        """
        Stores validated media in private storage with an opaque UUID filename.
        Returns: (storage_relative_path, mime_type, file_size_bytes, sha256_hash)
        """
        mime_type, ext, size_bytes, file_hash = self.validate_and_inspect_media(file_bytes, filename)
        
        # Opaque filename prevents path traversal
        secure_filename = f"{uuid.uuid4().hex}{ext}"
        target_path = os.path.join(self.originals_dir, secure_filename)

        with open(target_path, "wb") as f:
            f.write(file_bytes)

        rel_path = os.path.join("private", "originals", secure_filename).replace("\\", "/")
        return rel_path, mime_type, size_bytes, file_hash

    def get_absolute_path(self, relative_path: str) -> str:
        # Prevent path traversal attacks
        clean_path = os.path.normpath(relative_path).lstrip("/\\")
        abs_path = os.path.abspath(os.path.join(self.base_path, clean_path))
        if not abs_path.startswith(self.base_path):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Illegal storage path traversal attempt",
            )
        if not os.path.exists(abs_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media file not found on disk",
            )
        return abs_path

storage_service = StorageService()
