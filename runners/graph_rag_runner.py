import os
from pathlib import Path
from typing import Any, Callable

import numpy as np
from openai import AsyncOpenAI
from nano_graphrag import GraphRAG
from nano_graphrag.base import QueryParam
from nano_graphrag._llm import openai_complete_if_cache
from nano_graphrag._storage import Neo4jStorage
from nano_graphrag._storage.gdb_neo4j import make_path_idable
from nano_graphrag._utils import wrap_embedding_func_with_attrs

from _storage import ChromaVectorStorage, RedisKVStorage
from config import get_settings
from runners.base import BaseRagRunner
from services.openai_client import OpenAIClient

settings = get_settings()


def _attempt_working_dir(corpus_id: str, attempt_id: str) -> Path:
    return Path(settings.DATA_DIR) / "corpora" / corpus_id / "attempts" / attempt_id / "nanographrag"


def _embedding_dim(model: str) -> int:
    model_lower = model.lower()
    if "3-large" in model_lower:
        return 3072
    if "3-small" in model_lower or "ada" in model_lower:
        return 1536
    return 1536


def _make_embedding_func(model: str) -> Callable:
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    dim = _embedding_dim(model)

    @wrap_embedding_func_with_attrs(embedding_dim=dim, max_token_size=8192)
    async def _embed(texts: list[str]) -> np.ndarray:
        response = await client.embeddings.create(
            model=model, input=texts, encoding_format="float"
        )
        return np.array([item.embedding for item in response.data])

    return _embed


def _make_model_func(model: str) -> Callable:
    async def _complete(prompt, system_prompt=None, history_messages=[], **kwargs) -> str:
        return await openai_complete_if_cache(
            model,
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            **kwargs,
        )

    return _complete


class GraphRagRunner(BaseRagRunner):
    def __init__(self) -> None:
        self._last_rag: GraphRAG | None = None
        self._last_param: QueryParam | None = None
        self._last_question: str | None = None
        self._fallback_openai = OpenAIClient(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            embed_model=settings.OPENAI_EMBED_MODEL,
        )

    def _build_rag(self, corpus_id: str, attempt_id: str, config: dict[str, Any]) -> GraphRAG:
        os.environ.setdefault("OPENAI_API_KEY", settings.OPENAI_API_KEY)

        working_dir = _attempt_working_dir(corpus_id, attempt_id)
        working_dir.mkdir(parents=True, exist_ok=True)

        addon_params = {
            "attempt_id": attempt_id,
            "corpus_id": corpus_id,
            "redis_url": settings.REDIS_URL,
            "chroma_host": settings.CHROMA_HOST,
            "chroma_port": settings.CHROMA_PORT,
            "neo4j_url": settings.NEO4J_URI,
            "neo4j_auth": (settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            "chroma_collection_prefix": "col",
        }

        rag = GraphRAG(
            working_dir=str(working_dir),
            enable_local=True,
            enable_naive_rag=True,
            chunk_token_size=int(config.get("chunk_token_size", 1200)),
            chunk_overlap_token_size=int(config.get("chunk_overlap_token_size", 100)),
            embedding_func=_make_embedding_func(settings.OPENAI_EMBED_MODEL),
            best_model_func=_make_model_func(settings.OPENAI_MODEL),
            cheap_model_func=_make_model_func(settings.OPENAI_MODEL),
            key_string_value_json_storage_cls=RedisKVStorage,
            vector_db_storage_cls=ChromaVectorStorage,
            graph_storage_cls=Neo4jStorage,
            addon_params=addon_params,
            tiktoken_model_name=settings.OPENAI_MODEL,
        )
        return rag

    def build_index(
        self,
        corpus_id: str,
        attempt_id: str,
        source_path: str,
        book_name: str | None,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        text = Path(source_path).read_text(encoding="utf-8")
        rag = self._build_rag(corpus_id, attempt_id, config)
        rag.insert(text)

        working_dir = _attempt_working_dir(corpus_id, attempt_id)
        neo4j_namespace = f"{make_path_idable(str(working_dir))}__chunk_entity_relation"
        chroma_collections = [
            f"col__{attempt_id}__entities",
            f"col__{attempt_id}__chunks",
        ]

        return {
            "working_dir": str(working_dir),
            "neo4j_namespace": neo4j_namespace,
            "chroma_collections": chroma_collections,
            "redis_prefix": f"kv:{attempt_id}:",
        }

    def retrieve(
        self,
        corpus_id: str,
        attempt_id: str,
        question: str,
        top_k: int,
        expand_graph: bool,
        config: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        rag = self._build_rag(corpus_id, attempt_id, config or {})
        mode = "local" if expand_graph else "naive"
        param = QueryParam(mode=mode, top_k=top_k, only_need_context=True)
        context = rag.query(question, param)

        self._last_rag = rag
        self._last_param = QueryParam(mode=mode, top_k=top_k)
        self._last_question = question

        if not isinstance(context, str):
            return []
        return [{"text": context, "score": 0.0, "meta": {"mode": mode}}]

    def answer(self, question: str, contexts: list[dict[str, Any]]) -> str:
        if self._last_rag and self._last_param and self._last_question == question:
            try:
                return self._last_rag.query(question, self._last_param)
            except Exception:
                pass
        return self._fallback_openai.answer(question, contexts)
