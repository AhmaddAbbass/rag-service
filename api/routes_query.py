from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.deps import get_current_user
from api.schemas import QueryRequest, QueryResponse, RetrieveResponse
from db.models import Attempt, Corpus, User
from db.session import get_db
from runners.registry import get_runner

router = APIRouter()


def _get_ready_attempt(
    db: Session, corpus: Corpus, attempt_id: str | None
) -> Attempt:
    selected_id = attempt_id or corpus.latest_success_attempt_id
    if not selected_id:
        raise HTTPException(status_code=400, detail="No ready attempt available")
    attempt = (
        db.query(Attempt)
        .filter(Attempt.attempt_id == selected_id)
        .filter(Attempt.corpus_id == corpus.corpus_id)
        .first()
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found")
    if attempt.status != "ready":
        raise HTTPException(status_code=400, detail=f"Attempt not ready ({attempt.status})")
    return attempt


@router.post("/{corpus_id}/query", response_model=QueryResponse)
def query_corpus(
    corpus_id: str,
    request: QueryRequest,
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

    attempt = _get_ready_attempt(db, corpus, request.attempt_id)
    runner = get_runner(attempt.runner_type)

    contexts = runner.retrieve(
        corpus_id=corpus.corpus_id,
        attempt_id=attempt.attempt_id,
        question=request.question,
        top_k=request.top_k,
        expand_graph=request.expand_graph,
        config=attempt.config,
    )
    answer = runner.answer(request.question, contexts)

    return QueryResponse(answer=answer, contexts=contexts)


@router.post("/{corpus_id}/retrieve", response_model=RetrieveResponse)
def retrieve_only(
    corpus_id: str,
    request: QueryRequest,
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

    attempt = _get_ready_attempt(db, corpus, request.attempt_id)
    runner = get_runner(attempt.runner_type)

    contexts = runner.retrieve(
        corpus_id=corpus.corpus_id,
        attempt_id=attempt.attempt_id,
        question=request.question,
        top_k=request.top_k,
        expand_graph=request.expand_graph,
        config=attempt.config,
    )

    return RetrieveResponse(contexts=contexts)
