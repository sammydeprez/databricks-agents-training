# Lab 3b: Teach Genie Code a skill

**Goal:** capture a repeatable task as a reusable instruction file — first by letting Genie Code write it, then by writing one yourself — so "write the rules once, AI follows them every time" becomes something you've done, not just heard.
**Code written:** none — one markdown file, in plain English.

Skills extend Genie Code — the AI assistant built into notebooks and the SQL editor — with
domain-specific instructions, saved as a markdown file called `SKILL.md` that follows the open Agent
Skills standard: a name, a description of when to use it, and the instructions themselves. This is the
same "write the rules once" idea as Lab 1's instructions block, Lab 2's Genie Agent instructions, and
Lab 4's Knowledge Assistant instructions — except now you're writing the rules into a reusable file for
your own coding assistant, instead of a one-off configuration screen for an agent someone else will use.

!!! warning "Before you start"
    - **Start your warehouse first.** Open **SQL Editor**, run `SELECT 1`, and click **Start, attach and run** if asked. Genie Code can't start a stopped warehouse on its own — it just reports that the query failed.
    - **Set the effort to Low.** At the bottom of the Genie Code panel, change **Auto** to **Low**. Every **new chat** resets it to Auto, so check it each time. Your trainer will say if Auto works in today's workspace.

## Part A: let Genie Code write the skill

### Step 1: do the task once

1. Open the **SQL Editor** and click the **Genie Code** icon (top right).
2. Ask it to turn a transcript into minutes, using one row from a table the setup notebook already
   loaded for you (the same task you just did in SQL with `ai_extract` in Lab 3, Step 4):

    ```text
    Turn this transcript into meeting minutes: one line per action item, with the owner and due date.

    SELECT transcript FROM your_catalog.your_schema.meeting_transcripts WHERE transcript_id = 'MT-01';
    ```

3. Let it run the query and produce the minutes. If it asks to change your open query, click
   **Accept**. Read the result — does it match what you'd write by hand?

### Step 2: capture it as a skill

1. In the same chat, tell Genie Code:

    ```text
    Capture this as a skill I can reuse on other transcripts.
    ```

2. Genie Code proposes a new file. Click **Accept all** to save it.
3. Open it: **Workspace > Home > .assistant > skills > meeting-minutes > SKILL.md**. Read it end to
   end — you'll write one of these yourself in Part B, so look at its shape:
    - a block at the top between two `---` lines, with a **name** and a **description**
    - the instructions underneath, in ordinary markdown

**Check yourself**

- [ ] Does the description explain *when* to use the skill, specifically enough that a colleague who's never seen this task would know to reach for it?
- [ ] Is anything in the instructions vague enough that two people could follow it and get different results?

## Part B: write a skill by hand and test it

Now the other way round: you write the rules, Genie Code follows them. The skill is the house rules for
SQL on the maintenance tables — the same rules you gave the Genie Agent in Lab 2, but this time for your
own coding assistant.

### Step 3: get a baseline, without a skill

1. In the Genie Code panel, click **New chat** (pencil icon, top of the panel) and set the effort to **Low** again.
2. Ask:

    ```text
    Show overdue work orders per unit from your_catalog.your_schema.work_orders
    ```

3. Note the total and look at the SQL it put in the editor. Write down how it decided what "overdue"
   means. Don't accept the change to your query.

### Step 4: write the skill

1. Open **Workspace > Home > .assistant > skills**. Click **Create > Folder** and name it `maintenance-sql`.
2. Open the new folder and click **Create > File**. It opens straight away as `New File <date>.py`.
   Double-click that name in the tab at the top and rename it to `SKILL.md`.
3. Paste this, replace `your_catalog` and `your_schema` with your own names everywhere, and **finish the description
   yourself** — it decides when Genie Code reaches for this skill, so it's the most important line in
   the file:

    ```markdown
    ---
    name: maintenance-sql
    description: House rules for writing SQL against the maintenance tables (work_orders, assets, technicians) in your_catalog.your_schema. Use this skill whenever a question is about ...
    ---

    # Maintenance SQL conventions

    1. Always use full table names: your_catalog.your_schema.work_orders, your_catalog.your_schema.assets, your_catalog.your_schema.technicians.
    2. "Overdue" means status = 'Open' AND due_date < current_date(). Nothing else counts as overdue.
    3. Exclude work orders with status 'Cancelled' unless the question explicitly asks about cancelled work.
    4. Units are named exactly 'Unit 1' to 'Unit 4'. Always list them in that order (ORDER BY unit), never sorted by count.
    5. When listing individual work orders, always show wo_id as the first column.
    6. Under every answer, add one line: "Overdue = status Open and due_date before today."
    ```

    The file saves automatically. The right-hand pane shows a preview of the markdown.

Rule 6 is there on purpose: it's a visible fingerprint, so you can tell at a glance whether Genie Code
used your skill.

### Step 5: test it

1. Back in the SQL Editor, click **New chat** in Genie Code, set the effort to **Low**, and ask the same question as in Step 3.
2. Compare with your baseline, rule by rule:
    - Did the fingerprint line appear under the answer?
    - Click the **Thoughts** line at the top of the answer. Does it mention loading `maintenance-sql`?
    - Did the total change? Read the `WHERE` clause — what does it count as overdue now?
    - Are the units in Unit 1 to Unit 4 order?
3. Now ask something your skill should **not** touch, in a new chat:

    ```text
    How many IT tickets in your_catalog.your_schema.it_tickets are there per requester team?
    ```

    Did the fingerprint line appear this time? It shouldn't — that's the description doing its job.

### Step 6: change one rule and re-test

1. Edit `SKILL.md`: change one rule or add one — for example, change the fingerprint line in rule 6 to
   something new, or add "Always include the priority column when listing work orders."
2. Start a **new chat** (the skill is read at the start of a chat) and ask:

    ```text
    List the 5 oldest overdue work orders in your_catalog.your_schema
    ```

3. Did your change show up? Is `wo_id` the first column?

**Check yourself**

- [ ] What changed between the baseline and the skill answer — the numbers, or only the wording? Which one would a manager notice first?
- [ ] How did you know the skill was used? Would a colleague who didn't write it know?
- [ ] Your skill and Lab 2's Genie Agent instructions say almost the same thing. Who is each one for — and which would you keep up to date when the definition of "overdue" changes?
- [ ] Who should own a skill file like this in a real department — the person who wrote it, or the team that owns the data?

## Stretch

- Make the description deliberately vague (for example, "Rules for SQL") and see whether Genie Code still picks the skill for the IT-ticket question. Then put the specific description back.
- Point the Part A skill at a completely different kind of text (an incident report from
  `your_catalog.your_schema.incident_reports`) and see how far the instructions generalise before they
  need editing.

---

The takeaway: you write the rules once, and Genie Code follows them every time after — the same
principle behind every "Instructions" panel in this course, just applied to your own coding assistant
instead of an agent you built for someone else.
