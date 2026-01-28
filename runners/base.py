from abc import ABC, abstractmethod
from typing import Any


class BaseRagRunner(ABC):
    @abstractmethod
    def build_index(
        self,
        corpus_id: str,
        attempt_id: str,
        source_path: str,
        book_name: str | None,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def retrieve(
        self,
        corpus_id: str,
        attempt_id: str,
        question: str,
        top_k: int,
        expand_graph: bool,
        config: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def answer(self, question: str, contexts: list[dict[str, Any]]) -> str:
        raise NotImplementedError
