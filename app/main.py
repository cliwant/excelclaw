"""ExcelClaw WhatsApp Bot — FastAPI application."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.whatsapp.webhook import router as webhook_router
from app.agent.sessions import active_session_count

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.getLogger(__name__).info("ExcelClaw WhatsApp Bot starting up")
    yield
    logging.getLogger(__name__).info("ExcelClaw WhatsApp Bot shutting down")


app = FastAPI(
    title="ExcelClaw WhatsApp Bot",
    description="Turn your Excel into an AI agent via WhatsApp",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(webhook_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "active_sessions": active_session_count(),
    }
