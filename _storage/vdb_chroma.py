import asyncio
from dataclasses import dataclass
from typing import Any

import chromadb
import numpy as np
from nano_graphrag.base import BaseVectorStorage
from nano_graphrag._utils import logger


@dataclass
class ChromaVectorStorage(BaseVectorStorage):
    def __post_init__(self):
        addon_params = self.global_config.get("addon_params", {})
        self._chroma_host = addon_params.get("chroma_host")
        self._chroma_port = addon_params.get("chroma_port")
        self._attempt_id = addon_params.get("attempt_id")
        self._collection_prefix = addon_params.get("chroma_collection_prefix", "col")
        if not self._chroma_host or not self._chroma_port or not self._attempt_id:
            raise ValueError("Missing chroma_host, chroma_port, or attempt_id in addon_params")
        self._client = chromadb.HttpClient(host=self._chroma_host, port=self._chroma_port)
        self._collection_name = f"{self._collection_prefix}__{self._attempt_id}__{self.namespace}"
        try:
            self._collection = self._client.get_collection(self._collection_name)
        except Exception:
            self._collection = self._client.create_collection(self._collection_name)
        self._max_batch_size = int(self.global_config.get("embedding_batch_num", 32))
        logger.info(f"ChromaVectorStorage using collection {self._collection_name}")

    async def upsert(self, data: dict[str, dict]):
        if not data:
            logger.warning("No vectors to upsert")
            return []
        ids = list(data.keys())
        documents = [data[k]["content"] for k in ids]
        metadatas: list[dict[str, Any]] = []
        for k in ids:
            meta = {field: data[k].get(field) for field in self.meta_fields}
            metadatas.append(meta)

        batches = [
            documents[i : i + self._max_batch_size]
            for i in range(0, len(documents), self._max_batch_size)
        ]
        embeddings_list = await asyncio.gather(
            *[self.embedding_func(batch) for batch in batches]
        )
        embeddings = np.concatenate(embeddings_list)
        embeddings = embeddings.tolist()

        self._collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        return ids

    async def query(self, query: str, top_k: int = 5):
        embedding = await self.embedding_func([query])
        if isinstance(embedding, np.ndarray):
            query_vector = embedding[0].tolist()
        else:
            query_vector = embedding[0]
        results = self._collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            include=["metadatas", "distances", "documents", "ids"],
        )
        ids = results.get("ids", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        output: list[dict[str, Any]] = []
        for idx, meta, dist in zip(ids, metas, distances):
            entry = {"id": idx, "distance": float(dist)}
            if meta:
                entry.update(meta)
            output.append(entry)
        return output

    async def index_done_callback(self):
        return
