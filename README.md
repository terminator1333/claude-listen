# listen — audio meetings to Claude-ready notes

A Claude Code skill that turns an audio recording into two things:

1. A speaker-labeled transcript with timestamps.
2. A structured `meeting-notes.md` written in the vocabulary of the current project (if a `CLAUDE.md` is present).

You invoke it inside Claude Code like a slash command:

```
/listen ~/recordings/standup.m4a extract action items and decisions that affect the roadmap
```

The free-text instruction after the path is optional. With no instruction, you get the full default structure (summary, decisions, action items, open questions, technical discussion, follow-ups).

## How it works

- **Transcription**: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2 backend for Whisper).
- **Speaker diarization**: [pyannote.audio](https://github.com/pyannote/pyannote-audio) 3.x.
- **Extraction**: Claude reads the transcript and the project's `CLAUDE.md`, then writes the notes. No extra LLM call needed.

GPU is used if available, otherwise CPU. Anonymous labels (`SPEAKER_00`, `SPEAKER_01`, …) come out of diarization; the skill then asks you who's who and rewrites the transcript with real names.

## Install

Requires Python 3.10+, `uv`, and `ffmpeg` in PATH.

```bash
# 1. Clone the repo.
git clone https://github.com/<user>/listen.git
cd listen

# 2. Install deps.
uv sync

# 3. Link it as a Claude Code skill.
ln -s "$(pwd)" ~/.claude/skills/listen

# 4. Set up HF access for pyannote (one time).
#    a. Create a read token at https://hf.co/settings/tokens
#    b. Accept the model ToS at https://hf.co/pyannote/speaker-diarization-3.1
export HF_TOKEN=<your-token>   # put this in your shell rc
```

### CUDA torch (optional, strongly recommended for anything longer than a few minutes)

`uv sync` installs the default torch wheel from PyPI. For CUDA, install a matching wheel afterwards:

```bash
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

Pick the tag that matches your CUDA runtime (`cu118`, `cu121`, `cu124`, …).

## Use

From any Claude Code session:

```
/listen path/to/audio.m4a
```

Or with an extraction focus:

```
/listen path/to/audio.m4a just the action items please, nothing else
```

Output goes to `./meetings/<YYYY-MM-DD-HHMM>/`:

- `transcript.md` — speaker-labeled, timestamped.
- `transcript.json` — full structured data (word-level timings, diarization segments).
- `meeting-notes.md` — structured extraction tailored to your instruction.
- `metadata.json` — model, device, duration, detected language.

## Running the CLI directly (without Claude)

```bash
uv run python scripts/transcribe.py --audio meeting.m4a --output-dir out/
# Options:
#   --model {tiny,base,small,medium,large-v2,large-v3}  default: small
#   --device {auto,cuda,cpu}                            default: auto
#   --language en                                       default: auto-detect
#   --num-speakers 3                                    default: infer
#   --no-diarize                                        skip speaker separation
```

## Hardware notes

Rough wall-clock times for a 60-minute mono recording:

| Hardware            | Model     | Transcribe | Diarize | Total |
|---------------------|-----------|------------|---------|-------|
| CPU (8 cores)       | `small`   | ~8 min     | ~6 min  | ~14 min |
| CPU (8 cores)       | `medium`  | ~22 min    | ~6 min  | ~28 min |
| GPU (consumer)      | `small`   | ~30 s      | ~45 s   | ~75 s |
| GPU (consumer)      | `large-v3`| ~1.5 min   | ~45 s   | ~2.5 min |

Numbers vary with recording quality, number of speakers, and model cache state.

## Limitations

- Transcript quality depends on audio quality. Noisy rooms, strong accents, and overlapping speech all degrade results. Diarization especially struggles with heavy overlap.
- Only transcribes, doesn't translate. A meeting in French comes out as French text. Claude can still write English notes on request.
- No voice enrollment — speakers come out as anonymous labels; you identify them manually per meeting.
- Outputs are written to the current directory's `meetings/` folder. If you want them elsewhere, move the directory afterwards.

## License

MIT.
