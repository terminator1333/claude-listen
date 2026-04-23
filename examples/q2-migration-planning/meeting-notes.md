# Meeting notes — Q2 migration planning

*Recorded 2026-04-15 · 45 min · Audio: `q2-migration-planning.m4a`*
*Attendees: Alice, Bob, Charlie*

## Summary

Working session to scope the Q2 database migration. The group settled on a phased rollout plan (shadow writes → dual-write → cutover) instead of a big-bang, and identified the schema-validation step as the critical-path risk. Two weeks to deliver.

## Decisions

- **Phased cutover, not big-bang** (Bob's proposal, all agreed). Three phases: shadow writes for initial validation, dual-write for a week with zero divergence, then cutover. Rationale: big-bang has no rollback path in the 2-week window.
- **Schema validation runs on every commit, not nightly** (Alice). Rationale: nightly catches problems too late given the deadline.
- **No rollback path from phase 2 → phase 1** (tentative, Alice). Shadow-write volume is small enough to replay if dual-write diverges.

## Action items

- **Bob** — draft the phase-1 shadow-write code by Monday.
- **Charlie** — set up schema-validation CI step this week, running on every commit.
- **Alice** — follow up with the platform team on connection-pool limits. Came up on the thread last week but wasn't closed.

## Open questions

- Do we need an explicit rollback from dual-write back to shadow-writes, or can we rely on replay? Alice's tentative answer is replay; Charlie noting as an open question in the migration doc.

## Technical discussion

### Why phased over big-bang

Bob: "Big-bang scares me given the 2-week window. If anything goes wrong during cutover we have no rollback path that doesn't involve restoring from backup, which is a six-hour operation."

Three phases:
1. **Shadow writes** — read traffic stays on old DB, writes are mirrored fire-and-forget to the new schema. Failures are logged, not retried. Purpose: exercise the new schema against production write volume.
2. **Dual-write** — both DBs receive writes, reads still served from old. Look for divergence.
3. **Cutover** — after one clean week of dual-write, flip reads to the new DB.

### Schema validation

Charlie: needs to be "airtight" before shadow writes begin, otherwise constraint violations surface at cutover time. Alice and Bob agreed per-commit is worth the setup cost.

## Flagged for follow-up

- Connection-pool limits conversation with the platform team is still open from a previous thread — Alice to drive.
- Rollback-from-phase-2 question tabled but should have a documented answer before shadow writes start, since it affects how much state phase 2 is allowed to accumulate.
