from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class SignupRequest(BaseModel):
    email: str
    password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    created_at: datetime


class CorpusCreateRequest(BaseModel):
    text: str
    book_name: Optional[str] = None


class CorpusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    corpus_id: str
    book_name: Optional[str]
    source_len_chars: int
    created_at: datetime
    latest_success_attempt_id: Optional[str]


class AttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attempt_id: str
    corpus_id: str
    runner_type: str
    status: str
    config: dict[str, Any]
    artifacts: Optional[dict[str, Any]]
    error: Optional[str]
    created_at: datetime
    finished_at: Optional[datetime]


class CorpusCreateResponse(BaseModel):
    corpus_id: str
    attempt_id: str


class ContextItem(BaseModel):
    text: str
    score: float
    meta: dict[str, Any]


class QueryRequest(BaseModel):
    question: str
    attempt_id: Optional[str] = None
    top_k: int = 5
    expand_graph: bool = True


class QueryResponse(BaseModel):
    answer: str
    contexts: list[ContextItem]


class RetrieveResponse(BaseModel):
    contexts: list[ContextItem]
