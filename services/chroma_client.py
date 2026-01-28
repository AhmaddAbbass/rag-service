from typing import Any

import chromadb
from chromadb.errors import NotFoundError


class ChromaClient:
    def __init__(self, host: str, port: int) -> None:
        self.client = chromadb.HttpClient(host=host, port=port)

    def heartbeat(self) -> bool:
        return self.client.heartbeat() is not None

    def get_or_create_collection(self, name: str) -> Any:
        try:
            return self.client.get_collection(name)
        except NotFoundError:
            return self.client.create_collection(name)

    def delete_collection(self, name: str) -> None:
        try:
            self.client.delete_collection(name)
        except NotFoundError:
            return
