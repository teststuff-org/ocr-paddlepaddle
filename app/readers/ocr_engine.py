"""Moteur OCR (PaddleOCR). Isolé ici : changer de moteur = modifier ce seul fichier."""
from functools import lru_cache

import numpy as np
from paddleocr import PaddleOCR

from app.config import OCR_LANG, OCR_USE_MKLDNN


@lru_cache(maxsize=1)
def _get_engine() -> PaddleOCR:
    # Chargé une seule fois (le premier appel télécharge les modèles)
    return PaddleOCR(
        lang=OCR_LANG,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        enable_mkldnn=OCR_USE_MKLDNN,
    )


def ocr_image(image_bgr: np.ndarray) -> list[str]:
    """Retourne les lignes de texte reconnues dans une image (tableau numpy BGR)."""
    results = _get_engine().predict(image_bgr)
    lines: list[str] = []
    for result in results:
        lines.extend(result["rec_texts"])
    return lines
