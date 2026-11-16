import json

from app.exporters.base import ExportedFile
from app.models import Document


def export_json(document: Document) -> ExportedFile:
    data = {
        "page_count": len(document.pages),
        "pages": [
            {"page": p.number, "source": p.source, "lines": p.lines, "text": "\n".join(p.lines)}
            for p in document.pages
        ],
    }
    content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    return ExportedFile(content, "application/json", "json")
