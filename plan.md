# Definition of Done (we’re “done” when all of this works)

We can say the project is done when:

1. A user can **signup + login** and receives an **access token** (opaque token, not JWT).
2. With that token, the user can create a corpus: `POST /corpora` with `{book_name?, text}` and get back `{corpus_id, attempt_id}`.
3. The service builds GraphRAG artifacts and stores them in:

   * **Postgres** for metadata + ownership + statuses
   * **Neo4j** for the graph (GDB)
   * **Chroma** for embeddings/chunks (VDB)
   * **Redis** for GraphRAG KV (node summaries, mappings, etc.)
4. The user can query: `POST /corpora/{corpus_id}/query` and get:

   * `answer`
   * `contexts` (retrieved evidence with metadata)
   * defaulting to `latest_success_attempt_id` unless attempt specified
5. The user can list and inspect:

   * `GET /corpora`
   * `GET /corpora/{corpus_id}`
   * `GET /corpora/{corpus_id}/attempts/{attempt_id}`
6. The user can delete: `DELETE /corpora/{corpus_id}` and it cleans up **all stores** (Postgres/Neo4j/Chroma/Redis) with no leftovers.
7. Everything runs locally via `docker compose up` and is configured through `.env` **only for infrastructure + OpenAI**.

---

# Repo layout (root folder is `rag-service/`)

Keep `nano_graphrag_repo/` untouched (dependency). Your app lives under `rag-service/`.

```
rag-service/
  app.py
  config.py
  docker-compose.yml
  Dockerfile
  .env.example
  README.md

  api/
    schemas.py
    deps.py                 # auth dependency, db session dependency
    routes_auth.py
    routes_corpora.py
    routes_attempts.py
    routes_query.py
    routes_health.py

  db/
    models.py
    migrations/             # alembic
    session.py

  ingestion/
    create_corpus.py
    build_attempt.py
    delete_corpus.py
    storage_fs.py           # stores raw text locally
    validate.py
    locks.py

  runners/
    base.py
    graph_rag_runner.py
    registry.py

  services/
    openai_client.py
    neo4j_client.py
    chroma_client.py
    redis_client.py

  data/
    corpora/
      <corpus_id>/
        source.txt
        meta.json            # optional if you want, but Postgres is primary truth
        attempts/
          <attempt_id>/
            logs.txt         # per attempt logs
```

**Rule:** Postgres is the *source of truth*. The filesystem (`data/`) holds raw text + optional logs.

---

# `.env` contract (NO auth/jwt secrets here)

`.env` will include infra endpoints + OpenAI key only:

**OpenAI**

* `OPENAI_API_KEY=...`
* `OPENAI_MODEL=...`
* `OPENAI_EMBED_MODEL=...` (if you want separate embeddings model)

**Postgres**

* `POSTGRES_HOST=postgres`
* `POSTGRES_PORT=5432`
* `POSTGRES_DB=rag`
* `POSTGRES_USER=rag`
* `POSTGRES_PASSWORD=rag`
* `DATABASE_URL=postgresql+psycopg://rag:rag@postgres:5432/rag` (or constructed)

**Neo4j**

* `NEO4J_URI=bolt://neo4j:7687`
* `NEO4J_USER=neo4j`
* `NEO4J_PASSWORD=...`

**Chroma**

* `CHROMA_HOST=chroma`
* `CHROMA_PORT=8000`

**Redis**

* `REDIS_URL=redis://redis:6379/0`

**App**

* `DATA_DIR=/app/data`
* `MAX_TEXT_CHARS=2000000`
* `DEFAULT_RUNNER=graph`

---

# Database organization (super important, do this exactly)

## Postgres (ownership + lifecycle)

Tables (minimal but complete):

### `users`

* `id` (uuid recommended)
* `email` (unique)
* `password_hash` (bcrypt/argon2)
* `created_at`

### `sessions`  ✅ replaces JWT

* `id` (uuid)
* `user_id` (FK → users.id)
* `token_hash` (sha256 of the token, never store raw token)
* `created_at`
* `expires_at`
* `revoked_at` (nullable)

**How auth works**

* Signup → store user with hashed password.
* Login → generate random token (e.g., 32 bytes), store **hash(token)** in sessions, return token to client.
* Requests include: `Authorization: Bearer <token>`
* Server hashes provided token and checks `sessions.token_hash` exists and not expired/revoked.

This avoids any “JWT secret” in env and is production-safe for MVP.

### `corpora`

* `corpus_id` (string or uuid; string ok if you like `c_...`)
* `owner_user_id` (FK → users.id)
* `book_name` nullable
* `source_path` (points to `data/corpora/<corpus_id>/source.txt`)
* `source_sha256`
* `source_len_chars`
* `created_at`
* `latest_success_attempt_id` nullable

### `attempts`

* `attempt_id` (string primary key)
* `corpus_id` (FK → corpora.corpus_id)
* `runner_type` (`graph` only for now)
* `status` (`queued|building|ready|failed`)
* `config` (jsonb)
* `artifacts` (jsonb) — pointers for cleanup and loading
* `error` nullable
* `created_at`
* `finished_at` nullable

> Attempts are not “jobs”; they’re just versioned build runs with status.

---

## Chroma (VDB)

**Use one collection per attempt** to make cleanup trivial:

* collection name: `col__{attempt_id}`

Each embedding record metadata includes:

* `corpus_id`, `attempt_id`, `chunk_id`, `book_name`, maybe `offset_start/end`

Delete = delete the collection.

---

## Neo4j (GDB)

**Single Neo4j DB** (community friendly). Isolation by properties:

* Every node and relationship has:

  * `corpus_id`
  * `attempt_id`

Create indexes:

* index on `attempt_id`
* index on `corpus_id` (optional but recommended)

Deletion:

```cypher
MATCH (n {attempt_id: $attempt_id})
DETACH DELETE n
```

---

## Redis (KV required by GraphRAG)

Redis is part of the GraphRAG pipeline, not “cache”.

**Namespace keys by attempt_id**:

Prefix:

* `kv:{attempt_id}:...`

Recommended KV layout (minimum viable):

* `kv:{attempt_id}:chunk:{chunk_id}` → raw chunk text (or pointer)
* `kv:{attempt_id}:node_summary:{node_id}` → summary text
* `kv:{attempt_id}:node_chunks:{node_id}` → JSON list of chunk_ids
* `kv:{attempt_id}:entity_alias:{name}` → canonical entity id (optional)

✅ **Deletion safety trick (must do):**
Maintain a set of keys you created:

* `kv:{attempt_id}:__keys` (Redis SET)

Whenever you create a key `k`, do:

* `SET k value`
* `SADD kv:{attempt_id}:__keys k`

Cleanup:

* `SMEMBERS __keys` → batch delete → delete `__keys` itself

This avoids dangerous `KEYS kv:{attempt_id}:*` usage later.

---

# Runner scope (only two for now)

* `BaseRagRunner` (contract)
* `GraphRagRunner` (the only implementation for now)

No LightRAG runner, no NaiveRAG runner yet.

---

# Phase plan (developer-facing, with sanity checks + success gates)

## Phase 0 — Local Docker infra + config + health

**Goal:** One command boots all dependencies and the API can connect.

**Deliverables**

* `rag-service/docker-compose.yml` with services:

  * postgres, neo4j, redis, chroma
  * plus `rag-api` (optional; can run locally too)
* `.env.example` with all infra vars (no auth vars)
* `config.py` loads env and validates required fields
* `/health` endpoint checks:

  * Postgres connect
  * Neo4j connect
  * Redis ping
  * Chroma reachable

**Sanity checks**

* `docker compose up -d`
* `curl localhost:<api_port>/health` returns all green
* Restart all containers → still green

**Success criteria**

* Infra is reproducible and stable.
* App fails fast with clear errors if env missing.

**After Phase 0, you can**

* Start stack and verify dependencies in <1 minute.

---

## Phase 1 — Postgres schema + auth (sessions, not JWT)

**Goal:** Users exist, login returns access token, protected routes work.

**Deliverables**

* Alembic migrations for `users` + `sessions`
* Auth endpoints:

  * `POST /auth/signup` {email, password}
  * `POST /auth/login` {email, password} → {access_token}
  * `POST /auth/logout` (revokes current token)
  * `GET /auth/me` (returns user info)
* Auth dependency:

  * reads `Authorization: Bearer <token>`
  * hashes token and checks sessions table

**Sanity checks**

* signup + login works
* invalid token rejected
* `/auth/me` shows correct user
* logout revokes token (token stops working)

**Success criteria**

* We can authenticate without any auth secrets in env.
* Protected endpoints are truly protected.

**After Phase 1, you can**

* Create a user and call protected endpoints.

---

## Phase 2 — Corpora + attempts lifecycle (ownership enforced)

**Goal:** Users can create corpora and attempts exist as versioned builds.

**Deliverables**

* Migrations for `corpora` + `attempts`
* Filesystem storage:

  * write `data/corpora/<corpus_id>/source.txt`
* Endpoints (protected):

  * `POST /corpora` creates corpus row + attempt row (`queued`)
  * `GET /corpora` lists only the current user’s corpora
  * `GET /corpora/{corpus_id}` ownership enforced
  * `GET /corpora/{corpus_id}/attempts/{attempt_id}`

**Sanity checks**

* User A cannot access User B’s corpus
* Restart stack → corpus list persists
* Attempt is linked correctly to corpus

**Success criteria**

* Ownership is correct.
* Postgres is the source of truth and consistent.

**After Phase 2, you can**

* Create corpora and see attempts, but builds aren’t done yet.

---

## Phase 3 — BaseRagRunner + GraphRagRunner build (Neo4j + Chroma + Redis)

**Goal:** A build attempt actually produces GraphRAG artifacts across all stores.

**Deliverables**

* `runners/base.py` defines:

  * `build_index(text, meta)`
  * `load_index(artifacts)`
  * `retrieve(query, opts)`
  * `answer(query, contexts, opts)`
* `runners/graph_rag_runner.py` implements build pipeline:

### Build pipeline (exact steps)

1. Load `source.txt`
2. Chunking (`chunk_size`, `overlap`)
3. Embedding chunks (OpenAI embed model)
4. Create Chroma collection `col__{attempt_id}` and upsert vectors
5. Extract entities/relations (OpenAI model)
6. Upsert into Neo4j:

   * nodes: `(:Entity {id, name, corpus_id, attempt_id, ...})`
   * rels: `(:Entity)-[:REL {type, corpus_id, attempt_id, ...}]->(:Entity)`
7. Populate Redis KV namespace:

   * `chunk:{chunk_id}` → chunk text or pointer
   * `node_summary:{node_id}` → (optional but useful)
   * `node_chunks:{node_id}` → list of chunk_ids
   * add all keys to `__keys` set
8. Update attempt status to `ready` and save artifacts pointers:

   * `chroma_collection=col__{attempt_id}`
   * `redis_prefix=kv:{attempt_id}:`
   * `neo4j_filter=attempt_id` (implicit)

**Attempt status transitions**

* `queued → building → ready|failed`
* On failure, store error string and mark failed.

**Sanity checks**

* Create corpus triggers build and ends `ready`
* Chroma collection exists and has >0 vectors
* Neo4j has nodes tagged with attempt_id
* Redis has keys under the attempt prefix AND `__keys` set populated
* Build failure is recorded correctly when you intentionally break OpenAI key

**Success criteria**

* GraphRAG build works end-to-end and persists across restarts.

**After Phase 3, you can**

* Build real graph+vector+kv artifacts for a corpus.

---

## Phase 4 — Query endpoint (retrieve + answer)

**Goal:** User can ask questions and get answers with evidence.

**Deliverables**

* `POST /corpora/{corpus_id}/query`:

  * chooses attempt:

    * if request includes attempt_id → use it
    * else use `corpora.latest_success_attempt_id`
  * loads artifacts
  * retrieval strategy (minimum viable):

    1. vector search in Chroma → top_k chunks
    2. optionally expand via Neo4j:

       * map chunk entities to nodes
       * expand 1-hop neighbors
       * include their associated chunks via Redis `node_chunks`
    3. unify contexts + dedupe
  * answer via OpenAI with structured prompt that includes contexts

* (Optional but recommended) `POST /corpora/{corpus_id}/retrieve` for debug only

**Sanity checks**

* Query returns:

  * `answer` string
  * `contexts[]` each has `{text, score, meta}`
* Query fails cleanly if no ready attempt exists
* Ownership enforced

**Success criteria**

* “Create → build → query” is working for multiple users without leakage.

**After Phase 4, you can**

* Actually use the service as intended.

---

## Phase 5 — Deletion correctness (no leaks across stores)

**Goal:** Delete corpus removes everything across Postgres/Neo4j/Chroma/Redis.

**Deliverables**

* `DELETE /corpora/{corpus_id}`:

  * verify owner
  * for each attempt:

    * delete Chroma collection `col__{attempt_id}`
    * delete Neo4j nodes/edges by attempt_id
    * delete Redis keys using `__keys`
    * delete attempt row
  * delete corpus row
  * delete filesystem folder under `data/corpora/<corpus_id>`

**Sanity checks**

* After deletion:

  * Postgres: no corpus/attempt rows exist
  * Chroma: collection not found
  * Neo4j: `count(n)` for attempt_id is 0
  * Redis: `__keys` set gone and keys gone
* Delete called twice behaves safely (404 or idempotent)

**Success criteria**

* Zero leftovers. Cleanup is reliable.

**After Phase 5, you can**

* Operate without storage bloat and without cross-user contamination.

---

## Phase 6 — Async builds (optional but recommended soon)

**Goal:** Build doesn’t block API calls.

**Deliverables**

* Background build via FastAPI BackgroundTasks (simple first)
* Polling endpoint already exists (`GET attempt`)
* Attempt logs written to `data/.../logs.txt`

**Sanity checks**

* Create returns quickly (attempt queued/building)
* polling shows status eventually ready
* concurrent builds don’t corrupt stores

**Success criteria**

* API responsive under multiple builds.

**After Phase 6, you can**

* Use it like a real service.

---

# “How we know we’re progressing” after each phase (quick recap)

* **P0:** infra boots + /health ok
* **P1:** signup/login works; protected endpoints work
* **P2:** corpora/attempts persisted + ownership works
* **P3:** GraphRAG build writes to Neo4j + Chroma + Redis
* **P4:** query returns answer + contexts
* **P5:** delete cleans everything
* **P6:** builds async + status polling

---

# Extra dev notes (to prevent future pain)

### 1) IDs

Use `corpus_id` and `attempt_id` everywhere. Don’t invent new namespaces.

### 2) Logs

Always write `logs.txt` per attempt. When Neo4j/LLM extraction fails, logs are gold.

### 3) Neo4j schema discipline

Every node/edge must have `attempt_id`. That makes deletion and isolation trivial.

### 4) Redis KV discipline

Always add created keys to `kv:{attempt_id}:__keys`. This is your safe delete handle.

