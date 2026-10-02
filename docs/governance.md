# Governance, evaluation and cost

Before you build anything else today, agree on how you'll judge it. An AI draft is not a finished
output — a person still checks it before it goes anywhere. Take the Annual Operating Report (AOR) as
the running example: whoever in the room writes it today, an AI-drafted version is never final without
them signing off on it. That's the pattern for every agent you build over the next two days, not a
special rule for one of them.

## Before an agent goes live, someone must be able to answer

Work through these four questions as a group, against the agents you've already built (Lab 1's tool,
Lab 2's Genie Agent) and the ones still to come:

- **Which data can it see, and who decided that?** A wrong KPI number and a wrong action item owner
  fail differently — name what "right" means for each agent before you trust its output.
- **How do we know it's right, and how often do we check?** Where exactly does a person read the output
  before it reaches a decision or goes out the door? You'll be asked this again on the capstone canvas —
  start thinking about it now.
- **What does it cost per month, and what stops it running away?** Each AI Function or agent call costs
  tokens. At what volume does "cheap per call" become a real budget line, and who notices if it
  spikes?
- **Who is accountable when it's wrong?** Not the model — a person. Each new agent needs an owner and a
  permissions decision: who can run it, who can see its output.

Keep these four questions in mind through Lab 3 and Lab 3b today, and through Lab 4 and Lab 5 tomorrow — every
agent you touch from here gets judged by the same standard, not a new one each time.
