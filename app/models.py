from dataclasses import dataclass, field


@dataclass
class Page:
    number: int          # numéro de page, à partir de 1
    lines: list[str]     # lignes de texte lues
    source: str          # "text_layer" (texte natif du PDF) ou "ocr"


@dataclass
class Document:
    pages: list[Page] = field(default_factory=list)
