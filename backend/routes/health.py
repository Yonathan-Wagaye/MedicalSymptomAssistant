from fastapi import APIRouter
import logging

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    logging.info("Health check successful")
    return {"status": "ok"}
