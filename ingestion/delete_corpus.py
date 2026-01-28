from sqlalchemy.orm import Session

from config import get_settings
from db.models import Attempt, Corpus
from ingestion.storage_fs import delete_corpus_folder
from services.chroma_client import ChromaClient
from services.neo4j_client import Neo4jClient
from services.redis_client import RedisClient

settings = get_settings()


def delete_corpus(db: Session, corpus_id: str) -> bool:
    corpus = db.query(Corpus).filter(Corpus.corpus_id == corpus_id).first()
    if corpus is None:
        return False

    attempts = db.query(Attempt).filter(Attempt.corpus_id == corpus_id).all()

    chroma = ChromaClient(settings.CHROMA_HOST, settings.CHROMA_PORT)
    neo4j = Neo4jClient(settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    redis = RedisClient(settings.REDIS_URL)

    for attempt in attempts:
        artifacts = attempt.artifacts or {}
        collections = artifacts.get(
            "chroma_collections",
            [artifacts.get("chroma_collection", f"col__{attempt.attempt_id}")],
        )
        for collection in collections:
            if collection:
                chroma.delete_collection(collection)

        neo4j_namespace = artifacts.get("neo4j_namespace")
        if neo4j_namespace:
            neo4j.delete_namespace(neo4j_namespace)
        else:
            neo4j.delete_attempt(attempt.attempt_id)

        redis.delete_attempt_keys(attempt.attempt_id)
        db.delete(attempt)

    db.delete(corpus)
    db.commit()
    delete_corpus_folder(corpus_id)
    neo4j.close()

    return True
