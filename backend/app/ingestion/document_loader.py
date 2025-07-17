# document_loader.py
"""Document loaders for PDFs, DOCX, TXT, and images."""
from __future__ import annotations

import io
from pathlib import Path
from typing import Iterable

from docx import Document as DocxDocument
from pdfminer.high_level import extract_text as pdf_extract_text

from .ocr import ocr_image

def load_pdf(path: Path) -> str:
    """Extract text from a PDF."""
    return pdf_extract_text(path)

def load_docx(path: Path) -> str:
    """Extract text from a DOCX."""
    doc = DocxDocument(path)
    return "\n".join(p.text for p in doc.paragraphs)

def load_txt(path: Path) -> str:
    return Path(path).read_text()

def load_image(path: Path) -> str:
    return ocr_image(path)

LOADERS: dict[str, callable[[Path], str]] = {
    ".pdf": load_pdf,
    ".docx": load_docx,
    ".txt": load_txt,
    ".png": load_image,
    ".jpg": load_image,
    ".jpeg": load_image,
}

def extract_text(path: Path) -> str:
    loader = LOADERS.get(path.suffix.lower())
    if not loader:
        raise ValueError(f"Unsupported file type: {path.suffix}")
    return loader(path)

def batch_extract(paths: Iterable[Path]) -> list[str]:
    return [extract_text(p) for p in paths]
