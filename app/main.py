import logging

from fastapi import FastAPI

from app.config import OCR_LANG, OCR_USE_MKLDNN, RENDER_DPI
from app.logging_config import configure_logging
from app.routes import documents, health

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="OCR API")
app.include_router(health.router)
app.include_router(documents.router)

# Trace la configuration réellement appliquée : c'est la première chose à vérifier quand un
# résultat surprend (langue, résolution de rendu, oneDNN désactivé sur CPU Windows).
logger.info(
    "OCR API demarree : lang=%s dpi=%d mkldnn=%s level=%s",
    OCR_LANG,
    RENDER_DPI,
    OCR_USE_MKLDNN,
    logging.getLevelName(logger.getEffectiveLevel()),
)
