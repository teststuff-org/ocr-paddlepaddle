import os

OCR_LANG = os.getenv("OCR_LANG", "fr")   # fr, en, ch, japan, korean...
RENDER_DPI = int(os.getenv("RENDER_DPI", "200"))  # résolution de rendu des pages avant OCR
