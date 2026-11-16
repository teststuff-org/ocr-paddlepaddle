"""Moteur OCR (PaddleOCR). Isolé ici : changer de moteur = modifier ce seul fichier."""
import logging
import threading
import time
from functools import lru_cache

import numpy as np
from paddleocr import PaddleOCR

from app.config import OCR_LANG, OCR_MODEL_PROFILE, OCR_USE_MKLDNN

logger = logging.getLogger(__name__)

# PaddleOCR n'est pas thread-safe : uvicorn execute les routes sync dans un pool de threads, deux
# requetes simultanees ecraseraient le meme predictor. Le verrou serialise l'inference.
_ENGINE_LOCK = threading.Lock()

# Mesure sur une page A4 a 200 dpi, CPU sans oneDNN : medium 50 s, mobile 7 s pour le meme texte.
# Medium reste le defaut (plus sur sur les petits caracteres) ; mobile se choisit sciemment.
_MODEL_PROFILES = {
    "medium": {},
    "mobile": {
        "ocr_version": "PP-OCRv5",
        "text_detection_model_name": "PP-OCRv5_mobile_det",
        "text_recognition_model_name": "PP-OCRv5_mobile_rec",
    },
}


def _profile_options() -> dict[str, str]:
    if OCR_MODEL_PROFILE not in _MODEL_PROFILES:
        raise ValueError(
            f"OCR_MODEL_PROFILE={OCR_MODEL_PROFILE!r} inconnu, valeurs possibles : "
            + ", ".join(sorted(_MODEL_PROFILES))
        )
    return _MODEL_PROFILES[OCR_MODEL_PROFILE]


@lru_cache(maxsize=1)
def _get_engine() -> PaddleOCR:
    # Chargé une seule fois (le premier appel télécharge les modèles)
    started = time.perf_counter()
    engine = PaddleOCR(
        lang=OCR_LANG,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        enable_mkldnn=OCR_USE_MKLDNN,
        **_profile_options(),
    )
    # Le premier appel telecharge les modeles : cette duree explique une premiere requete lente.
    logger.info(
        "Moteur OCR charge : profil=%s lang=%s mkldnn=%s duree=%.1fs",
        OCR_MODEL_PROFILE, OCR_LANG, OCR_USE_MKLDNN, time.perf_counter() - started,
    )
    return engine


def ocr_image(image_bgr: np.ndarray) -> list[str]:
    """Retourne les lignes de texte reconnues dans une image (tableau numpy BGR)."""
    started = time.perf_counter()
    with _ENGINE_LOCK:
        results = _get_engine().predict(image_bgr)

    lines: list[str] = []
    for result in results:
        lines.extend(result["rec_texts"])

    logger.debug(
        "Inference OCR : image=%dx%d lignes=%d duree=%.0f ms",
        image_bgr.shape[1], image_bgr.shape[0], len(lines), (time.perf_counter() - started) * 1000,
    )
    return lines
