from enum import Enum

from app.exporters.base import ExportedFile
from app.exporters.json_exporter import export_json
from app.exporters.word_exporter import export_word
from app.models import Document


class OutputFormat(str, Enum):
    json = "json"
    docx = "docx"


_EXPORTERS = {
    OutputFormat.json: export_json,
    OutputFormat.docx: export_word,
}


def export(document: Document, output_format: OutputFormat) -> ExportedFile:
    return _EXPORTERS[output_format](document)


__all__ = ["OutputFormat", "ExportedFile", "export"]
