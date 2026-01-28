from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.deps import get_current_user
from api.schemas import AttemptResponse
from db.models import Attempt, Corpus, User
from db.session import get_db

router = APIRouter()


@router.get("/{corpus_id}/attempts/{attempt_id}", response_model=AttemptResponse)
def get_attempt(
    corpus_id: str,
    attempt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    corpus = (
        db.query(Corpus)
        .filter(Corpus.corpus_id == corpus_id)
        .filter(Corpus.owner_user_id == current_user.id)
        .first()
    )
    if corpus is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Corpus not found")

    attempt = (
        db.query(Attempt)
        .filter(Attempt.attempt_id == attempt_id)
        .filter(Attempt.corpus_id == corpus_id)
        .first()
    )
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    return attempt
