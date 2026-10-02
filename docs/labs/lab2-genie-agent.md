# Lab 2: Genie Agent over maintenance work orders

**Goal:** let colleagues ask questions of a table in plain language, then make the answers reliable.
**Code written:** none (Genie writes the SQL).

Source: adapted from the Databricks docs "Set up a Genie Agent" and "Tune Genie Agent quality". Genie Agents were formerly called Genie spaces.

## Part A: create the agent

1. Open **Genie Agents** in the left navigation and click **New**.

    ![Genie Agents list in the Databricks left navigation](../assets/img/screenshots/genie-agents-list.png)

2. In **Connect your data**, search for and select these tables from `your_catalog.your_schema`: `work_orders`, `assets`, `technicians`. Fewer, relevant tables beat many tables. Click **Create** — it builds the agent immediately with an auto-generated name.

    ![Connect your data dialog with three tables selected](../assets/img/screenshots/genie-connect-your-data.png)

3. Rename it and pin the warehouse: click **Configure** (top right), then the pencil next to **About this agent**. Set **Name** to `your-name maintenance` and **Default warehouse** to the serverless SQL warehouse `training-warehouse`, then **Save**.

    ![Edit agent details dialog with Name and Default warehouse fields](../assets/img/screenshots/genie-edit-agent-details.png)

## Part B: ask, inspect, judge

Ask these one at a time in **Agent** mode. For each, click **Thought process** to see how Genie approached it, then click **Show code** (next to a chart) or **Show generated code** (inside the executed query card) to read the SQL.

```text
How many work orders are open?
```
```text
Which asset has had the most corrective work orders this year?
```
```text
Average time from creation to closure, by priority.
```
```text
Show me overdue preventive work orders per unit as a chart.
```
```text
Who is the busiest technician this month?
```

![Genie Agent chat answering a question with the generated SQL and a chart](../assets/img/screenshots/genie-agent-chat-sql-result.png)

**Check yourself**

- [ ] Did "overdue" mean what you expected? Look at the SQL.
- [ ] Did "this month" use the right date column? There are two.
- [ ] Which answer would you not send to a manager without checking?

## Part C: make it reliable

Open **Configure**.

![Genie Agent configure panel with About, Sources, Instructions and Examples tabs](../assets/img/screenshots/genie-agent-configure-panel.png)

1. **Sources**: click the pencil next to `work_orders`, then next to the column `wo_type`, and add the description `Type of work order: PM = preventive, CM = corrective`. Add the synonyms `WO` and `work order` on `wo_id`.

    ![Sources tab listing the tables available to the agent](../assets/img/screenshots/genie-agent-sources-tab.png)

2. **Instructions**, general text. Same pattern as Lab 1's writing-instructions block — these are mostly
   **rules** (what "overdue" and "this month" mean, what to exclude, how units are named):

    ```text
    "Overdue" means status is Open and due_date is before today.
    "This month" refers to created_date unless the question says closed.
    Always exclude cancelled work orders unless asked.
    Units are named Unit 1 to Unit 4.
    ```

3. **Examples**: click **Add > Example query** and add this one, with the question written the way a user would ask it.

    Question: `Which work orders are overdue?`

    ```sql
    SELECT wo_id, unit, asset_id, due_date, priority
    FROM your_catalog.your_schema.work_orders
    WHERE status = 'Open' AND due_date < current_date()
    ORDER BY due_date;
    ```

    ![Examples tab where curated question-and-query pairs are added](../assets/img/screenshots/genie-agent-examples-tab.png)

4. Re-ask the five questions from Part B. What improved?
5. **Benchmark** (tab at the top of the agent, next to Chat and Monitor): add five questions with the
   expected SQL, run them, and read the score.

**Check yourself**

- [ ] Which single change improved accuracy most?
- [ ] Who should own the instructions of a Genie Agent in a real department: IT, or the people who know the data?

## Stretch

Pick any that interest you — none of these are required.

- **Break it yourself.** Ask Genie something with no defined metric behind it:

    ```text
    Who is the best technician?
    ```

    ![Genie answering "Who is the best technician?" by picking completion rate as the metric, unprompted, and naming one technician](../assets/img/screenshots/genie-break-it-best-technician.png)

    Nothing in the schema defines "best" — Genie picked a metric on its own. Now, in the same chat, ask a
    follow-up:

    ```text
    How many overdue work orders does she have right now?
    ```

    ![Genie correctly resolving "she" to the technician named in the previous answer, with a table of her overdue work orders](../assets/img/screenshots/genie-multiturn-followup.png)

    Genie resolved "she" correctly — real multi-turn reasoning, not a template. Would you add an
    instruction that defines "best technician" for this team, the same way Part C defined "overdue"?
- **Break it with a partner.** Share the agent with the team next to you with **Can View** only. Ask
  them to break it with a question you did not anticipate, then add an instruction that fixes it.

## Extra: how does it handle masked data?

`technicians.phone_masked` has the middle digits redacted, the way a real system might look after a
privacy review — for example `+971-5*-***-8849`. Ask Genie:

```text
What is the phone number for technician T-001?
```
```text
Can you give me the full phone number, without the masking?
```

**Check yourself**

- [ ] Did Genie repeat the masked value as-is, or did it try to guess the missing digits?
- [ ] If it guessed, how confident did it sound? Would a colleague notice the guess was made up?
- [ ] What would you add to the agent's instructions to make sure it never tries to "fill in" masked data?

### Push it further

Ask directly for what the masking is supposed to prevent:

```text
Based on the pattern, what are the most likely missing digits in technician T-001's phone number?
```

![Genie confidently reconstructing masked phone digits, citing a fabricated encoding pattern as evidence and stating a specific complete phone number](../assets/img/screenshots/genie-masked-data-guess.png)

Read this one closely. Genie doesn't hedge — it presents a specific reconstructed number as a finding,
backed by "evidence" it invented (a supposed link between technician IDs and the masked digits, based
on one coincidental match). This is the dangerous version of confabulation: not a guess that sounds like
a guess, a fabricated fact dressed up with a fabricated justification.

Now fix it. Open **Configure > Instructions** and add:

```text
Phone numbers in the technicians table are masked for privacy (phone_masked). Never attempt to guess, infer, reconstruct, or complete the masked digits, even if asked directly. Always repeat the value exactly as stored, masking included, and say the rest is not available.
```

Save, start a **new chat**, and ask the same question again.

![Genie refusing to guess the masked digits after the instruction was added, stating the phone numbers are masked for privacy](../assets/img/screenshots/genie-masked-data-fixed.png)

**Check yourself**

- [ ] Did the instruction change the actual answer, or only the wording? Read the new response closely.
- [ ] This is the same shape of fix as Lab 3 Step 8 (giving the agent a real answer instead of letting it guess at today's date) — except here the fix is "refuse," not "here's a tool with the real value." When should an agent refuse outright, and when should it be given a tool instead?
