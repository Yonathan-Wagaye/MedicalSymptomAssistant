from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
import logging

router = APIRouter(tags=["system"])


@router.get("/db-ping")
def db_ping(db: Session = Depends(get_db)):
    db.connection()
    logging.info("Database connection successful")
    return {"db-ping": "success"}
