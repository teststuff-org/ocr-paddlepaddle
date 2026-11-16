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
        total = pdf.page_count
        logger.info(
            "PDF ouvert : pages=%d taille=%d octets force_ocr=%s",
            total, len(pdf_bytes), force_ocr,
        )
        for number, page in enumerate(pdf, start=1):
            document.pages.append(read_page(number, page, force_ocr, total))

    _log_summary(document, started)
    return document


def read_page(number: int, page: pymupdf.Page, force_ocr: bool, total: int) -> Page:
    """Lit une page : texte natif si disponible, sinon OCR."""
    started = time.perf_counter()

    # Debut et fin de page au niveau INFO : une page scannee prend des dizaines de secondes.
    # Sans ces deux reperes, l'appelant ne sait pas si le serveur travaille ou s'il est bloque.
    logger.info("Page %d/%d : debut (force_ocr=%s)", number, total, force_ocr)

    if not force_ocr:
        lines = _extract_text_layer(page)
        if lines:
            _log_page_end(number, total, "text_layer", len(lines), started)
            return Page(number=number, lines=lines, source="text_layer")
        logger.info("Page %d/%d : aucune couche texte, recours a l'OCR", number, total)

    image = _render_page(page)
    logger.info(
        "Page %d/%d : OCR en cours (image %dx%d px, %d dpi)",
        number, total, image.shape[1], image.shape[0], RENDER_DPI,
    )
    lines = ocr_image(image)
    _log_page_end(number, total, "ocr", len(lines), started)

    if not lines:
        logger.warning(
            "Page %d/%d : OCR sans aucun texte reconnu (scan vide, trop clair ou illisible)",
            number, total,
        )

    return Page(number=number, lines=lines, source="ocr")


def _extract_text_layer(page: pymupdf.Page) -> list[str]:
    text = page.get_text().strip()
    return [line for line in text.splitlines() if line.strip()]


def _render_page(page: pymupdf.Page) -> np.ndarray:
    """Convertit la page en image BGR (format attendu par PaddleOCR)."""
    pixmap = page.get_pixmap(dpi=RENDER_DPI, colorspace=pymupdf.csRGB, alpha=False)
    rgb = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, 3)
    return np.ascontiguousarray(rgb[:, :, ::-1])


def _log_page_end(number: int, total: int, source: str, line_count: int, started: float) -> None:
    logger.info(
        "Page %d/%d : fin source=%s lignes=%d duree=%.1fs",
        number, total, source, line_count, time.perf_counter() - started,
    )


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
