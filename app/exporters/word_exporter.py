from io import BytesIO

from docx import Document as WordDocument

from app.exporters.base import ExportedFile
from app.models import Document

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def export_word(document: Document) -> ExportedFile:
    word = WordDocument()
    for index, page in enumerate(document.pages):
        if index > 0:
            word.add_page_break()
        word.add_heading(f"Page {page.number}", level=2)
        for line in page.lines:
            word.add_paragraph(line)

    buffer = BytesIO()
    word.save(buffer)
    return ExportedFile(buffer.getvalue(), DOCX_MEDIA_TYPE, "docx")
