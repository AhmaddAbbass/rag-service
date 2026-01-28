import json
from typing import Any

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential


class OpenAIClient:
    def __init__(self, api_key: str, model: str, embed_model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.embed_model = embed_model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(model=self.embed_model, input=texts)
        return [item.embedding for item in response.data]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def extract_graph(self, text: str) -> dict[str, Any]:
        system = (
            "You extract entities and relations from text. "
            "Return only strict JSON with keys: entities (list), relations (list). "
            "Each entity: {id, name}. Each relation: {source, target, type}."
        )
        user = (
            "Text:\n" + text + "\n\n"
            "Return compact JSON only. Limit to the most salient entities and relations."
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0,
        )
        content = response.choices[0].message.content or "{}"
        return _safe_json_loads(content)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def answer(self, question: str, contexts: list[dict[str, Any]]) -> str:
        context_text = "\n\n".join(
            [
                f"[Context {i+1}]\n{c['text']}"
                for i, c in enumerate(contexts)
            ]
        )
        system = (
            "You answer questions using provided contexts. "
            "If the answer is not contained, say you don't know."
        )
        user = (
            f"Question: {question}\n\n"
            f"Contexts:\n{context_text}\n\n"
            "Answer concisely and cite relevant context numbers in parentheses."
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""


def _safe_json_loads(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(content[start : end + 1])
            except json.JSONDecodeError:
                return {"entities": [], "relations": []}
        return {"entities": [], "relations": []}
