# Transcript

*Duration: 00:45:12 · Language: en*

### Alice [00:00:04]
Okay, so we're here to figure out the Q2 migration plan. I think the big open question is whether we do a big-bang cutover or phase it. Bob, you wanted to start?

### Bob [00:00:18]
Yeah. Big-bang scares me given the 2-week window. If anything goes wrong during cutover we have no rollback path that doesn't involve restoring from backup, which is a six-hour operation. So I'd like to propose a three-phase approach: shadow writes, then dual-write, then cutover after a week of clean dual-write.

### Alice [00:01:02]
What's the blast radius of shadow writes?

### Bob [00:01:05]
Zero. Read traffic still goes to the old DB. Shadow writes are fire-and-forget; if they fail we log and move on. The goal there is just to exercise the new schema against production write volume.

### Charlie [00:01:31]
I'm with Bob on this. But we need the schema-validation step to be airtight before we even start shadow writes, otherwise we're going to find constraint violations at the worst possible time.

### Alice [00:01:52]
Yeah. Charlie, can you own the validation CI?

### Charlie [00:01:56]
I can. One question — do we want this running on every commit, or nightly? Nightly is easier to stand up.

### Alice [00:02:08]
Every commit. Nightly catches things too late. We've got two weeks.

### Bob [00:02:15]
Agreed.

### Charlie [00:02:17]
Okay. Every commit it is.

### Alice [00:02:22]
Good. So Bob, you draft the phase-1 shadow-write code by Monday. Charlie, validation CI this week. I'll handle the platform-team conversation about connection-pool limits — that came up on the thread last week and I never followed up.

### Bob [00:02:40]
One thing — do we need a rollback from phase 2 back to phase 1? If dual-write diverges we might want to unwind.

### Alice [00:02:49]
Good question. My instinct is no, the shadow-write volume during that window is small enough to just replay. But let's think about it and not block phase 1 on the answer.

### Charlie [00:03:04]
I'll note it as an open question in the doc.

### Alice [00:03:09]
Perfect. Anything else?

### Bob [00:03:12]
No, I think we're good.

### Alice [00:03:14]
Okay, thanks everyone.
