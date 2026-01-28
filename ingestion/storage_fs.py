import os
from pathlib import Path

from config import get_settings

settings = get_settings()


def corpus_dir(corpus_id: str) -> Path:
    return Path(settings.DATA_DIR) / "corpora" / corpus_id


def source_path(corpus_id: str) -> Path:
    return corpus_dir(corpus_id) / "source.txt"


def attempt_dir(corpus_id: str, attempt_id: str) -> Path:
    return corpus_dir(corpus_id) / "attempts" / attempt_id


def attempt_log_path(corpus_id: str, attempt_id: str) -> Path:
    return attempt_dir(corpus_id, attempt_id) / "logs.txt"


def write_source_text(corpus_id: str, text: str) -> Path:
    path = source_path(corpus_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def append_attempt_log(corpus_id: str, attempt_id: str, message: str) -> None:
    path = attempt_log_path(corpus_id, attempt_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(message.rstrip() + os.linesep)


def delete_corpus_folder(corpus_id: str) -> None:
    path = corpus_dir(corpus_id)
    if not path.exists():
        return
    for child in sorted(path.rglob("*"), reverse=True):
        if child.is_file():
            child.unlink()
        elif child.is_dir():
            try:
                child.rmdir()
            except OSError:
                pass
    try:
        path.rmdir()
    except OSError:
        pass
