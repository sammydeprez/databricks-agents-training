# RAG from scratch — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Databricks demo notebook that parses the Lab 4 PDFs with `ai_parse_document`, chunks and embeds them in SQL, searches them with plain-SQL cosine similarity, and runs a visible tool-calling agent over that search — plus an optional guide page.

**Architecture:** One Databricks source-format notebook (`notebooks/rag_from_scratch.py`), mostly `%sql` cells against the participant's own schema (`USE CATALOG/SCHEMA` set in the first Python cell). Four Delta tables (`rag_parsed`, `rag_elements`, `rag_chunks`, `rag_index`) and two SQL functions (`cosine_sim`, `search_regulations`). One Python cell runs the agent loop through Unity Gateway's `chat/completions` route.

**Tech Stack:** Databricks serverless notebook, Databricks SQL (`ai_parse_document`, `ai_query`, `variant_explode`, higher-order array functions), Databricks SDK `WorkspaceClient().api_client`, MkDocs Material.

**Spec:** `design/specs/2026-10-01-rag-from-scratch-design.md`

## Global Constraints

- Embedding model: `system.ai.gte-large-en` (1024 floats). Chat model: `system.ai.gpt-oss-120b` via `POST /ai-gateway/mlflow/v1/chat/completions`.
- No Vector Search endpoint; the notebook says a Vector Search endpoint is the better production choice and why it's skipped.
- Catalog: widget `catalog`, empty → `current_catalog()`; `hive_metastore` → stop with the `lab_data` message. Schema = sanitised login, same rule as `00_setup_my_data.py`.
- Documents: widget `documents` = `Quick (2 small PDFs)` (FANR-REG-12.pdf, FANR-REG-17.pdf) or `All 6 PDFs`.
- No extra pip installs. Public documents only. No client names.
- `read_files` needs a constant path → pass it as a named parameter via `spark.sql(sql, args=...)`.
- Page numbers shown to people are 1-based (`page_id + 1`).

## Review Focus

- Setup notebook not run (no PDFs in the volume) → the settings cell stops with "run the lab_data notebook first", not a stack trace. Pinned in Task 1.
- Re-running the notebook (or switching Quick → All 6) → every table and function is `CREATE OR REPLACE`; second run gives the same row counts. Pinned in Task 6 (re-run check).
- Model call fails (endpoint renamed/disabled) → the agent cell prints the error and names `CHAT_MODEL` to change. Pinned in Task 5.
- Question with no answer in the documents → agent says it couldn't find it, does not invent. Pinned in Task 5 (third question).
- An element longer than the chunk size → becomes its own (long) chunk, not dropped. Pinned in Task 2 check (`max(len)` reported, no element lost: kept elements = elements in chunks).

## Testing approach

Notebooks can't be unit-tested locally. Each section ends with a **Check** cell containing Python `assert`s on the tables it created. "Run the test" = import the notebook into the workspace (**Workspace > ⋮ > Import > File**) and **Run all**; a failing assert stops the run at the broken section. Local check: `python3 -c "import ast; ast.parse(open('notebooks/rag_from_scratch.py').read())"`.

---

### Task 1: Notebook skeleton, settings, extract

**Files:**
- Create: `notebooks/rag_from_scratch.py`

**Interfaces:**
- Produces: session `USE CATALOG/SCHEMA`; Python vars `CATALOG`, `SCHEMA_NAME`, `DOCS`, `SELECTED`; table `rag_parsed(path STRING, doc_name STRING, parsed VARIANT)`.

- [ ] **Step 1: Write the intro, settings cell and its check**

```python
# Databricks notebook source
# MAGIC %md
# MAGIC # RAG from scratch
# MAGIC In Lab 4 you gave Knowledge Assistant six PDFs and it answered questions about them. This notebook
# MAGIC does the same job **by hand, one visible step at a time**, using only built-in AI functions in SQL:
# MAGIC
# MAGIC 1. **Extract** — read the text, tables and figures out of each PDF (`ai_parse_document`)
# MAGIC 2. **Clean** — keep the content, drop page headers, footers and logos
# MAGIC 3. **Chunk** — cut the text into pieces of about 1,000 characters
# MAGIC 4. **Embed** — turn every chunk into a list of 1,024 numbers that captures its meaning (`ai_query`)
# MAGIC 5. **Search** — find the chunks closest in meaning to a question
# MAGIC 6. **Agent** — let a chat model decide when to search, and answer from what it finds
# MAGIC
# MAGIC Run the **lab_data** notebook first (it puts the PDFs in your `docs` volume). Then click **Run all**.
# MAGIC
# MAGIC > **Why no Vector Search endpoint?** In a real system you'd store the vectors in a Mosaic AI Vector
# MAGIC > Search index. Here we keep them in an ordinary table and compare a question against every chunk
# MAGIC > in SQL — fast enough for a few thousand chunks, no extra cost, and you can read exactly how it
# MAGIC > works. Step 5 explains what an endpoint would add.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 0. Settings
# MAGIC **Catalog:** leave empty unless your trainer gives you one (same as the lab_data notebook).
# MAGIC **Documents:** *Quick* parses two short regulations in about a minute — good for a live demo.
# MAGIC *All 6* parses everything, including the 248-page IAEA glossary, and takes several minutes.

# COMMAND ----------

import re

dbutils.widgets.text("catalog", "", "Catalog (leave empty unless your trainer gives you one)")
dbutils.widgets.dropdown("documents", "Quick (2 small PDFs)", ["Quick (2 small PDFs)", "All 6 PDFs"], "Documents")

CATALOG = dbutils.widgets.get("catalog").strip() or spark.sql("SELECT current_catalog() AS c").first()["c"]
if CATALOG == "hive_metastore":
    raise Exception("Your workspace's default catalog is hive_metastore, which can't hold the lab data. "
                    "Ask your trainer for a catalog name and type it into the 'catalog' box at the top.")
user_email = spark.sql("SELECT current_user() AS u").first()["u"]
SCHEMA_NAME = re.sub(r"[^a-z0-9_]", "_", user_email.split("@")[0].lower())
spark.sql(f"USE CATALOG `{CATALOG}`")
spark.sql(f"USE SCHEMA `{SCHEMA_NAME}`")

DOCS = f"/Volumes/{CATALOG}/{SCHEMA_NAME}/docs"
QUICK = ["FANR-REG-12.pdf", "FANR-REG-17.pdf"]  # emergency preparedness (20 pages), operator certification (14 pages)
try:
    available = sorted(f.name for f in dbutils.fs.ls(DOCS) if f.name.endswith(".pdf"))
except Exception:
    available = []
if not available:
    raise Exception(f"No PDFs found in {DOCS}. Run the lab_data notebook first (Set up my data), then come back.")
SELECTED = [n for n in QUICK if n in available] if dbutils.widgets.get("documents").startswith("Quick") else available

print(f"Working in {CATALOG}.{SCHEMA_NAME}")
print(f"Documents to process ({len(SELECTED)}):")
for n in SELECTED:
    print("  -", n)
```

- [ ] **Step 2: Write the extract cells**

```python
# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Extract: what's actually inside a PDF?
# MAGIC A PDF is a picture of a page, not a list of sentences. `ai_parse_document` looks at each page and
# MAGIC returns its **elements**: titles, paragraphs, tables, figures, page headers and footers — each with
# MAGIC its type, its text, and where on which page it sits. Figures even get a written description.
# MAGIC
# MAGIC We store the raw result once in `rag_parsed`, so the slow part never has to run twice.

# COMMAND ----------

spark.sql("""
CREATE OR REPLACE TABLE rag_parsed AS
SELECT path,
       regexp_extract(path, '[^/]+$', 0) AS doc_name,
       ai_parse_document(content)        AS parsed
FROM read_files(:docs, format => 'binaryFile', pathGlobFilter => '*.pdf')
WHERE regexp_extract(path, '[^/]+$', 0) IN (SELECT explode(from_json(:selected, 'array<string>')))
""", args={"docs": DOCS, "selected": json.dumps(SELECTED)})
print("parsed:", spark.table("rag_parsed").count(), "document(s)")

# COMMAND ----------

# MAGIC %sql
# MAGIC -- How much did we get out of each document?
# MAGIC SELECT doc_name,
# MAGIC        size(cast(parsed:document:pages AS ARRAY<VARIANT>))    AS pages,
# MAGIC        size(cast(parsed:document:elements AS ARRAY<VARIANT>)) AS elements,
# MAGIC        cast(parsed:error_status AS STRING)                    AS errors
# MAGIC FROM rag_parsed
# MAGIC ORDER BY doc_name

# COMMAND ----------

# MAGIC %sql
# MAGIC -- The raw elements of page 5 of the first document, in reading order.
# MAGIC -- Look at the 'type' column: this is what the parser understood about the layout.
# MAGIC SELECT el.pos                                        AS element,
# MAGIC        el.value:type::STRING                         AS type,
# MAGIC        el.value:content::STRING                      AS text,
# MAGIC        el.value:description::STRING                  AS figure_description
# MAGIC FROM (SELECT * FROM rag_parsed ORDER BY doc_name LIMIT 1),
# MAGIC      LATERAL variant_explode(parsed:document:elements) AS el
# MAGIC WHERE el.value:bbox[0]:page_id::INT = 4
# MAGIC ORDER BY el.pos
```

Change the settings cell's first line from `import re` to `import json, re`.

- [ ] **Step 3: Write the Task 1 check cell**

```python
# COMMAND ----------

# Check: one parsed row per selected document, no parse errors, and every document has elements.
rows = spark.sql("""SELECT doc_name, size(cast(parsed:document:elements AS ARRAY<VARIANT>)) AS n,
                           cast(parsed:error_status AS STRING) AS err FROM rag_parsed""").collect()
assert sorted(r.doc_name for r in rows) == sorted(SELECTED), f"expected {SELECTED}, got {[r.doc_name for r in rows]}"
assert all(r.n and r.n > 0 for r in rows), "a document came back with no elements"
assert all(r.err in (None, "null", "[]") for r in rows), f"parse errors: {[(r.doc_name, r.err) for r in rows]}"
print("Extract OK")
```

- [ ] **Step 4: Syntax-check locally**

Run: `python3 -c "import ast; ast.parse(open('notebooks/rag_from_scratch.py').read()); print('ok')"`
Expected: `ok`

- [ ] **Step 5: Run in the workspace (Quick)**

Import the file (**Workspace > ⋮ > Import > File**), Run all. Expected: settings prints two PDFs; summary shows FANR-REG-12 (20 pages) and FANR-REG-17; page-5 table shows typed elements; `Extract OK`.
Also: temporarily point `DOCS` at an empty path and confirm the "Run the lab_data notebook first" message (Review Focus 1), then revert.

- [ ] **Step 6: Commit**

```bash
git add notebooks/rag_from_scratch.py
git commit -m "RAG demo: settings and extract with ai_parse_document"
```

---

### Task 2: Clean and chunk

**Files:**
- Modify: `notebooks/rag_from_scratch.py` (append)

**Interfaces:**
- Consumes: `rag_parsed`.
- Produces: `rag_elements(doc_name STRING, element_index INT, page INT, element_type STRING, text STRING, kept BOOLEAN)`; `rag_chunks(chunk_id STRING, doc_name STRING, first_page INT, last_page INT, text STRING, chars INT)`.

- [ ] **Step 1: Write the clean cells**

```python
# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Clean: keep the content, drop the furniture
# MAGIC Every page repeats the same header, footer and page number. If we kept them, half our search
# MAGIC results would be "Federal Authority for Nuclear Regulation — page 7". So we flatten the elements
# MAGIC into one row each, and mark what to keep.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE rag_elements AS
# MAGIC SELECT doc_name,
# MAGIC        el.pos                                  AS element_index,
# MAGIC        el.value:bbox[0]:page_id::INT + 1       AS page,
# MAGIC        el.value:type::STRING                   AS element_type,
# MAGIC        trim(el.value:content::STRING)          AS text,
# MAGIC        el.value:type::STRING NOT IN ('page_header', 'page_footer', 'page_number', 'figure')
# MAGIC          AND length(trim(el.value:content::STRING)) > 0 AS kept
# MAGIC FROM rag_parsed, LATERAL variant_explode(parsed:document:elements) AS el

# COMMAND ----------

# MAGIC %sql
# MAGIC -- What did we keep, and what did we throw away?
# MAGIC SELECT element_type, kept, count(*) AS elements, any_value(left(text, 80)) AS example
# MAGIC FROM rag_elements
# MAGIC GROUP BY element_type, kept
# MAGIC ORDER BY kept DESC, elements DESC
```

- [ ] **Step 2: Write the chunk cells**

```python
# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Chunk: cut the text into pieces
# MAGIC A search should return a paragraph, not a whole 200-page document — and a model can only read so
# MAGIC much at once. So we glue consecutive elements together until we have about **1,000 characters**,
# MAGIC then start a new chunk. The rule is one window function: keep a running count of characters per
# MAGIC document, and chunk number = running count ÷ 1,000, rounded down.
# MAGIC
# MAGIC This rule is deliberately simple. Look at the samples below: sometimes a chunk ends mid-sentence,
# MAGIC or mixes the end of one section with the start of the next. Real systems fix that with
# MAGIC **overlap** (each chunk repeats the end of the previous one) and by **splitting on section
# MAGIC headers** — Knowledge Assistant does both for you.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE rag_chunks AS
# MAGIC WITH running AS (
# MAGIC   SELECT *,
# MAGIC          sum(length(text) + 1) OVER (PARTITION BY doc_name ORDER BY element_index
# MAGIC                                      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS chars_so_far
# MAGIC   FROM rag_elements
# MAGIC   WHERE kept
# MAGIC ),
# MAGIC numbered AS (
# MAGIC   SELECT *, cast(floor((chars_so_far - 1) / 1000) AS INT) AS chunk_no FROM running
# MAGIC )
# MAGIC SELECT concat(doc_name, ' #', lpad(cast(chunk_no AS STRING), 3, '0'))                   AS chunk_id,
# MAGIC        doc_name,
# MAGIC        min(page)                                                                         AS first_page,
# MAGIC        max(page)                                                                         AS last_page,
# MAGIC        concat_ws('\n', transform(array_sort(collect_list(struct(element_index, text))), x -> x.text)) AS text,
# MAGIC        count(*)                                                                          AS elements
# MAGIC FROM numbered
# MAGIC GROUP BY doc_name, chunk_no

# COMMAND ----------

# MAGIC %sql
# MAGIC -- How big are the chunks? Most should be close to 1,000 characters; a very long table or
# MAGIC -- paragraph becomes one bigger chunk on its own.
# MAGIC SELECT doc_name, count(*) AS chunks,
# MAGIC        min(length(text)) AS shortest, cast(avg(length(text)) AS INT) AS average, max(length(text)) AS longest
# MAGIC FROM rag_chunks
# MAGIC GROUP BY doc_name
# MAGIC ORDER BY doc_name

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Three chunks to read. Where does each one start and stop? Would you have cut it there?
# MAGIC SELECT chunk_id, first_page, last_page, length(text) AS chars, text
# MAGIC FROM rag_chunks
# MAGIC ORDER BY chunk_id
# MAGIC LIMIT 3 OFFSET 4
```

- [ ] **Step 3: Write the Task 2 check cell**

```python
# COMMAND ----------

# Check: nothing kept was lost on the way into chunks, and chunk sizes are sensible.
kept = spark.sql("SELECT count(*) AS n FROM rag_elements WHERE kept").first().n
in_chunks = spark.sql("SELECT sum(elements) AS n FROM rag_chunks").first().n
assert kept == in_chunks, f"{kept} kept elements but {in_chunks} in chunks"
avg_len = spark.sql("SELECT avg(length(text)) AS a FROM rag_chunks").first().a
assert 500 < avg_len < 2500, f"average chunk length {avg_len} looks wrong"
print(f"Chunk OK: {in_chunks} elements in {spark.table('rag_chunks').count()} chunks, average {int(avg_len)} characters")
```

- [ ] **Step 4: Syntax-check locally** — same command as Task 1 Step 4, expect `ok`.

- [ ] **Step 5: Run in the workspace (Quick)** — re-import, Run all. Expected: kept/dropped table shows `page_footer`/`figure` with `kept = false`; chunk stats per document; `Chunk OK`.

- [ ] **Step 6: Commit**

```bash
git add notebooks/rag_from_scratch.py
git commit -m "RAG demo: clean elements and chunk with a running character count"
```

---

### Task 3: Embed

**Files:**
- Modify: `notebooks/rag_from_scratch.py` (append)

**Interfaces:**
- Consumes: `rag_chunks`.
- Produces: `cosine_sim(a ARRAY<FLOAT>, b ARRAY<FLOAT>) RETURNS DOUBLE`; `rag_index` = `rag_chunks` columns + `embedding ARRAY<FLOAT>`.

- [ ] **Step 1: Write the "meaning, not words" cells**

```python
# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Embed: turn meaning into numbers
# MAGIC An **embedding model** reads a piece of text and returns a fixed-length list of numbers — here
# MAGIC 1,024 of them. Texts that mean similar things get similar lists, even when they share no words.
# MAGIC To compare two lists we use **cosine similarity**: 1 means "pointing the same way", 0 means
# MAGIC "unrelated". It's three lines of SQL, so let's write it ourselves.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION cosine_sim(a ARRAY<FLOAT>, b ARRAY<FLOAT>)
# MAGIC RETURNS DOUBLE
# MAGIC COMMENT 'Cosine similarity of two vectors: 1 = same direction, 0 = unrelated'
# MAGIC RETURN aggregate(zip_with(a, b, (x, y) -> x * y), 0D, (acc, v) -> acc + v)
# MAGIC        / (sqrt(aggregate(a, 0D, (acc, x) -> acc + x * x)) * sqrt(aggregate(b, 0D, (acc, x) -> acc + x * x)))

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Four sentences. 1 and 2 mean the same with different words. 4 shares the word "drill" with
# MAGIC -- sentence 1 but means something else. Which pairs score highest?
# MAGIC WITH sentences AS (
# MAGIC   SELECT * FROM VALUES
# MAGIC     (1, 'How often must emergency drills be held?'),
# MAGIC     (2, 'What is the required frequency of emergency exercises?'),
# MAGIC     (3, 'Who may operate the reactor control room?'),
# MAGIC     (4, 'The drill bit broke while boring into the concrete wall.') AS t(id, sentence)
# MAGIC ),
# MAGIC vectors AS (SELECT id, sentence, ai_query('system.ai.gte-large-en', sentence) AS v FROM sentences)
# MAGIC SELECT a.id AS s1, b.id AS s2, round(cosine_sim(a.v, b.v), 3) AS similarity, a.sentence AS sentence_1, b.sentence AS sentence_2
# MAGIC FROM vectors a JOIN vectors b ON a.id < b.id
# MAGIC ORDER BY similarity DESC
```

- [ ] **Step 2: Write the embed-chunks cells**

```python
# COMMAND ----------

# MAGIC %md
# MAGIC Now the same for every chunk. One `ai_query` call per row — Databricks batches them for you.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE rag_index AS
# MAGIC SELECT *, ai_query('system.ai.gte-large-en', text) AS embedding
# MAGIC FROM rag_chunks

# COMMAND ----------

# MAGIC %sql
# MAGIC -- What a chunk looks like to the search: its text, and 1,024 numbers (first 8 shown).
# MAGIC SELECT chunk_id, left(text, 120) AS text_start, size(embedding) AS dimensions, slice(embedding, 1, 8) AS first_8_numbers
# MAGIC FROM rag_index
# MAGIC ORDER BY chunk_id
# MAGIC LIMIT 5
```

- [ ] **Step 3: Write the Task 3 check cell**

```python
# COMMAND ----------

# Check: every chunk has a 1,024-number embedding, and cosine_sim behaves.
bad = spark.sql("SELECT count(*) AS n FROM rag_index WHERE embedding IS NULL OR size(embedding) <> 1024").first().n
assert bad == 0, f"{bad} chunk(s) without a proper embedding"
assert spark.table("rag_index").count() == spark.table("rag_chunks").count()
same = spark.sql("SELECT cosine_sim(array(1F, 2F, 3F), array(1F, 2F, 3F)) AS s").first().s
assert abs(same - 1.0) < 1e-6, same
print("Embed OK")
```

- [ ] **Step 4: Syntax-check locally** — expect `ok`.

- [ ] **Step 5: Run in the workspace (Quick)** — expected: sentence pair (1, 2) scores highest; pair (1, 4) noticeably lower despite sharing "drill"; dimensions = 1024; `Embed OK`. Record the actual scores for the trainer note.

- [ ] **Step 6: Commit**

```bash
git add notebooks/rag_from_scratch.py
git commit -m "RAG demo: embed chunks and show cosine similarity on four sentences"
```

---

### Task 4: Search function

**Files:**
- Modify: `notebooks/rag_from_scratch.py` (append)

**Interfaces:**
- Consumes: `rag_index`, `cosine_sim`.
- Produces: `search_regulations(question STRING) RETURNS TABLE (doc_name STRING, first_page INT, last_page INT, score DOUBLE, text STRING)` — top 5 by score.

- [ ] **Step 1: Write the search cells**

```python
# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Search: compare the question with every chunk
# MAGIC Searching is now three moves: embed the question with the same model, score every chunk with
# MAGIC `cosine_sim`, keep the top 5. We wrap that in a SQL function so anything — a query, a dashboard,
# MAGIC an agent — can call it by name.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION search_regulations(question STRING)
# MAGIC RETURNS TABLE (doc_name STRING, first_page INT, last_page INT, score DOUBLE, text STRING)
# MAGIC COMMENT 'Finds the 5 passages of the FANR regulations and IAEA safety guides closest in meaning to the question.'
# MAGIC RETURN
# MAGIC   WITH q AS (SELECT ai_query('system.ai.gte-large-en', question) AS v)
# MAGIC   SELECT i.doc_name, i.first_page, i.last_page, cosine_sim(i.embedding, q.v) AS score, i.text
# MAGIC   FROM rag_index i CROSS JOIN q
# MAGIC   ORDER BY score DESC
# MAGIC   LIMIT 5

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT round(score, 3) AS score, doc_name, first_page, last_page, left(text, 200) AS passage
# MAGIC FROM search_regulations('How often must the operator run emergency exercises?')

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT round(score, 3) AS score, doc_name, first_page, last_page, left(text, 200) AS passage
# MAGIC FROM search_regulations('What training does a shift supervisor need before certification?')

# COMMAND ----------

# MAGIC %md
# MAGIC > **In production, use a Vector Search endpoint instead.** What we just did is a *brute-force*
# MAGIC > search: every question is compared with every chunk. That's fine for a few thousand chunks, and
# MAGIC > you can read every line of it. A Mosaic AI Vector Search endpoint adds what a real system needs:
# MAGIC > an **approximate nearest-neighbour index** that stays fast at millions of chunks, **automatic
# MAGIC > sync** when the source table changes, **filters** (for example "only FANR documents"), and
# MAGIC > **hybrid search** that mixes meaning with exact keyword matches. We skip it here because it needs
# MAGIC > an always-on endpoint, takes a while to provision, and hides the very steps this notebook is about.
```

- [ ] **Step 2: Write the Task 4 check cell**

```python
# COMMAND ----------

# Check: the emergency-exercise question finds the emergency regulation first.
top = spark.sql("SELECT doc_name FROM search_regulations('How often must the operator run emergency exercises?')").collect()
assert len(top) == 5, f"expected 5 results, got {len(top)}"
assert top[0].doc_name == "FANR-REG-12.pdf", f"top hit was {top[0].doc_name}"
print("Search OK")
```

- [ ] **Step 3: Syntax-check locally** — expect `ok`.

- [ ] **Step 4: Run in the workspace (Quick)** — expected: first search's top hits are FANR-REG-12, second's FANR-REG-17; `Search OK`.

- [ ] **Step 5: Commit**

```bash
git add notebooks/rag_from_scratch.py
git commit -m "RAG demo: brute-force search_regulations function and Vector Search callout"
```

---

### Task 5: Agent loop

**Files:**
- Modify: `notebooks/rag_from_scratch.py` (append)

**Interfaces:**
- Consumes: `search_regulations` (SQL), `/ai-gateway/mlflow/v1/chat/completions`.
- Produces: Python `ask(question: str, max_rounds: int = 4) -> str` (final answer text, also printed).

- [ ] **Step 1: Write the agent cells**

```python
# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Agent: let the model decide when to search
# MAGIC This is the tool-calling loop from the morning's theory, with nothing hidden:
# MAGIC
# MAGIC 1. We send the question plus a description of one tool, `search_regulations`.
# MAGIC 2. The model doesn't answer yet — it replies "please call `search_regulations` with this question".
# MAGIC 3. **Our code** runs the SQL function and sends the passages back.
# MAGIC 4. The model either searches again or writes the answer, citing document and page.
# MAGIC
# MAGIC The model never touches the data itself. It only asks; we decide what runs.

# COMMAND ----------

import json
from databricks.sdk import WorkspaceClient

CHAT_MODEL = "system.ai.gpt-oss-120b"   # change here if your workspace uses a different chat model
w = WorkspaceClient()

TOOLS = [{
    "type": "function",
    "function": {
        "name": "search_regulations",
        "description": "Search the FANR regulations and IAEA safety guides. Returns the 5 most relevant "
                       "passages with document name and page numbers.",
        "parameters": {
            "type": "object",
            "properties": {"question": {"type": "string", "description": "What to look up, in plain English"}},
            "required": ["question"],
        },
    },
}]

SYSTEM = ("You answer questions about nuclear safety regulations. Always call search_regulations before "
          "answering, and search again if the first results don't cover every part of the question. "
          "Answer only from the passages it returns and cite each fact as (document, page). "
          "If the passages don't contain the answer, say you couldn't find it in the documents.")


def search_regulations(question):
    rows = spark.sql(
        "SELECT doc_name, first_page, last_page, round(score, 3) AS score, text FROM search_regulations(:q)",
        args={"q": question},
    ).collect()
    return [r.asDict() for r in rows]


def text_of(message):
    content = message.get("content")
    if isinstance(content, str):
        return content
    parts = content or []
    return "\n".join(p.get("text", "") for p in parts if p.get("type") in ("text", "output_text"))


def ask(question, max_rounds=4):
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    print(f"USER: {question}\n")
    for _ in range(max_rounds):
        try:
            reply = w.api_client.do("POST", "/ai-gateway/mlflow/v1/chat/completions",
                                    body={"model": CHAT_MODEL, "messages": messages, "tools": TOOLS, "max_tokens": 2000})
        except Exception as e:
            print(f"The model call failed: {e}\nCheck that CHAT_MODEL = {CHAT_MODEL!r} exists in Unity Gateway "
                  "(AI/ML > AI Gateway) and change it in the cell above if not.")
            return ""
        message = reply["choices"][0]["message"]
        calls = message.get("tool_calls") or []
        if not calls:
            answer = text_of(message)
            print("ASSISTANT:\n" + answer)
            return answer
        messages.append({"role": "assistant", "content": text_of(message), "tool_calls": calls})
        for call in calls:
            query = json.loads(call["function"]["arguments"]).get("question", question)
            print(f"MODEL ASKS: search_regulations({query!r})")
            hits = search_regulations(query)
            for h in hits:
                print(f"   {h['score']:.3f}  {h['doc_name']} p.{h['first_page']}-{h['last_page']}  {h['text'][:80]!r}")
            print()
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(hits)})
    print(f"(stopped after {max_rounds} rounds without a final answer)")
    return ""

# COMMAND ----------

answer_1 = ask("How often does a nuclear facility have to hold emergency exercises, and who must take part?")

# COMMAND ----------

answer_2 = ask("What must a reactor operator have done before FANR certifies them, and what is their role "
               "during an emergency?")

# COMMAND ----------

# MAGIC %md
# MAGIC A question the documents can't answer. A good agent says so instead of guessing.

# COMMAND ----------

answer_3 = ask("What is the speed limit for vehicles on the plant site?")
```

- [ ] **Step 2: Write the Task 5 check cell**

```python
# COMMAND ----------

# Check: answers came back, the first one cites the emergency regulation, the third admits it didn't find it.
assert answer_1 and "REG-12" in answer_1, "answer 1 should cite FANR-REG-12"
assert answer_2, "answer 2 is empty"
assert any(w_ in answer_3.lower() for w_ in ("couldn't find", "could not find", "not found", "no information", "not contain", "does not")), \
    "answer 3 should say the documents don't cover it"
print("Agent OK")
```

- [ ] **Step 3: Syntax-check locally** — expect `ok`.

- [ ] **Step 4: Run in the workspace (Quick)** — expected: each `ask` prints at least one `MODEL ASKS:` line with five hits; question 2 shows two searches (one per topic) or one search that hits both documents; question 3 ends with "couldn't find"; `Agent OK`. Also set `CHAT_MODEL = "system.ai.does-not-exist"` once and confirm the friendly message (Review Focus 3), then revert.

- [ ] **Step 5: Commit**

```bash
git add notebooks/rag_from_scratch.py
git commit -m "RAG demo: visible tool-calling agent over search_regulations"
```

---

### Task 6: Wrap-up cells, full run, guide page

**Files:**
- Modify: `notebooks/rag_from_scratch.py` (append)
- Create: `docs/labs/extra-rag-from-scratch.md`
- Modify: `mkdocs.yml` (Day 2 nav, after Lab 4), `docs/index.md` (table row), `docs/trainer-notes.md` (Known snags / Day 2 note)

- [ ] **Step 1: Write the closing cells**

```python
# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. What Knowledge Assistant did for you
# MAGIC | Step here | In Lab 4's Knowledge Assistant |
# MAGIC |---|---|
# MAGIC | `ai_parse_document` into `rag_parsed` | Done when you picked the volume as a source |
# MAGIC | Drop headers, footers, figures | Done for you |
# MAGIC | 1,000-character chunks | Smarter chunks, with overlap and section awareness |
# MAGIC | `ai_query` embeddings into `rag_index` | Done for you, kept in sync when files change |
# MAGIC | `search_regulations` brute-force SQL | A Vector Search index |
# MAGIC | The `ask` loop and system prompt | The agent, its instructions, and the citations panel |
# MAGIC
# MAGIC Knowledge Assistant is the right choice when you want this to just work. Building it by hand is
# MAGIC how you understand why an answer came out the way it did — and where to look when it's wrong.
# MAGIC
# MAGIC ## Clean up
# MAGIC Nothing to do here: everything this notebook made (`rag_parsed`, `rag_elements`, `rag_chunks`,
# MAGIC `rag_index`, `cosine_sim`, `search_regulations`) lives in your schema, which the **lab_data**
# MAGIC notebook's **Clean up my data** removes at the end of the training.
```

- [ ] **Step 2: Full run, Quick and All 6, plus re-run** — In the workspace: Run all with Quick; note total time. Run all again (re-run must pass unchanged — Review Focus 2). Switch to All 6, Run all; note time and chunk count. All checks print OK.

- [ ] **Step 3: Write the guide page `docs/labs/extra-rag-from-scratch.md`**

```markdown
# Extra: build RAG by hand

**Goal:** see every step Knowledge Assistant hides — extract, chunk, embed, search, agent — by running them yourself in SQL.
**Time:** 20–30 minutes (optional). **Code written:** none — you run a notebook and read its output.

Your trainer will demo this. If you want to run it yourself afterwards:

1. Make sure you've run the **lab_data** notebook (see [Before you start](../setup.md)).
2. In **Workspace**, click **⋮ > Import**, choose **URL**, and paste:

    ```text
    https://raw.githubusercontent.com/sammydeprez/databricks-agents-training/develop/notebooks/rag_from_scratch.py
    ```

3. Open **rag_from_scratch**. Leave **Catalog** as you did for lab_data, keep **Documents** on **Quick**, and click **Run all**.

## What to look at

| Step | Look at | Ask yourself |
|---|---|---|
| 1. Extract | The element types on page 5 | What did the parser think was a heading, a table, a figure? |
| 2. Clean | The kept / dropped table | What would search results look like if we kept the footers? |
| 3. Chunk | The three sample chunks | Where would you have cut instead? |
| 4. Embed | The four-sentence similarity grid | Why does "drill bit" score lower than "emergency exercises", despite sharing a word? |
| 5. Search | The two example searches | Is the top passage the one you'd have picked? |
| 6. Agent | The `MODEL ASKS:` lines | When did it search twice? What did it say when the answer wasn't there? |

!!! note "Why not a Vector Search endpoint?"
    A real system would put the vectors in a Mosaic AI Vector Search index. The notebook compares the
    question with every chunk in plain SQL instead — fine for a few thousand chunks, no extra cost, and
    every line readable. The notebook's Step 5 explains what an endpoint would add.

**Check yourself**

- [ ] Which step would you change first if answers kept citing the wrong page?
- [ ] What did Knowledge Assistant do for you in Lab 4 that you had to do by hand here?
```

- [ ] **Step 4: Wire it into the site**

`mkdocs.yml` Day 2, after Lab 4:
```yaml
      - Lab 4, Knowledge Assistant: labs/lab4-knowledge-assistant.md
      - Extra, build RAG by hand: labs/extra-rag-from-scratch.md
```
`docs/index.md`, after the Lab 4 row:
```markdown
| 2 | [Extra: RAG by hand](labs/extra-rag-from-scratch.md) | Optional: extract, chunk, embed and search the regulations yourself in SQL | 20–30 min |
```
`docs/trainer-notes.md`, Known snags — add (with the measured numbers from Step 2):
```markdown
- **RAG-from-scratch demo** (`notebooks/rag_from_scratch.py`): Quick mode ran in <QUICK> on serverless,
  All 6 in <ALL6> (<N> chunks). Good moment to demo: right after Lab 4 Part B, while the Knowledge
  Assistant's answers are fresh. It calls models through Unity Gateway (`/ai-gateway/mlflow/v1/chat/completions`,
  `system.ai.gpt-oss-120b`) because the classic `databricks-*` endpoints are disabled on the training
  workspace; if the chat model changes, edit `CHAT_MODEL` in Step 6.
```
`<QUICK>`, `<ALL6>`, `<N>` are filled with the numbers measured in Step 2 — not left as placeholders.

- [ ] **Step 5: Build the site**

Run: `source .venv/bin/activate && mkdocs build --strict`
Expected: `Documentation built`, no WARNING lines.

- [ ] **Step 6: Commit and push**

```bash
git add notebooks/rag_from_scratch.py docs/labs/extra-rag-from-scratch.md mkdocs.yml docs/index.md docs/trainer-notes.md design/
git commit -m "RAG-from-scratch demo notebook and optional guide page"
git push remote develop
```
