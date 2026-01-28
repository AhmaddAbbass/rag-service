# Testing Checklist

## Smoke
- `docker compose up --build`
- `GET /health` -> all components true

## Auth
- signup + login -> token
- missing token -> 401
- /auth/me -> returns user
- logout -> token rejected

## Corpora
- POST /corpora with short text -> returns corpus_id + attempt_id
- GET /corpora -> includes your corpus
- GET /corpora/{corpus_id}/attempts/{attempt_id} -> status transitions

## Query
- POST /corpora/{corpus_id}/query -> returns answer + contexts
- multi-hop question -> contexts from multiple chunks

## Delete
- DELETE /corpora/{corpus_id}
- verify query fails and storage cleaned
