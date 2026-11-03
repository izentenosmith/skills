# Roles — who commands, who touches production, who talks

Incidents go wrong in a recognizable way: everyone works the technical problem at once, several people change production without telling each other, nobody keeps the stakeholders informed, and nobody is sure who decides. The fix is a small, explicit separation of roles (*Site Reliability Engineering*, ch. 14). It costs a sentence to set up and saves the hour spent undoing two people's uncoordinated "fixes".

## The four roles

| Role | Holds | Does not |
|---|---|---|
| **Incident commander** | The overall picture and every decision. Assigns the other roles and keeps whatever isn't assigned. | Debug. The moment the commander is deep in a log file, nobody is commanding. |
| **Operations** | The **only** hands on production. Proposes and carries out containment, rollbacks, flag flips, repairs — each confirmed. | Act on anything not routed through the commander. |
| **Communications** | Stakeholder updates on a fixed cadence, each naming the time of the next one. | Speculate about cause in an update. |
| **Planning** | The log and its state block, the list of temporary changes, follow-up items, the next handoff. | Change production. |

**No freelancing.** Someone who spots a fix tells operations; they don't apply it. Two uncoordinated production changes make every later observation ambiguous — which change did that?

## Scaled to a small team, with an agent

Most incidents in a small team have one or two people. The roles still exist; they just double up:

- **The user is the incident commander** — every production action waits on their confirmation anyway.
- **The agent is planning, and drafts communications** — it keeps the log, the state block and the temporary-change list, drafts each stakeholder update with its next-update time, and proposes options. The user sends the updates.
- **Operations is whoever holds production access** — usually the user. When the agent runs a confirmed production command, it acts as operations for that one action only.

Write the assignment into the state block at declaration, even when one person holds three roles. When a second person joins, the first thing they read is who holds what.

## Handing off

Command, and any role, changes hands **only when the incoming person confirms they have it** — never by the outgoing person leaving. The same applies when an agent session ends with the incident open and another picks it up.

- [ ] The state block is current: status, roles, exit criteria, temporary changes, open questions, next update time.
- [ ] The outgoing holder says, in one message: what's happening, what's been tried, what's in flight, and what they would do next.
- [ ] The incoming holder acknowledges explicitly.
- [ ] A `handoff` entry is logged — `handoff · commander: <from> → <to>, acknowledged` — and announced wherever coordination happens.

## Asking for help

At each 30–60 minute checkpoint, the commander asks whether the incident needs more people or a different specialist. Pulling someone in early is cheap; an exhausted responder making a production change at hour four is not. Whoever made the most recent change to the affected system is usually the fastest source of context — ask them first.
