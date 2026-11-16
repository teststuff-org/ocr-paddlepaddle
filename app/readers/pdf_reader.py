"""Lecture d'un PDF, page par page."""
import logging
import time

import numpy as np
import pymupdf

from app.config import RENDER_DPI
from app.models import Document, Page
from app.readers.ocr_engine import ocr_image

logger = logging.getLogger(__name__)


def read_pdf(pdf_bytes: bytes, force_ocr: bool = False) -> Document:
    """Lit le PDF PAGE PAR PAGE et retourne un Document."""
    started = time.perf_counter()
    document = Document()
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
        logger.info(
            "PDF ouvert : pages=%d taille=%d octets force_ocr=%s",
            pdf.page_count, len(pdf_bytes), force_ocr,
        )
        for number, page in enumerate(pdf, start=1):
            document.pages.append(read_page(number, page, force_ocr))

    _log_summary(document, started)
    return document


def read_page(number: int, page: pymupdf.Page, force_ocr: bool) -> Page:
    """Lit une page : texte natif si disponible, sinon OCR."""
    started = time.perf_counter()

    if not force_ocr:
        lines = _extract_text_layer(page)
        if lines:
            logger.debug(
                "Page %d : couche texte, %d ligne(s), %.0f ms",
                number, len(lines), _elapsed_ms(started),
            )
            return Page(number=number, lines=lines, source="text_layer")
        logger.info("Page %d : aucune couche texte, recours a l'OCR", number)

    image = _render_page(page)
    lines = ocr_image(image)
    duration_ms = _elapsed_ms(started)
    if not lines:
        logger.warning(
            "Page %d : OCR sans aucun texte reconnu apres %.0f ms (scan vide, trop clair ou illisible)",
            number, duration_ms,
        )
    else:
        # L'OCR coute des dizaines de secondes par page : sa duree merite le niveau INFO,
        # contrairement a la couche texte qui se lit en quelques millisecondes.
        logger.info("Page %d : OCR, %d ligne(s), %.0f ms", number, len(lines), duration_ms)

    return Page(number=number, lines=lines, source="ocr")


def _extract_text_layer(page: pymupdf.Page) -> list[str]:
    text = page.get_text().strip()
    return [line for line in text.splitlines() if line.strip()]


def _render_page(page: pymupdf.Page) -> np.ndarray:
    """Convertit la page en image BGR (format attendu par PaddleOCR)."""
    pixmap = page.get_pixmap(dpi=RENDER_DPI, colorspace=pymupdf.csRGB, alpha=False)
    rgb = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, 3)
    return np.ascontiguousarray(rgb[:, :, ::-1])


def _elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000


def _log_summary(document: Document, started: float) -> None:
    # Le rapport ocr/total est l'indicateur utile : un PDF a couche texte qui part en OCR
    # signale un scan, et beaucoup d'OCR sur un document numerique annonce une extraction de
    # mauvaise qualite (couche texte inutilisable).
    pages = len(document.pages)
    ocr_pages = sum(1 for page in document.pages if page.source == "ocr")
    lines = sum(len(page.lines) for page in document.pages)
    empty_pages = sum(1 for page in document.pages if not page.lines)
    logger.info(
        "Lecture terminee : pages=%d ocr=%d vides=%d lignes=%d duree=%.2fs",
        pages, ocr_pages, empty_pages, lines, time.perf_counter() - started,
    )
