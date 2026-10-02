# Extra: build RAG by hand

**Goal:** see every step Knowledge Assistant hides — extract, chunk, embed, search, agent — by running them yourself in SQL.
**Code written:** none — you run a notebook and read its output.

Your trainer will demo this. If you want to run it yourself afterwards:

1. Make sure you've run the **lab_data** notebook (see [Before you start](../setup.md)).
2. In **Workspace**, click **⋮ > Import**, choose **URL**, and paste:

    ```text
    https://raw.githubusercontent.com/sammydeprez/databricks-agents-training/develop/notebooks/rag_from_scratch.py
    ```

3. Open **rag_from_scratch**, keep **Documents** on **Quick**, and click **Run all**. It takes about 2 minutes.
   If the Settings cell stops with "No PDFs found", type the same catalog you used for lab_data into the
   **Catalog** box at the top and click **Run all** again.

## What to look at

| Step | Look at | Ask yourself |
|---|---|---|
| 1. Extract | The element types on page 5 | What did the parser think was a heading, a table, a figure? |
| 2. Clean | The kept / dropped table | What would search results look like if we kept the footers? |
| 3. Chunk | The three sample chunks, `starts_with` and `ends_with` | Where would you have cut instead? |
| 4. Embed | The four-sentence similarity grid | Why does "drill bit" score no closer to "emergency drills" than an unrelated sentence, despite sharing a word? |
| 5. Search | The two example searches | Is the top passage the one you'd have picked? |
| 6. Agent | The `MODEL ASKS:` lines and the answers | When did it search more than once? Which sentences in answer 2 have no citation? What did it say when the answer wasn't there? |

!!! note "Why not a Vector Search endpoint?"
    A real system would put the vectors in a Mosaic AI Vector Search index. The notebook compares the
    question with every chunk in plain SQL instead — fine for a few thousand chunks, no extra cost, and
    every line readable. Step 5 in the notebook explains what an endpoint would add.

**Check yourself**

- [ ] Which step would you change first if answers kept citing the wrong page?
- [ ] What did Knowledge Assistant do for you in Lab 4 that you had to do by hand here?
- [ ] Run it twice. Did the number of elements change? What does that tell you about `ai_parse_document`?

Everything the notebook creates lives in your own schema, so the lab_data **Clean up my data** step
removes it at the end of the training.
