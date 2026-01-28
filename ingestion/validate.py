import hashlib


def compute_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_text(text: str, max_chars: int) -> None:
    if not text or not text.strip():
        raise ValueError("Text is empty")
    if len(text) > max_chars:
        raise ValueError(f"Text exceeds max length {max_chars}")
