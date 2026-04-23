# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A Claude Code skill that transcribes + diarizes audio recordings and produces project-aware meeting notes. The repo is designed to be cloned and symlinked as `~/.claude/skills/listen`, which makes it invokable as `/listen` from any Claude Code session.

## Architecture

Two pieces only:

1. **`scripts/transcribe.py`** — standalone Python CLI. Takes `--audio` and `--output-dir`. Runs faster-whisper for ASR, pyannote.audio for speaker diarization, maps words to speakers by max time overlap, groups into speaker turns, and emits `transcript.md`, `transcript.json`, `metadata.json`. No Claude-specific logic.
2. **`SKILL.md`** — Claude's playbook. Parses the user's `/listen` invocation, runs the script via Bash, reads the transcript, consults the project's `CLAUDE.md` for vocabulary, asks the user to identify speakers, then writes `meeting-notes.md`.

The extraction step uses Claude itself — no external LLM call. The script only handles audio.

## Common commands

```bash
uv sync                                           # Install deps.
uv run python scripts/transcribe.py --help        # Show CLI options.
uv run python scripts/transcribe.py --audio <f> --output-dir out/  # Run transcription directly.
```

For CUDA torch (after `uv sync`):
```bash
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

## Portability constraint

This repo is meant to be open-sourced. When editing anything that gets committed:

- No hardcoded personal paths (no `/home/<user>/`, no `/mnt/...` mounts, no specific cluster references).
- No personal tokens, emails, or usernames.
- No assumptions about SLURM or any particular compute environment beyond "Python + optional GPU".
- When in doubt, run `grep -rE '(home/[a-z]+|mnt/|@[a-z]+\.(com|org|edu))' .` and clean up anything it finds in tracked files.

## Editing tips

- The `SKILL.md` front matter `description` field determines when Claude auto-invokes the skill. If you change the trigger language, make sure it still mentions `/listen` and the "audio meeting" use case.
- `scripts/transcribe.py` has one job. Resist adding Claude-specific logic there; put playbook-style instructions in `SKILL.md` instead.
- Keep `pyproject.toml` minimal. Every added dep is a potential install failure for users on unusual platforms.

## Known gotchas

- `pyannote/speaker-diarization-3.1` requires ToS acceptance on Hugging Face. Without `HF_TOKEN` + ToS acceptance, diarization will 401. The script surfaces a clear error message for this.
- `ffmpeg` must be in PATH. faster-whisper invokes it to decode compressed formats.
- `compute_type="int8"` is used on CPU for speed. On GPU, `float16` is used. Don't change these without benchmarking.
- Word-to-speaker assignment uses max time overlap, not boundary snapping. In heavy crosstalk you'll see speaker labels flicker mid-sentence. That's the diarization being imperfect, not a bug in the glue code.
