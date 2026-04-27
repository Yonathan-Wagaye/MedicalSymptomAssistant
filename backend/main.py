import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import config
from backend.core.logging import setup_logging
from backend.routes import api_router

setup_logging()

logging.info(f"Starting application in {config.ENV_STATE} environment")

app = FastAPI(title="Medical Symptom Assistant", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)