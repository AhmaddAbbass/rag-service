import uuid

from sqlalchemy.orm import Session

from config import get_settings
from db.models import Attempt, Corpus
from ingestion.storage_fs import write_source_text
from ingestion.validate import compute_sha256, validate_text

settings = get_settings()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def create_corpus(
    db: Session,
    owner_user_id: str | uuid.UUID,
    text: str,
    book_name: str | None,
    runner_type: str = "graph",
) -> tuple[str, str]:
    validate_text(text, settings.MAX_TEXT_CHARS)

    corpus_id = _new_id("c")
    attempt_id = _new_id("a")

    source_path = write_source_text(corpus_id, text)
    source_sha = compute_sha256(text)

    corpus = Corpus(
        corpus_id=corpus_id,
        owner_user_id=owner_user_id,
        book_name=book_name,
        source_path=str(source_path),
        source_sha256=source_sha,
        source_len_chars=len(text),
    )
    attempt = Attempt(
        attempt_id=attempt_id,
        corpus_id=corpus_id,
        runner_type=runner_type,
        status="queued",
        config={
            "chunk_token_size": 1200,
            "chunk_overlap_token_size": 100,
            "top_k": 5,
        },
        artifacts=None,
    )

    db.add(corpus)
    db.add(attempt)
    db.commit()

    return corpus_id, attempt_id
