# Capstone and use case canvas

The governance, evaluation and cost discussion ran on Thursday — see
[Governance, evaluation and cost](governance.md) — keep those four questions in mind throughout.

## Pick your case

Three cases, chosen from what came up most in the pre-course survey. Pick one as a team, or bring your
own idea if you have a specific use case in mind. None of these need a new agent built from scratch —
you're extending what you already built in the labs with one more data source, and asking it one good
question.

- **Meeting assistant** — re-run or extend Lab 3's `ai_extract` pattern (Step 4) over
  `your_catalog.your_schema.meeting_transcripts`, or point your Lab 3b Genie Code skill at a transcript it
  hasn't seen.
- **KPI and annual operating report** — open your Lab 2 Genie Agent, add
  `your_catalog.your_schema.monthly_kpis` as an extra source (**Configure > Sources**), and ask a KPI
  question. If you have time, try `ai_query` drafting a sentence of the report from the answer. A human
  reviews and signs off before it's final — same pattern as the governance discussion.
- **Memo and approval helper** — open your Lab 4 Knowledge Assistant and check whether it can already
  answer from the `memo_templates` folder your team added as a source on Thursday (see the warning
  below). Ask "what's the process for X" and see what it drafts.

!!! warning "The memo helper needed a head start"
    A Knowledge Assistant source needs hours to sync. If your team picked **Memo and approval helper**,
    this only works because you added `memo_templates` as a source on your Lab 4 Knowledge Assistant at
    the end of Thursday — see [Trainer notes](trainer-notes.md). If you didn't, pick a different case;
    there isn't time this morning for a first sync.

## Brainstorm

If your case doesn't fit one of the three above:

1. **Alone, 5 min.** Write one sticky note per task in your department that is slow, repetitive, or document heavy. One task per note.
2. **Team, 10 min.** Cluster similar notes. Give each cluster a name.
3. **Team, 8 min.** Place each cluster on the wall grid: value (up) against feasibility (right). Anything touching plant control, safety classified information or personal data goes in the **needs approval first** column, whatever its value.
4. **Team, 7 min.** Pick one cluster from the top right. Fill in the canvas below.

## Demo without a build

No new build today — demo with the agents you already have from the labs, pointed at your use case.
One question and one good answer is enough. If your idea doesn't map to an existing lab agent at all,
describe on the canvas below what you'd build next, rather than trying to build it now.

## Pitch to your manager (3 min per team)

1. The problem, in one sentence, with who has it and how often.
2. Live demo with a lab agent, one question, one answer.
3. The value: time, errors or risk reduced.
4. One risk and how you would control it.
5. The first step you are asking for, and who approves it.

Peers play the manager and ask one hard question.

## The one-page use case canvas

Copy this into a doc, or use the printed A4 version.

| The problem | The solution | The ask |
|---|---|---|
| Who has this problem, and how often? | Which tool fits: Genie Agent, Knowledge Assistant, AI Functions, Supervisor Agent? | How will success be measured? |
| What does it cost today in time, delay or errors? | What data does it need, and what is its classification? | What is the main risk and how is it controlled? |
| What would "good" look like? | Where does a human check the output? | What is the smallest first step, and who must approve it? |

## Clean up

Before you leave, remove what you built today:

1. Open the **Agents** page and delete every agent you created (Genie Agent, Knowledge Assistant, Supervisor Agent) — `⋮` next to each, then **Delete**.
2. Open the **lab_data** notebook you imported in [Before you start](setup.md), change the setting to **Clean up my data**, and click **Run all**. It removes your schema and everything in it.
