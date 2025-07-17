# ocr.py
"""
Lightweight OCR helper using Tesseract.
If Tesseract is not installed, raise a clear error.
"""
from pathlib import Path
import pytesseract
from PIL import Image

def ocr_image(path: Path) -> str:
    try:
        img = Image.open(path)
        return pytesseract.image_to_string(img)
    except (OSError, pytesseract.TesseractNotFoundError) as exc:
        raise RuntimeError(f"OCR failed: {exc}") from exc
