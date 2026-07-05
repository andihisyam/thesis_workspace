from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routers import compile_router, documents, drafts, review

app = FastAPI(title="Thesis Assistant API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(documents.router, prefix="/api")
app.include_router(review.router, prefix="/api")
app.include_router(drafts.router, prefix="/api")
app.include_router(compile_router.router, prefix="/api")


@app.get("/api/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
