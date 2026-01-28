from datetime import datetime, timezone

from sqlalchemy.orm import Session

from db.models import Attempt, Corpus
from ingestion.locks import attempt_lock
from ingestion.storage_fs import append_attempt_log
from runners.registry import get_runner


def build_attempt(db: Session, attempt_id: str) -> None:
    with attempt_lock(attempt_id):
        attempt = db.query(Attempt).filter(Attempt.attempt_id == attempt_id).first()
        if attempt is None:
            return
        corpus = db.query(Corpus).filter(Corpus.corpus_id == attempt.corpus_id).first()
        if corpus is None:
            return

        attempt.status = "building"
        db.commit()
        append_attempt_log(corpus.corpus_id, attempt_id, "Build started")

        try:
            runner = get_runner(attempt.runner_type)
            artifacts = runner.build_index(
                corpus_id=corpus.corpus_id,
                attempt_id=attempt_id,
                source_path=corpus.source_path,
                book_name=corpus.book_name,
                config=attempt.config,
            )
            attempt.status = "ready"
            attempt.artifacts = artifacts
            attempt.error = None
            attempt.finished_at = datetime.now(timezone.utc)
            corpus.latest_success_attempt_id = attempt_id
            db.commit()
            append_attempt_log(corpus.corpus_id, attempt_id, "Build completed successfully")
        except Exception as exc:  # noqa: BLE001
            attempt.status = "failed"
            attempt.error = str(exc)
            attempt.finished_at = datetime.now(timezone.utc)
            db.commit()
            append_attempt_log(corpus.corpus_id, attempt_id, f"Build failed: {exc}")
