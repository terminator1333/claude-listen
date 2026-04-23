# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Plain-English disclaimer section in the README covering recording consent, privacy, transcription accuracy, model behavior, and third-party service risk. Complements the MIT license's legal-style warranty disclaimer.

## [0.1.0] - 2026-04-23

### Added

- Initial release.
- `/listen` Claude Code slash command: invokes the transcription pipeline and walks the user through speaker mapping before writing project-aware notes.
- `scripts/transcribe.py` CLI: faster-whisper + pyannote.audio 3.1 pipeline. Decodes audio once via PyAV and shares the numpy waveform between ASR and diarization (supports mp3, m4a, wav, flac, ogg, opus, webm, mov).
- Transcription checkpoint to `_transcription_cache.json` so diarization retries don't re-run Whisper.
- Automatic device selection (`--device auto`) with CUDA 12.1 torch pinned in `pyproject.toml` to match `ctranslate2`'s runtime. CPU fallback works out of the box.
- HF token resolution: `HF_TOKEN` env var → `HUGGING_FACE_HUB_TOKEN` env var → `~/.cache/huggingface/token` (from `huggingface-cli login`).
- Outputs: `transcript.md`, `transcript.json`, `meeting-notes.md`, `metadata.json` in `./meetings/<YYYY-MM-DD-HHMM>/`.

### Known limitations

- Diarization sometimes splits one speaker across multiple labels, especially on short turns. The `/listen` skill surfaces this during the mapping dialog so the user can merge manually.
- No voice enrollment; speakers are identified per meeting.
- Transcription only, not translation.

[Unreleased]: https://github.com/terminator1333/claude-listen/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/terminator1333/claude-listen/releases/tag/v0.1.0
