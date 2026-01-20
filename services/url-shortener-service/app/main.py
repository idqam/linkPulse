from fastapi import FastAPI
from app.api.v1.routes.short_urls import router as short_urls_router
from app.api.redirect import router as redirect_router

app = FastAPI()

app.include_router(short_urls_router, prefix="/api/v1")
app.include_router(redirect_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
