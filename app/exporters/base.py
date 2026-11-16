from dataclasses import dataclass


@dataclass
class ExportedFile:
    content: bytes
    media_type: str
    extension: str
