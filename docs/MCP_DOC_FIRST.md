# MCP Doc-First (Graph-Backed)

Membria enforces a **doc-first workflow** for MCP tools. The agent must call
`membria.fetch_docs` before using other tools that read/write memory. The
documents are pulled **from the graph**, not from external sources.

## Why doc-first even if docs are in the graph?

- Ensures the agent **explicitly loads** the minimal authoritative context.
- Provides **traceability** of which documents were used.
- Creates a consistent **session contract** for guardrails.
 - Produces a **doc-shot snapshot** that can be referenced in decisions.

## Tool: `membria.fetch_docs`

Fetch documents from the graph and return them to the agent.

**Inputs**
- `doc_types` (optional): list of doc types (e.g. `spec`, `guide`, `readme`)
- `file_paths` (optional): list of exact file paths
- `doc_ids` (optional): list of document ids
- `limit` (optional, default 10): max number of docs

**Outputs**
- `status`: `"success"`
- `count`: number of docs returned
- `doc_shot_id`: deterministic id for this doc snapshot
- `docs`: list of documents with `id`, `file_path`, `doc_type`, `updated_at`,
  `metadata`, `content`

## Guard behavior

- In the MCP daemon, if a tool is called **without a prior `membria.fetch_docs`**
  in the same session, Membria logs a **warning** (soft-guard).
- The daemon tracks a `session_docs` record keyed by `session_id`.

## Traceability (Decision → Docs)

- When a decision is recorded via MCP daemon and `session_id` is present,
  Membria links the decision to the docs used in the session.
- Relationships created:
  - `Decision -[:USES_DOCSHOT]-> DocShot`
  - `Decision -[:DOCUMENTS]-> Document` (with `doc_shot_id`, `doc_updated_at`)

## Temporary Factcheck (MVP)

- If a decision is recorded with `doc_shot_id`, Membria sets
  `Decision.factcheck_status = "pending"`.
- Factcheck can be closed manually by updating `factcheck_status` to
  `verified|failed|skipped`.

## Implementation

- MCP daemon tool: `/Users/miguelaprossine/membria-cli/src/membria/mcp_daemon.py`
- MCP server tool: `/Users/miguelaprossine/membria-cli/src/membria/mcp_server.py`
- Graph read: `/Users/miguelaprossine/membria-cli/src/membria/graph.py`
- Schemas: `/Users/miguelaprossine/membria-cli/src/membria/mcp_schemas.py`
