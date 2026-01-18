from fastapi import FastAPI
from app.api.v1.routes.short_urls import router as short_urls_router

app = FastAPI()

app.include_router(short_urls_router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok"}
