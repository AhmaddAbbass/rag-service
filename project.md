# rag-service — Project Overview (Everything)

## What this project is
**rag-service** is a backend service that helps people turn raw text into a “smart knowledge source” they can query later.

A user provides:
- a large piece of text (for example: a book, notes, documentation, research paper, or any long article)
- optionally a `book_name` (a human-friendly label)

The service then builds a **GraphRAG** system for that text:
- it learns a **knowledge graph** of entities and relations (who/what connects to what)
- it also builds a **vector index** so it can retrieve the most relevant passages
- it stores extra key-value information needed by GraphRAG during retrieval and answering

After that, the user can ask questions like:
- “Summarize chapter 3”
- “What did the author say about X?”
- “How is A related to B?”
- “Give me evidence and explain it”

…and the service answers using the stored data.

---

## Why GraphRAG (and not just normal RAG)
Normal RAG mostly does:
1) retrieve chunks similar to your question
2) pass them to the LLM to answer

GraphRAG adds a **knowledge graph** layer so the system can:
- connect concepts across distant sections of the text
- expand retrieval through relationships (“if you asked about X, also pull related Y and Z”)
- answer questions that require linking multiple facts (“why is A connected to B?”)
- improve traceability and reduce missing context

So GraphRAG is meant for:
- deeper reasoning
- multi-hop questions
- better “connection making” over large texts

---

## Who this is for
This service is designed for people who want to build a RAG / KG pipeline **without manually wiring everything** each time.

Examples:
- researchers indexing papers/books
- teams indexing internal docs
- students indexing lecture notes
- developers indexing a project’s documentation

Key point: each new text becomes its own isolated “knowledge space”.

---

## Core user story (the full flow)
A user experience should look like this:

1) **Signup / Login**
   - user creates an account
   - user logs in and receives an access token (so the service knows who they are)

2) **Create a corpus**
   - user uploads text and optional `book_name`
   - service returns a `corpus_id` (the ID of that text)
   - service starts building the GraphRAG index in the background or synchronously (depending on setup)

3) **Wait for build to finish**
   - build status becomes `ready` if successful
   - or `failed` if something went wrong

4) **Query**
   - user asks a question against that `corpus_id`
   - service retrieves relevant content (vector retrieval + graph expansion)
   - service returns:
     - an answer
     - supporting contexts (evidence snippets)

5) **Manage**
   - user can list their corpora
   - inspect build attempts/status
   - delete a corpus and all its stored data

---

## Important concepts (explained simply)

### Corpus
A **corpus** is the input text a user provided (optionally named by `book_name`).
It’s the “thing” the user wants to query later.

### Attempt
An **attempt** is one build run for a corpus.
Why have attempts?
- user might rebuild later using improved logic/settings
- builds can fail and be retried
- we want versioning instead of overwriting

The service always knows which attempt is the “latest successful one” for default querying.

### Isolation / Multi-tenancy
Each user’s corpora are isolated:
- you can only see and query your own corpora
- data should never leak across users or across corpora

---

## What the service builds under the hood (high-level only)
When building GraphRAG, the service produces:

1) **Knowledge Graph (graph database)**
- entities: people, places, concepts, objects
- relations: how entities connect (e.g., “A causes B”, “X is part of Y”, “Ali is the father of …”)

2) **Vector Index (vector database)**
- chunks of the text are embedded
- enables “semantic search” so retrieval finds meaning, not just keywords

3) **KV Store (key-value database)**
GraphRAG needs supporting mappings like:
- which text chunks relate to which graph nodes
- summaries / precomputed info
- other fast lookup structures used during retrieval & answering

---

## What “correct behavior” means
The system must be reliable in these ways:

### Correctness
- answers should be based on retrieved evidence from the user’s text
- the service should return contexts used for the answer (traceability)

### Isolation
- no user can access another user’s corpora
- no corpus should mix with another corpus’s stored data

### Cleanup
- deleting a corpus should remove all associated stored data, fully

### Stability
- the same corpus can be queried repeatedly, even after service restarts

---

## Key endpoints (conceptual)
This project exposes these capabilities (exact URLs may evolve, but these are the “product features”):

- Authentication:
  - signup
  - login
  - logout
  - get current user

- Corpus lifecycle:
  - create corpus (start build)
  - list corpora
  - inspect corpus details
  - inspect build status (attempt)
  - delete corpus

- Query:
  - query corpus and get answer + contexts
  - (optional) retrieve-only endpoint for debugging

---

## What tests we should run (practical checklist)

### A) Smoke tests (basic “is the system alive?”)
1) Service starts successfully
2) Can reach health/status endpoint
3) All dependencies are reachable (DBs)

**Success looks like:** health endpoint shows all components OK.

---

### B) Auth tests (security baseline)
1) Signup works
2) Login returns an access token
3) Protected endpoints reject missing token
4) Token works for authorized calls
5) Logout revokes token (token stops working)

**Success looks like:** only authenticated users can access corpus/query operations.

---

### C) Corpus build tests (GraphRAG indexing)
1) Create corpus with a small sample text
2) Build finishes successfully (`ready`)
3) Attempt metadata shows artifacts exist (at a conceptual level)
4) Repeat with a second corpus and confirm separation

**Success looks like:** build is consistently reproducible, and corpora are isolated.

---

### D) Query tests (RAG quality + evidence)
1) Ask a question that has a clear answer in the text
2) Verify response includes:
   - answer
   - contexts (evidence snippets)
3) Ask a multi-hop question (requires linking two parts of text)
4) Verify retrieval returns relevant contexts, not random

**Success looks like:** answers are grounded in evidence from the correct corpus.

---

### E) Multi-user isolation tests (critical)
1) Create User A and User B
2) User A creates a corpus
3) User B tries to:
   - list it
   - inspect it
   - query it
   - delete it

**Success looks like:** User B is denied for all actions on User A’s corpus.

---

### F) Deletion tests (no leftovers)
1) Create corpus + build it
2) Query it once
3) Delete it
4) Confirm:
   - it no longer appears in list
   - it cannot be queried
   - creating a new corpus does not see any leftovers or contamination

**Success looks like:** deletion is complete and final.

---

### G) Restart / persistence tests
1) Create corpus, build, query
2) Restart services
3) Query again

**Success looks like:** the service still answers correctly after restart.

---

## What we are intentionally NOT doing yet
To keep scope clean and deliver the core product first, we are not focusing on:
- multiple RAG modes (LightRAG, NaiveRAG, etc.) — will come later
- advanced background job systems — attempts are enough for now
- fancy UI — this is a backend service

---

## Summary (one paragraph)
rag-service is a backend that turns user-provided text into a queryable GraphRAG knowledge base. It supports user accounts, isolates each user’s corpora, builds a knowledge graph + vector index + KV structures, and lets users query later with evidence. It includes lifecycle management (create, status, query, delete), and it must be testable through clear smoke/auth/build/query/isolation/deletion/restart checks.

---
