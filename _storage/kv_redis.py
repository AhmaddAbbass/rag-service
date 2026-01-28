import json
from dataclasses import dataclass
from typing import Any

import redis
from nano_graphrag.base import BaseKVStorage
from nano_graphrag._utils import logger


@dataclass
class RedisKVStorage(BaseKVStorage[Any]):
    def __post_init__(self):
        addon_params = self.global_config.get("addon_params", {})
        self._redis_url = addon_params.get("redis_url")
        self._attempt_id = addon_params.get("attempt_id")
        if not self._redis_url or not self._attempt_id:
            raise ValueError("Missing redis_url or attempt_id in addon_params")
        self._client = redis.Redis.from_url(self._redis_url, decode_responses=True)
        self._prefix = f"kv:{self._attempt_id}:{self.namespace}:"
        self._keys_set = f"kv:{self._attempt_id}:__keys"
        logger.info(f"RedisKVStorage initialized for namespace {self.namespace}")

    def _full_key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    def _strip_prefix(self, full_key: str) -> str:
        if full_key.startswith(self._prefix):
            return full_key[len(self._prefix) :]
        return full_key

    async def all_keys(self) -> list[str]:
        keys = self._client.smembers(self._keys_set)
        return [self._strip_prefix(k) for k in keys if k.startswith(self._prefix)]

    async def get_by_id(self, id: str):
        raw = self._client.get(self._full_key(id))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def get_by_ids(self, ids: list[str], fields: set[str] | None = None):
        if not ids:
            return []
        full_keys = [self._full_key(i) for i in ids]
        raws = self._client.mget(full_keys)
        results: list[Any | None] = []
        for raw in raws:
            if raw is None:
                results.append(None)
                continue
            try:
                item = json.loads(raw)
            except json.JSONDecodeError:
                results.append(None)
                continue
            if fields is None or item is None:
                results.append(item)
            else:
                results.append({k: v for k, v in item.items() if k in fields})
        return results

    async def filter_keys(self, data: list[str]) -> set[str]:
        if not data:
            return set()
        pipe = self._client.pipeline()
        for key in data:
            pipe.exists(self._full_key(key))
        exists_flags = pipe.execute()
        return {key for key, exists in zip(data, exists_flags) if exists == 0}

    async def upsert(self, data: dict[str, Any]):
        if not data:
            return
        pipe = self._client.pipeline()
        for key, value in data.items():
            full_key = self._full_key(key)
            pipe.set(full_key, json.dumps(value))
            pipe.sadd(self._keys_set, full_key)
        pipe.execute()

    async def drop(self):
        keys = self._client.smembers(self._keys_set)
        if not keys:
            return
        namespace_keys = [k for k in keys if k.startswith(self._prefix)]
        if namespace_keys:
            self._client.delete(*namespace_keys)
            self._client.srem(self._keys_set, *namespace_keys)

    async def index_done_callback(self):
        return
