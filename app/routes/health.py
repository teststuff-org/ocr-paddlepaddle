"""Points d'entrée de service : racine redirigée vers la doc, et sonde de vie."""
from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["health"])


@router.get("/", include_in_schema=False)
def redirect_to_docs() -> RedirectResponse:
    """Évite la 404 quand on ouvre `http://localhost:8000` sans chemin."""
    return RedirectResponse("/docs")


@router.get("/health")
def health() -> dict[str, str]:
    """Sonde de disponibilité : 200 si le processus répond, sans toucher à l'OCR."""
    return {"status": "ok"}
