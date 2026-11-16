"""Lecture d'un PDF, page par page."""
import numpy as np
import pymupdf

from app.config import RENDER_DPI
from app.models import Document, Page
from app.readers.ocr_engine import ocr_image


def read_pdf(pdf_bytes: bytes, force_ocr: bool = False) -> Document:
    """Lit le PDF PAGE PAR PAGE et retourne un Document."""
    document = Document()
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
        for number, page in enumerate(pdf, start=1):
            document.pages.append(read_page(number, page, force_ocr))
    return document


def read_page(number: int, page: pymupdf.Page, force_ocr: bool) -> Page:
    """Lit une page : texte natif si disponible, sinon OCR."""
    if not force_ocr:
        lines = _extract_text_layer(page)
        if lines:
            return Page(number=number, lines=lines, source="text_layer")

    image = _render_page(page)
    return Page(number=number, lines=ocr_image(image), source="ocr")


def _extract_text_layer(page: pymupdf.Page) -> list[str]:
    text = page.get_text().strip()
    return [line for line in text.splitlines() if line.strip()]


def _render_page(page: pymupdf.Page) -> np.ndarray:
    """Convertit la page en image BGR (format attendu par PaddleOCR)."""
    pixmap = page.get_pixmap(dpi=RENDER_DPI, colorspace=pymupdf.csRGB, alpha=False)
    rgb = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, 3)
    return np.ascontiguousarray(rgb[:, :, ::-1])
