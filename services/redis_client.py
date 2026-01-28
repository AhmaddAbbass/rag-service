import json
from typing import Any

import redis


class RedisClient:
    def __init__(self, url: str) -> None:
        self.client = redis.Redis.from_url(url, decode_responses=True)

    def ping(self) -> bool:
        return self.client.ping()

    def _track_key(self, attempt_id: str, full_key: str) -> None:
        self.client.sadd(f"kv:{attempt_id}:__keys", full_key)

    def set_value(self, attempt_id: str, key: str, value: str) -> None:
        full_key = f"kv:{attempt_id}:{key}"
        self.client.set(full_key, value)
        self._track_key(attempt_id, full_key)

    def set_json(self, attempt_id: str, key: str, value: Any) -> None:
        self.set_value(attempt_id, key, json.dumps(value))

    def get_value(self, attempt_id: str, key: str) -> str | None:
        full_key = f"kv:{attempt_id}:{key}"
        return self.client.get(full_key)

    def get_json(self, attempt_id: str, key: str) -> Any | None:
        raw = self.get_value(attempt_id, key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def delete_attempt_keys(self, attempt_id: str) -> None:
        keyset = f"kv:{attempt_id}:__keys"
        keys = self.client.smembers(keyset)
        if keys:
            self.client.delete(*list(keys))
        self.client.delete(keyset)
