from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.api import router

app = FastAPI(title="ReadQraft local API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173", "file://"],
    allow_origin_regex=r"^(file://.*|null)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root() -> dict:
    return {"app": "ReadQraft", "message": "Local backend is running on 127.0.0.1 only."}
