# API Notes

## Auth
- `POST /auth/signup` `{email, password}`
- `POST /auth/login` `{email, password}` -> `{access_token}`
- Use `Authorization: Bearer <token>` for protected endpoints.

## Corpora lifecycle
- `POST /corpora` `{book_name?, text}` -> `{corpus_id, attempt_id}`
- `GET /corpora`
- `GET /corpora/{corpus_id}`
- `GET /corpora/{corpus_id}/attempts/{attempt_id}`
- `DELETE /corpora/{corpus_id}`

## Query
- `POST /corpora/{corpus_id}/query` `{question, attempt_id?, top_k?, expand_graph?}`
- `POST /corpora/{corpus_id}/retrieve` (debug contexts only)
