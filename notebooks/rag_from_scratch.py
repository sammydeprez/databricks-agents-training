# Databricks notebook source
# MAGIC %md
# MAGIC # RAG from scratch
# MAGIC In Lab 4 you gave Knowledge Assistant six PDFs and it answered questions about them. This notebook
# MAGIC does the same job **by hand, one visible step at a time**, using only built-in AI functions in SQL:
# MAGIC
# MAGIC 1. **Extract** — read the text, tables and figures out of each PDF (`ai_parse_document`)
# MAGIC 2. **Clean** — keep the content, drop page headers, footers and figures
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
# MAGIC **Documents:** *Quick* uses two short regulations and runs end to end in about 2 minutes — good for
# MAGIC a live demo. *All 6* parses everything, including the 248-page IAEA glossary, in about 4–5 minutes.

# COMMAND ----------

dbutils.widgets.text("catalog", "", "Catalog (leave empty unless your trainer gives you one)")
dbutils.widgets.dropdown("documents", "Quick (2 small PDFs)", ["Quick (2 small PDFs)", "All 6 PDFs"], "Documents")

# COMMAND ----------

import json, re

CATALOG = dbutils.widgets.get("catalog").strip() or spark.sql("SELECT current_catalog() AS c").first()["c"]
if CATALOG == "hive_metastore":
    raise Exception("Your workspace's default catalog is hive_metastore, which can't hold the lab data. "
                    "Ask your trainer for a catalog name and type it into the 'catalog' box at the top.")
user_email = spark.sql("SELECT current_user() AS u").first()["u"]
SCHEMA_NAME = re.sub(r"[^a-z0-9_]", "_", user_email.split("@")[0].lower())

DOCS = f"/Volumes/{CATALOG}/{SCHEMA_NAME}/docs"
QUICK = ["FANR-REG-12.pdf", "FANR-REG-17.pdf"]  # emergency preparedness (20 pages), operator certification (14 pages)
try:
    available = sorted(f.name for f in dbutils.fs.ls(DOCS) if f.name.endswith(".pdf"))
except Exception:
    available = []
if not available:
    raise Exception(f"No PDFs found in {DOCS}. Run the lab_data notebook first (Set up my data), then come back.")
SELECTED = [n for n in QUICK if n in available] if dbutils.widgets.get("documents").startswith("Quick") else available

spark.sql(f"USE CATALOG `{CATALOG}`")
spark.sql(f"USE SCHEMA `{SCHEMA_NAME}`")
print(f"Working in {CATALOG}.{SCHEMA_NAME}")
print(f"Documents to process ({len(SELECTED)}):")
for n in SELECTED:
    print("  -", n)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Extract: what's actually inside a PDF?
# MAGIC A PDF is a picture of a page, not a list of sentences. `ai_parse_document` looks at each page and
# MAGIC returns its **elements**: titles, paragraphs, tables, figures, page headers and footers — each with
# MAGIC its type, its text, and where on which page it sits. Figures even get a written description.
# MAGIC
# MAGIC We store the raw result once in `rag_parsed`, so the slow part never has to run twice.
# MAGIC
# MAGIC Run this cell twice and the element counts can differ a little, or a block that was "text" comes
# MAGIC back as a "table". The parser is an AI model reading the page, not a fixed set of rules.

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

# COMMAND ----------

# Check: one parsed row per selected document, no parse errors, and every document has elements.
rows = spark.sql("""SELECT doc_name, size(cast(parsed:document:elements AS ARRAY<VARIANT>)) AS n,
                           cast(parsed:error_status AS STRING) AS err FROM rag_parsed""").collect()
assert sorted(r.doc_name for r in rows) == sorted(SELECTED), f"expected {SELECTED}, got {[r.doc_name for r in rows]}"
assert all(r.n and r.n > 0 for r in rows), "a document came back with no elements"
assert all(r.err in (None, "null", "[]") for r in rows), f"parse errors: {[(r.doc_name, r.err) for r in rows]}"
print("Extract OK")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Clean: keep the content, drop the furniture
# MAGIC Every page repeats the same header, footer and page number. If we kept them, half our search
# MAGIC results would be "Federal Authority for Nuclear Regulation — page 7". So we flatten the elements
# MAGIC into one row each, and mark what to keep. Figures are dropped too — including the written
# MAGIC descriptions you saw above, which is a real loss for diagrams; Knowledge Assistant can keep them.
# MAGIC Tables come back as HTML (`<table><tr>…`): we keep
# MAGIC them as they are — the embedding model reads the words fine, and the structure helps the chat
# MAGIC model later.

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
# MAGIC -- How big are the chunks? Most should be close to 1,000 characters. A very long table or
# MAGIC -- paragraph makes one bigger chunk, sometimes carrying the next few short elements with it.
# MAGIC SELECT doc_name, count(*) AS chunks,
# MAGIC        min(length(text)) AS shortest, cast(avg(length(text)) AS INT) AS average, max(length(text)) AS longest
# MAGIC FROM rag_chunks
# MAGIC GROUP BY doc_name
# MAGIC ORDER BY doc_name

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Three chunks of running text. Look at where each one starts and stops: would you have cut it there?
# MAGIC SELECT chunk_id, first_page, last_page, length(text) AS chars,
# MAGIC        left(text, 120) AS starts_with, right(text, 120) AS ends_with, text
# MAGIC FROM rag_chunks
# MAGIC WHERE text NOT LIKE '<table%'
# MAGIC ORDER BY chunk_id
# MAGIC LIMIT 3 OFFSET 2

# COMMAND ----------

# Check: nothing kept was lost on the way into chunks, and chunk sizes are sensible.
kept = spark.sql("SELECT count(*) AS n FROM rag_elements WHERE kept").first().n
in_chunks = spark.sql("SELECT sum(elements) AS n FROM rag_chunks").first().n
assert kept == in_chunks, f"{kept} kept elements but {in_chunks} in chunks"
avg_len = spark.sql("SELECT avg(length(text)) AS a FROM rag_chunks").first().a
assert 500 < avg_len < 2500, f"average chunk length {avg_len} looks wrong"
print(f"Chunk OK: {in_chunks} elements in {spark.table('rag_chunks').count()} chunks, average {int(avg_len)} characters")

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
# MAGIC -- sentence 1 but means something else. Which pair scores highest — and does sharing "drill"
# MAGIC -- make sentence 4 any closer to sentence 1 than the unrelated sentence 3?
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

# COMMAND ----------

# Check: every chunk has a 1,024-number embedding, and cosine_sim behaves.
bad = spark.sql("SELECT count(*) AS n FROM rag_index WHERE embedding IS NULL OR size(embedding) <> 1024").first().n
assert bad == 0, f"{bad} chunk(s) without a proper embedding"
assert spark.table("rag_index").count() == spark.table("rag_chunks").count()
same = spark.sql("SELECT cosine_sim(array(1F, 2F, 3F), array(1F, 2F, 3F)) AS s").first().s
assert abs(same - 1.0) < 1e-6, same
print("Embed OK")

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

# COMMAND ----------

# Check: the emergency-exercise question finds the emergency regulation first.
top = spark.sql("SELECT doc_name FROM search_regulations('How often must the operator run emergency exercises?')").collect()
assert len(top) == 5, f"expected 5 results, got {len(top)}"
assert top[0].doc_name == "FANR-REG-12.pdf", f"top hit was {top[0].doc_name}"
print("Search OK")

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
          "If the passages don't contain the answer, say you couldn't find it in the documents. "
          "After two searches that find nothing relevant, stop searching and say so.")


def search_regulations(question):
    rows = spark.sql(
        "SELECT doc_name, first_page, last_page, round(score, 3) AS score, text FROM search_regulations(:q)",
        args={"q": question},
    ).collect()
    return [r.asDict() for r in rows]


def tool_question(call, fallback):
    """The question the model wants to search for; falls back to the user's question if the arguments are broken."""
    try:
        args = json.loads(call["function"].get("arguments") or "{}")
    except (ValueError, TypeError):
        return fallback
    return args.get("question", fallback) if isinstance(args, dict) else fallback


def text_of(message):
    content = message.get("content")
    if isinstance(content, str):
        return content
    parts = content or []
    return "\n".join(p.get("text", "") for p in parts if p.get("type") in ("text", "output_text"))


def ask(question, max_rounds=4):
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    print(f"USER: {question}\n")
    for round_no in range(max_rounds):
        body = {"model": CHAT_MODEL, "messages": messages, "tools": TOOLS, "max_tokens": 4000}
        if round_no == max_rounds - 1:   # last round: take the tool away, so the model has to answer
            messages.append({"role": "user", "content": "Stop searching. Answer now from the passages above, with citations."})
            body = {"model": CHAT_MODEL, "messages": messages, "max_tokens": 4000}
        try:
            reply = w.api_client.do("POST", "/ai-gateway/mlflow/v1/chat/completions", body=body)
        except Exception as e:
            print(f"The model call failed: {e}\nCheck that CHAT_MODEL = {CHAT_MODEL!r} exists in Unity Gateway "
                  "(AI/ML > AI Gateway) and change it in the cell above if not.")
            return ""
        message = reply["choices"][0]["message"]
        calls = message.get("tool_calls") or []
        if not calls:
            answer = text_of(message)
            if not answer.strip():
                kinds = [p.get("type") for p in message.get("content") or []] if isinstance(message.get("content"), list) else type(message.get("content")).__name__
                print(f"(empty answer: content parts {kinds}, finish_reason {reply['choices'][0].get('finish_reason')})")
            print("ASSISTANT:\n" + answer)
            return answer
        messages.append({"role": "assistant", "content": text_of(message), "tool_calls": calls})
        for call in calls:
            query = tool_question(call, question)
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
# MAGIC Read that answer slowly. Every claim should end with a (document, page). Which sentences don't
# MAGIC have one? Those are the model filling gaps from its own training, not from the regulation — even
# MAGIC when it says everything was taken from the documents. Citations are what let you catch this, which
# MAGIC is why Knowledge Assistant shows them next to every answer.

# COMMAND ----------

# MAGIC %md
# MAGIC A question the documents can't answer. A good agent says so instead of guessing.

# COMMAND ----------

answer_3 = ask("What is the speed limit for vehicles on the plant site?")

# COMMAND ----------

# Check: answers came back, the first one cites the emergency regulation, the third admits it didn't find it.
plain = lambda t: t.replace("\u2011", "-").replace("\u2010", "-").replace("\u2019", "'")  # models like fancy hyphens
answer_1, answer_3 = plain(answer_1), plain(answer_3)
assert answer_1 and "REG-12" in answer_1, "answer 1 should cite FANR-REG-12"
assert answer_2, "answer 2 is empty"
assert any(w_ in answer_3.lower() for w_ in ("couldn't find", "could not find", "not found", "no information", "not contain", "does not")), \
    "answer 3 should say the documents don't cover it"
for broken in ("", "not json", '"just a string"', "[1, 2]", None):
    assert tool_question({"id": "x", "function": {"arguments": broken}}, "q") == "q", broken
print("Agent OK")

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
