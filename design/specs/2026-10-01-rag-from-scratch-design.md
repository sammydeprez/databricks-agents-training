# RAG from scratch — demo notebook

Date: 2026-10-01. Status: approved in conversation, awaiting spec review.

## Purpose

Show, step by step and with visible output, what Knowledge Assistant (Lab 4) does behind the scenes:
extract text from PDFs, chunk it, embed it, search it, and let an agent use that search as a tool.
Used by the trainer as a live demo, and optionally run by participants afterwards in their own schema.
The extraction, chunking and embedding steps are the point — each one stops to show its output.

## Constraints (verified in the training workspace on 1 October 2026)

- `ai_parse_document(content)` over `read_files(..., format => 'binaryFile')` works on serverless
  SQL. FANR-REG-12 (231 KB): 20 pages, 175 typed elements, ~10 s.
- `ai_query('system.ai.gte-large-en', text)` returns a 1024-float embedding.
- Classic `databricks-*` serving endpoints are disabled ("use Unity Gateway"). Chat with tool
  calling works at `POST /ai-gateway/mlflow/v1/chat/completions`, model `system.ai.gpt-oss-120b`,
  via `WorkspaceClient().api_client.do(...)` — returns `tool_calls` with `finish_reason: tool_calls`.
  No extra packages needed (the OpenAI client is not installed on serverless).
- All Claude endpoints are disabled in this workspace; the chat model is a constant so it can change.
- No Vector Search endpoint: similarity is computed in plain SQL over a Delta table. The notebook
  states explicitly that a Vector Search endpoint is the better production choice and why it is
  skipped here.
- Must work with any catalog: same catalog logic as `lab_data` (empty box → `current_catalog()`).
- Repo must stay public, no client data: only the public FANR/IAEA PDFs already in the `docs` volume.

## Deliverables

1. `notebooks/rag_from_scratch.py` — Databricks source-format notebook, mostly `%sql` cells, one
   Python cell for the agent loop.
2. `docs/labs/extra-rag-from-scratch.md` — optional participant page (Day 2, after Lab 4): import
   URL, prerequisite (setup notebook run), what to look at in each step. Added to nav and index.
3. Trainer notes: when to demo, measured run times for Quick and All 6, known rough edges.

## Notebook structure

| # | Section | Creates | Shows |
|---|---|---|---|
| 0 | Intro | — | What this rebuilds (Lab 4's KA), the five stages, why no Vector Search endpoint |
| 1 | Settings | widgets `catalog`, `documents` (Quick = 2 smallest PDFs / All 6) | Resolved catalog + schema, the PDFs found in the volume |
| 2 | Extract | `rag_parsed` (path, file name, VARIANT result) | Pages/elements per document, element-type mix, raw elements of one page |
| 3 | Clean | `rag_elements` (doc, page, element index, type, text) | What is dropped (page headers/footers, figures, empty) and why |
| 4 | Chunk | `rag_chunks` (chunk id, doc, first/last page, text, length) | Chunk-length spread, three sample chunks, one boundary cutting a sentence; note on overlap / header-aware splitting |
| 5 | Embed | function `cosine_sim`; table `rag_index` = `rag_chunks` + `embedding ARRAY<FLOAT>` | First 8 numbers of one vector; 4-sentence similarity grid ("meaning, not words") |
| 6 | Search | SQL table function `search_regulations(question STRING)` → top 5 (doc, page, score, text) | Two example searches; Vector Search callout |
| 7 | Agent | — | Printed tool-calling loop for three questions: answerable, needs two searches, not in the documents |
| 8 | What KA did for you | — | Table mapping each stage to what Knowledge Assistant hid |
| 9 | Clean up | — | Note: `lab_data` cleanup drops the whole schema, including these objects |

### Chunking rule

Elements kept in document order. Running character total per document; chunk number =
`floor(running_total / 1000)`. Readable as one window function, deliberately naive so its weakness
(cuts mid-sentence) is visible and discussable.

### Search

`search_regulations(question)` embeds the question once with `ai_query`, computes cosine similarity
against every chunk with SQL array functions, returns the top 5. The callout names what an endpoint
adds: approximate nearest-neighbour index, automatic sync from the Delta table, filtering, scale.

### Agent loop

System prompt: answer only from search results, cite document and page, say so when nothing
relevant is found. Up to 4 tool rounds per question. Each round prints the model's tool call, the
rows returned, and finally the answer. The tool runs `SELECT ... FROM search_regulations(:q)` via
`spark.sql` with a parameter, not string concatenation.

## Error handling

- No PDFs in the volume → stop with "run the setup notebook first".
- `hive_metastore` default catalog → same message as `lab_data`.
- Model call failure → print the endpoint error and the model constant to change.

## Testing

Run end to end in the training workspace with Quick and All 6. Check: row counts at each stage,
embedding dimension 1024, search returns the expected document for two known questions, the three
agent questions behave as described. Record run times. `mkdocs build --strict` passes.

## Out of scope

Vector Search endpoint, Lakebase/pgvector, overlap or header-aware chunking (discussed, not built),
OCR quality tuning, evaluation harness.
