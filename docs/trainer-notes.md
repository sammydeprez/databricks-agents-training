# Trainer notes

## One week before

- [ ] Confirm whose workspace. If it is the client's, check the region supports Knowledge Assistant, Supervisor Agent, AI Functions and pay-per-token models (Databricks page "Features with limited regional availability"). Have a backup workspace in a supported region.
- [ ] **Confirm Knowledge Assistant and Supervisor Agent are actually enabled — on a paid workspace too, not just trial.** Both fail immediately with "... is not available. To access this feature, please
      contact sales for assistance." on trial workspaces, which is the well-known case. But this is a
      separate Agent Bricks entitlement from the plan tier: a brand-new **paid** Azure workspace hit the
      identical error in testing, unaffected by any workspace admin setting (including the "Enforce Unity
      Gateway" toggle below). If you hit this, it needs your Databricks account team to enable Agent
      Bricks specifically — ask well before Day 1, since it isn't self-service. Genie Agent (Lab 2) and
      AI Functions (Lab 3) aren't affected either way. Test by actually creating one of each agent type
      once, don't just check the plan name.
- [ ] Open **Playground** and confirm you can get a real chat response back, not a hang or a
      `PERMISSION_DENIED` error — that's what Lab 1 Part A needs. Two independent failure modes seen in
      testing, both on a paid workspace:
    - The Playground page itself can hang on model-list loading the very first time it's opened after
      the workspace is created; reloading a minute or two later fixed it without any config change.
    - A model can load and be selectable but still return `PERMISSION_DENIED: The endpoint is
      temporarily disabled due to a Databricks-set rate limit of 0` on every prompt — seen consistently
      with the Claude models (Claude Fable/Opus/Sonnet 5.x) while Llama and GPT OSS models on the same
      workspace worked fine. If Claude is rate-limited like this, switch the trainee-facing guidance to
      a Llama or GPT OSS model instead (see the Unity Gateway naming note below) rather than trying to
      fix the rate limit — it did not respond to the "Enforce Unity Gateway" toggle in testing and looks
      like a platform-side limit, not a workspace setting.
- [ ] **Run Lab 3b end to end in the training workspace, both parts.** Verified on 1 October 2026:
      Genie Code no longer has an Agent/Chat mode — the selector at the bottom of the panel is now
      **Effort: Auto / Low**, and it's agentic either way. On that workspace **Auto** failed with "This
      workspace has no daily token allowance for the assistant" while **Low** worked for both parts
      (capture the minutes skill; hand-write `maintenance-sql`, which changed the overdue count from 624
      to 532 and added its fingerprint line). If Auto works on the day, participants can use it; if
      even Low fails, drop Lab 3b and use the 50 minutes as a longer break. Two things to say out loud:
      every **new chat** resets the effort to Auto, and Genie Code can't start a stopped
      `training-warehouse` — someone has to run a query in the SQL editor first.
- [ ] Serverless compute, a serverless SQL warehouse named `training-warehouse`, and a serverless usage policy with a nonzero budget.
- [ ] Participant accounts with rights to create agents and use Model Serving.
- [ ] **Decide which catalog participants use, and make sure they can create a schema in it.** The
      **lab_data** notebook has a **Catalog** box: left empty it uses the workspace's default catalog
      (`SELECT current_catalog()` in the SQL editor shows which one — often named after the
      workspace); filled in, it uses that catalog. If the default catalog works, participants type
      nothing. If not, pick or create one and tell everyone its name on Day 1. Either way, grant once:

    ```sql
    GRANT USE CATALOG, CREATE SCHEMA ON CATALOG <catalog> TO `account users`;
    ```

    Swap `` `account users` `` for a specific group if you don't want to grant this to everyone in the
    account. A participant who typed a catalog for setup must type the same one again for cleanup on
    Day 2. A default catalog of `hive_metastore` won't work — the notebook stops and asks for a name.
    That's the only prep needed — participants import the **lab_data** notebook straight from GitHub
    themselves, and it comes with its own copy of the Lab 4 PDFs bundled in, see
    [Before you start](setup.md).
- [ ] Build and sync the backup Knowledge Assistant.
- [ ] Run every lab end to end in the exact workspace and fix any menu names that changed.
- [ ] Send the guide URL to the client and ask them to open it on a corporate laptop.
- [ ] Print the use case canvas, one per team, plus sticky notes and markers.

## Day 1 (Thursday)

Thursday opens with theory (how LLMs work, embeddings, tool calling, RAG, agents) before the first
lab — see the slide deck for that material, not covered in this guide. After lunch the order is Lab 1,
Lab 2, Governance, Lab 3, Lab 3b, then Lab 4 Part A and the capstone-case vote.

Lab 4 Part A and the capstone-case vote have to be last, since the overnight sync is the whole reason
for doing them today. If Lab 3b's pre-Day-1 check fails (see the checklist item above), skip it and use
the time as a longer break instead.

- Open with the survey results, not the agenda. Say out loud: "You told us you want to build agents —
  that's exactly what these two days are: five agents, end to end." Ask who in the room writes the
  Annual Operating Report (AOR); it comes back in the capstone case list. This costs two minutes and
  directly answers their top wish, which the course already delivers but they don't yet know that.
- Start the day with the data rule on screen.
- Databricks basics: a quick check that everyone can find **SQL Editor**, **Genie**, **Agents** and
  **Playground** (see [Before you start](setup.md)) — skip the full navigation tour.
- Lab 1's "writing agent instructions" block (Part A) is the direct answer to "how do I write the
  rules," which came up explicitly in the pre-course survey. Call that out by name when you get there.
  The same instruction pattern — role, rules, tone, what to refuse — recurs in Lab 2 (Genie Agent
  instructions) and Lab 4 (Knowledge Assistant instructions); point that continuity out each time so it
  reads as one skill, not three unrelated ones.
- Lab 4 Part A (create the Knowledge Assistant) must run at the end of Day 1 regardless of what happens
  in the capstone — the first document sync takes hours. See the warning in
  [Lab 4](labs/lab4-knowledge-assistant.md).
- End of day: teams vote on their Friday capstone case (see [Capstone](capstone.md)) right after
  building their Lab 4 Knowledge Assistant. Any team choosing **Memo and approval helper** adds
  `memo_templates` as a second source on that same Knowledge Assistant, right now, so it syncs alongside
  the regulations overnight — there is no time for a first sync on Friday morning. Teams doing the other
  two cases don't need to do anything extra tonight.

## Day 2 (Friday)

- Labs 4 and 5 are back to back; skip stretch tasks if a lab overruns.
- Time the pitches strictly: three minutes plus one question.
- End of Day 2, before people leave: each participant deletes the agents they created (Genie Agent,
  Knowledge Assistant, Supervisor Agent) from the **Agents** page, then reopens their **lab_data**
  notebook, switches it to **Clean up my data**, and runs it to drop their schema. Two minutes — see the
  **Clean up** step at the end of the capstone page.

## Known snags

- **RAG-from-scratch demo** (`notebooks/rag_from_scratch.py`, guide page [Extra: build RAG by hand](labs/extra-rag-from-scratch.md)).
  Measured on serverless on 1 October 2026: **Quick** (FANR-REG-12 and -17) runs end to end in about
  2 minutes; **All 6** in about 4 minutes (3,700 elements, ~795 chunks). Good moment to demo it: right
  after Lab 4 Part B, while the Knowledge Assistant's answers are fresh. It calls models through Unity
  Gateway (`/ai-gateway/mlflow/v1/chat/completions`, `system.ai.gpt-oss-120b`, embeddings
  `system.ai.gte-large-en`) because the classic `databricks-*` endpoints are disabled on the training
  workspace; if the chat model changes, edit `CHAT_MODEL` in Step 6. `ai_parse_document` is not
  deterministic — element and chunk counts shift a little between runs; say so before someone asks.
  Answer 2 usually contains at least one uncited sentence: that's the point of the cell after it.

- Playground tool calls need serverless enabled and USE CATALOG, USE SCHEMA and EXECUTE on the function.
- GPT OSS 120B can throw an `InternalError` ("reasonPhrase contains one of the following prohibited
  characters") on some Lab 1 Part C tool-calling prompts. It's the model endpoint, not the lab steps —
  switch to a different **Tools enabled** model (Meta Llama 3.3 70B Instruct worked in testing) and
  retry.
- Newer workspaces route pay-per-token models through **Unity Gateway** (left navigation, under AI/ML)
  instead of the classic **Serving** page — Serving may show "No endpoints found" even though models
  work fine. Model names also change: the old `databricks-<model>` form (e.g.
  `databricks-meta-llama-3-3-70b-instruct`) can start failing in `ai_query` with "Endpoint ... does not
  exist" or "is disabled for this workspace, use Unity Gateway", once an admin turns on **Settings >
  Workspace admin > Advanced > Enforce Unity Gateway**. The fix is the fully-qualified name shown on the
  model's page under **AI Gateway > Models**, e.g. `system.ai.meta-llama-3-3-70b-instruct` (no
  `databricks-` prefix). Playground's own model picker can also lag behind Unity Gateway — a model
  listed there under **AI Gateway** may not appear in Playground's "Select an endpoint" search at all;
  opening that model's page and clicking **Chat in playground** works around it.
- AI Functions fail on Classic or Pro SQL warehouses.
- `ai_translate` handled Arabic fine both ways (Arabic→English and English→Arabic) in testing on this
  release — an earlier version of this guide said otherwise. If a participant hits a real translation
  gap for some other language, that's worth reporting, not assuming.
- A fresh trial workspace shows an empty Playground until pay-per-token models are enabled or an
  external model is connected — don't mistake this for the model-list hang above; check entitlements
  first on a trial workspace specifically.
- Knowledge Assistant skips files over 100 MB or 500 pages.
- Genie Code (the assistant behind Lab 3b) hit a genuinely broken state once during testing — the panel
  stuck on "Loading" indefinitely, with console errors climbing into the hundreds, across a fresh
  browser tab and a full page reload, resolving only after a longer wait. Unclear if this was a one-off
  outage or a repeatable issue; that's exactly why Lab 3b needs the live pre-Day-1 check above rather
  than being trusted on this description alone.
- Lab 3b Part B: **Create > File** in the workspace makes `New File <date>.py` immediately, with no
  name prompt. Participants rename it by double-clicking the name in the editor tab. A skill file that
  stays `.py` is never loaded — the first thing to check when "my skill does nothing".
- The **lab_data** notebook needs outbound internet access to clone the repo from GitHub. Earlier
  versions also fetched the Lab 4 PDFs live from fanr.gov.ae/iaea.org, which failed with `Temporary
  failure in name resolution` on serverless compute (its network policy commonly allows GitHub/PyPI but
  blocks arbitrary external sites) — the PDFs now ship inside the repo itself, so that specific failure
  is gone. If the GitHub clone itself fails, the workspace's network policy is blocking GitHub too, and
  that needs an admin to allow-list it (or run on a classic cluster, which usually has normal internet
  access).
