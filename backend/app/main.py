"""NagarLens API — FastAPI entry point.  Run: uvicorn app.main:app --reload --port 8000"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.api import planner, receipts, reviews, scorecards, summary
from app.database import init_db
from app.services.data_store import get_store


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    get_store()  # load data + run deterministic audit once at startup
    yield


app = FastAPI(
    title="NagarLens API",
    description="Evidence-to-action accountability for Mumbai road repairs. Find the evidence. Hear both sides. Act on every rupee.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list({config.FRONTEND_ORIGIN, "http://localhost:3000", "http://127.0.0.1:3000"}),
    allow_methods=["*"],
    allow_headers=["*"],
)
for r in (summary.router, reviews.router, scorecards.router, planner.router, receipts.router):
    app.include_router(r, prefix="/api")
