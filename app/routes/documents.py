"""Endpoint d'extraction : recoit un PDF, rend le document dans le format demande."""
import logging
import time

import pymupdf
from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile

from app.exporters import OutputFormat, export
from app.readers import read_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/ocr")
def ocr_pdf(
    file: UploadFile = File(...),
    output_format: OutputFormat = Query(OutputFormat.json, alias="format"),
    force_ocr: bool = Query(False, description="Forcer l'OCR même si le PDF contient du texte"),
):
    # `def` (et non `async def`) : FastAPI l'exécute dans un thread, l'OCR ne bloque pas le serveur.
    filename = file.filename or "document"
    pdf_bytes = file.file.read()
    started = time.perf_counter()
    logger.info(
        "Requete OCR : fichier=%s taille=%d octets format=%s force_ocr=%s",
        filename, len(pdf_bytes), output_format.value, force_ocr,
    )

    try:
        document = read_pdf(pdf_bytes, force_ocr=force_ocr)
        exported = export(document, output_format)
    except pymupdf.FileDataError:
        logger.warning("PDF invalide refuse : fichier=%s taille=%d octets", filename, len(pdf_bytes))
        raise HTTPException(status_code=400, detail="Fichier PDF invalide")
    except Exception:
        # Trace complete cote serveur, message court cote client : sans cela l'appelant ne voit
        # qu'un 500 opaque et n'a aucun moyen de distinguer OCR, rendu ou export.
        logger.exception(
            "Echec du traitement : fichier=%s taille=%d octets force_ocr=%s",
            filename, len(pdf_bytes), force_ocr,
        )
        raise HTTPException(status_code=500, detail="Traitement du PDF impossible")

    output_filename = f"{filename.rsplit('.', 1)[0]}.{exported.extension}"
    logger.info(
        "Requete OCR terminee : fichier=%s pages=%d format=%s sortie=%s taille_sortie=%d octets duree=%.2fs",
        filename, len(document.pages), output_format.value, output_filename,
        len(exported.content), time.perf_counter() - started,
    )

    return Response(
        content=exported.content,
        media_type=exported.media_type,
        headers={"Content-Disposition": f'attachment; filename="{output_filename}"'},
    )
