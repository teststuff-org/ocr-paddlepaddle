from fastapi import FastAPI

from app.routes import documents

app = FastAPI(title="OCR API")
app.include_router(documents.router)
