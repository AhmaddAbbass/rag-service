from fastapi import APIRouter
from sqlalchemy import text

from db.session import SessionLocal
from services.chroma_client import ChromaClient
from services.neo4j_client import Neo4jClient
from services.redis_client import RedisClient
from config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
def health_check():
    status = {"postgres": False, "neo4j": False, "redis": False, "chroma": False}

    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        status["postgres"] = True
    except Exception:
        status["postgres"] = False
    finally:
        try:
            db.close()
        except Exception:
            pass

    try:
        neo = Neo4jClient(settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        status["neo4j"] = neo.ping()
        neo.close()
    except Exception:
        status["neo4j"] = False

    try:
        redis = RedisClient(settings.REDIS_URL)
        status["redis"] = redis.ping()
    except Exception:
        status["redis"] = False

    try:
        chroma = ChromaClient(settings.CHROMA_HOST, settings.CHROMA_PORT)
        status["chroma"] = chroma.heartbeat()
    except Exception:
        status["chroma"] = False

    return {"ok": all(status.values()), "components": status}
