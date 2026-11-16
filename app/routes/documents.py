from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile
import pymupdf

from app.exporters import OutputFormat, export
from app.readers import read_pdf

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/ocr")
def ocr_pdf(
    file: UploadFile = File(...),
    output_format: OutputFormat = Query(OutputFormat.json, alias="format"),
    force_ocr: bool = Query(False, description="Forcer l'OCR même si le PDF contient du texte"),
):
    # `def` (et non `async def`) : FastAPI l'exécute dans un thread, l'OCR ne bloque pas le serveur.
    try:
        document = read_pdf(file.file.read(), force_ocr=force_ocr)
    except pymupdf.FileDataError:
        raise HTTPException(status_code=400, detail="Fichier PDF invalide")

    exported = export(document, output_format)
    filename = f"{(file.filename or 'document').rsplit('.', 1)[0]}.{exported.extension}"
    return Response(
        content=exported.content,
        media_type=exported.media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
