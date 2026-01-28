from fastapi import FastAPI

from api.routes_auth import router as auth_router
from api.routes_corpora import router as corpora_router
from api.routes_attempts import router as attempts_router
from api.routes_query import router as query_router
from api.routes_health import router as health_router

app = FastAPI(title="rag-service", version="0.1.0")

app.include_router(health_router, tags=["health"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(corpora_router, prefix="/corpora", tags=["corpora"])
app.include_router(attempts_router, prefix="/corpora", tags=["attempts"])
app.include_router(query_router, prefix="/corpora", tags=["query"])
