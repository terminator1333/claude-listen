---
name: listen
description: Use when the user wants to turn an audio meeting recording into a project-aware transcript and notes, or invokes /listen
---

# /listen — audio recording to project-aware notes

Turn an audio recording into two artifacts: a speaker-labeled transcript and a set of structured notes written in the vocabulary of the current project. The user invokes this with an audio path and an optional free-text instruction describing what to extract.

## Invocation

```
/listen <audio-path> [free-text instruction]
```

Example: `/listen ~/recordings/standup.m4a extract action items and decisions that affect the project roadmap`

- `<audio-path>` is required. Supports any format ffmpeg reads (mp3, wav, m4a, flac, ogg, opus, webm, mov).
- The free-text instruction, if given, guides what to emphasize in the notes. If absent, produce the full default structure described below.

## Skill location

The transcription script lives at `~/.claude/skills/listen/scripts/transcribe.py`. The uv project (for deps) is the same directory. If the skill is installed elsewhere, adjust the paths in the commands below.

## Steps

1. **Parse args from the user's message.** First token after `/listen` is the audio path. Everything after it is the free-text instruction (may be unquoted). If no audio path is given, ask via AskUserQuestion and stop — don't guess.

2. **Resolve paths.**
   - `PROJECT_DIR` = current working directory (the dir Claude was started in).
   - `OUTPUT_DIR` = `$PROJECT_DIR/meetings/<YYYY-MM-DD-HHMM>/` where the timestamp is now. Use `date +%Y-%m-%d-%H%M` via Bash.
   - Create `OUTPUT_DIR`.

3. **Verify the audio file exists.** If not, report the resolved path and stop.

4. **Run the transcription script.** Tell the user what's about to happen (one sentence, not a list), then run:
   ```
   uv run --project ~/.claude/skills/listen python ~/.claude/skills/listen/scripts/transcribe.py \
     --audio <audio-path> --output-dir <OUTPUT_DIR>
   ```
   Default model is `small`. For long recordings (>30min) on GPU, use `--model medium` or `--model large-v3` for better quality. Never pick a larger model on CPU without the user's go-ahead — it gets slow quickly.

   If transcription fails:
   - Missing `HF_TOKEN`: tell the user the two setup steps (create token at hf.co/settings/tokens, accept ToS at hf.co/pyannote/speaker-diarization-3.1). Suggest `--no-diarize` as a temporary workaround if they want a single-speaker transcript right now.
   - Missing ffmpeg: tell them to install it via their package manager.
   - Other errors: surface the actual error. Don't retry blindly.

5. **Read the generated transcript.** Read `transcript.md` from `OUTPUT_DIR`. If it's long, read it in chunks (use `offset` and `limit`) and build understanding incrementally rather than forcing everything into one pass.

6. **Read project context.** Read `$PROJECT_DIR/CLAUDE.md` if present. Also glance at `README.md` and any `docs/` dir. Use this vocabulary in the notes — prefer the project's terms over generic ones.

7. **Remap speakers to real names.** Collect the set of `SPEAKER_XX` labels present in the transcript, find each speaker's first substantive utterance (skip filler like "yeah", "uh", one-word turns), and ask the user to identify them via AskUserQuestion. Offer "skip / keep anonymous" as an option.
   - After they answer, rewrite `transcript.md` replacing each `SPEAKER_XX` with the real name (or the provided label). Do the same substitution in the JSON.
   - If the user skips, leave labels as-is.

8. **Write `meeting-notes.md` in `OUTPUT_DIR`.** Tailor the emphasis to the user's instruction:
   - If their instruction focuses on **action items / next steps**: lead with those, deprioritize general summary.
   - If it focuses on **decisions**: lead with decisions, include rationale where audible.
   - If it focuses on **technical content**: expand the technical section, cite speakers on specific claims.
   - If **no instruction**, use the full default structure below.

   Default structure (include only sections that have real content — don't invent to fill):
   - **Summary** — 2 to 3 sentences of plain prose. What was the meeting about, what was the outcome.
   - **Decisions** — bullets: who decided, what was decided, key rationale if it was stated.
   - **Action items** — bullets: `[owner] thing to do (timing if mentioned)`.
   - **Open questions** — bullets: things raised but not resolved.
   - **Technical discussion** — subheadings by topic. Attribute non-obvious claims to speakers.
   - **Flagged for follow-up** — things that sounded important but weren't resolved in the meeting.

   Rules while writing:
   - Use project vocabulary from `CLAUDE.md` when it's more precise than a generic word.
   - Don't editorialize. If attribution matters ("X said we should Y"), attribute. If the speaker doesn't matter, don't.
   - Don't include small talk, throat-clearing, or tangents unless they're load-bearing.
   - Prefer short bullets over paragraphs. Keep the whole doc skimmable.

9. **Report back.** One or two sentences. Paths to the three files (`transcript.md`, `transcript.json`, `meeting-notes.md`) and a one-line summary of what the meeting was about.

## Notes

- Diarization is imperfect. If the transcript looks wrong (e.g., one speaker attributed to another across a whole segment), surface this to the user rather than silently trusting it.
- If the transcript is in a language other than English and the user's instruction is English, write the notes in English but quote original-language phrases verbatim where they matter.
- Never overwrite an existing `meetings/<timestamp>/` directory. Timestamps include minute granularity so collisions are rare, but if one happens, append `-2`, `-3`, etc.
