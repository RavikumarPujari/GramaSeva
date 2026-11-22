import io
from typing import Tuple
from PIL import Image, ImageStat
from fastapi import HTTPException, status

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
SUPPORTED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}

def validate_image_bytes(image_bytes: bytes, filename: str = "upload.jpg") -> Tuple[Image.Image, int, int]:
    """
    Validates uploaded image bytes for real decodability, size boundaries, and visual health.
    Returns (PIL Image, width, height) or raises HTTPException.
    """
    size_bytes = len(image_bytes)
    if size_bytes == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image is empty (0 bytes).",
        )

    if size_bytes > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024*1024)}MB.",
        )

    # Magic signature verification
    is_valid_magic = (
        image_bytes.startswith(b"\xff\xd8\xff")  # JPEG
        or image_bytes.startswith(b"\x89PNG\r\n\x1a\n")  # PNG
        or (image_bytes.startswith(b"RIFF") and len(image_bytes) >= 12 and image_bytes[8:12] == b"WEBP")  # WebP
    )
    if not is_valid_magic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image format. Supported formats are JPEG, PNG, and WebP.",
        )

    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()  # Verifies structural integrity
        # Re-open for actual processing (verify closes stream in Pillow)
        img = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Corrupt or unreadable image file.",
        )

    w, h = img.size
    if w < 32 or h < 32:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image dimensions too small ({w}x{h}). Minimum required is 32x32 pixels.",
        )

    return img, w, h

def check_image_lighting_and_quality(img: Image.Image) -> dict:
    """
    Evaluates image lighting conditions and visual clarity (Part 17).
    """
    stat = ImageStat.Stat(img.convert("L"))
    mean_brightness = stat.mean[0]
    std_dev = stat.stddev[0]

    is_dark = mean_brightness < 30.0
    is_washed_out = mean_brightness > 235.0
    is_blurry = std_dev < 15.0

    return {
        "mean_brightness": round(mean_brightness, 1),
        "contrast_stddev": round(std_dev, 1),
        "is_dark": is_dark,
        "is_washed_out": is_washed_out,
        "is_blurry": is_blurry,
        "quality_warning": (
            "Image appears too dark for clear inspection." if is_dark else
            "Image appears washed out / overexposed." if is_washed_out else
            "Image has low contrast or may be blurry." if is_blurry else None
        ),
    }
