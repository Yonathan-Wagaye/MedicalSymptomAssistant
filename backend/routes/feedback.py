import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.feedback import Feedback
from backend.models.symptom_queries import SymptomQuery
from backend.schemas.feedback import FeedbackCreate, FeedbackResponse

router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse, status_code=201)
def create_feedback(body: FeedbackCreate, db: Session = Depends(get_db)):
    query_row = (
        db.query(SymptomQuery)
        .filter(SymptomQuery.id == body.symptom_query_id)
        .first()
    )
    if not query_row:
        raise HTTPException(status_code=404, detail="Symptom query not found")

    feedback = Feedback(
        symptom_query_id=body.symptom_query_id,
        helpful=body.helpful,
        comment=body.comment,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    logging.info(f"Feedback {feedback.id} created for query {body.symptom_query_id}")
    return feedback
