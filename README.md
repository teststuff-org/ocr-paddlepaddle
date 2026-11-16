# OCR API

API FastAPI : upload d'un PDF, extraction du texte (couche texte native, sinon OCR PaddleOCR), export en JSON ou Word.

## Lancer
- Linux / macOS : `./run.sh`
- Windows : `.\run.ps1`

Les scripts utilisent [uv](https://docs.astral.sh/uv/) (standard moderne) et se rabattent sur `venv` + `pip` si uv est absent.

Documentation interactive : http://localhost:8000/docs

## Utiliser
```bash
curl -F "file=@mon.pdf" "http://localhost:8000/documents/ocr?format=json"
curl -F "file=@mon.pdf" "http://localhost:8000/documents/ocr?format=docx" -o resultat.docx
```
Paramètres : `format` (`json` | `docx`), `force_ocr` (`true` pour forcer l'OCR même si le PDF contient du texte).
Langue OCR : variable d'environnement `OCR_LANG` (défaut `fr`).
