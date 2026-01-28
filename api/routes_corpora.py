from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.deps import get_current_user
from api.schemas import CorpusCreateRequest, CorpusCreateResponse, CorpusResponse
from config import get_settings
from db.models import Corpus, User
from db.session import SessionLocal, get_db
from ingestion.build_attempt import build_attempt
from ingestion.create_corpus import create_corpus as create_corpus_record
from ingestion.delete_corpus import delete_corpus

router = APIRouter()
settings = get_settings()


def _run_build_attempt(attempt_id: str) -> None:
    db = SessionLocal()
    try:
        build_attempt(db, attempt_id)
    finally:
        db.close()


@router.post("", response_model=CorpusCreateResponse)
def create_corpus(
    request: CorpusCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        corpus_id, attempt_id = create_corpus_record(
            db,
            owner_user_id=current_user.id,
            text=request.text,
            book_name=request.book_name,
            runner_type=settings.DEFAULT_RUNNER,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    background_tasks.add_task(_run_build_attempt, attempt_id)
    return CorpusCreateResponse(corpus_id=corpus_id, attempt_id=attempt_id)


@router.get("", response_model=list[CorpusResponse])
def list_corpora(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    corpora = db.query(Corpus).filter(Corpus.owner_user_id == current_user.id).all()
    return corpora


@router.get("/{corpus_id}", response_model=CorpusResponse)
def get_corpus(
    corpus_id: str,
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
    return corpus


@router.delete("/{corpus_id}")
def delete_corpus_route(
    corpus_id: str,
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

    delete_corpus(db, corpus_id)
    return {"ok": True}
