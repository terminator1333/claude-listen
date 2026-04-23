# Contributing to claude-listen

Thanks for wanting to help. The codebase is small (one Python script + one `SKILL.md` + config), so first-time contributors are welcome.

## Dev setup

```bash
git clone https://github.com/terminator1333/claude-listen.git
cd claude-listen
uv sync
```

The one dev dep is `ruff`, which `uv tool run` will fetch on demand. No pre-commit hook required, but running ruff before you push is appreciated:

```bash
uv tool run ruff check scripts/
uv tool run ruff format scripts/
```

## Running the CLI against a clip

Any mp3/m4a/wav works. For a quick smoke test on CPU:

```bash
uv run python scripts/transcribe.py --audio sample.m4a --output-dir out/ --model tiny --no-diarize
```

`--model tiny --no-diarize` makes this run in seconds on CPU, enough to exercise the pipeline end-to-end.

## Testing the Claude Code side

Symlink the repo to your local skills dir and invoke `/listen` in any Claude Code session:

```bash
ln -sf "$(pwd)" ~/.claude/skills/listen
```

The `SKILL.md` tells Claude how to drive the script, ask the speaker-mapping questions, and write `meeting-notes.md`. Changes there don't need CI — they affect Claude's behavior, not code that runs.

## Submitting a PR

- Branch off `main`: `git checkout -b feat/<short-name>` or `fix/<short-name>`.
- Keep PRs focused. One problem per PR is easier to review.
- Update `CHANGELOG.md` under `## [Unreleased]` if your change affects users.
- If you're changing CLI flags or output format, update `README.md` and `SKILL.md` too.
- Open a PR against `main`. GitHub Actions will run ruff and a CLI smoke test — make sure that's green.

## Good first issues

Some directions that would be high-value and don't require major refactors:

- **Voice enrollment.** Cache a speaker embedding per named speaker across meetings, so repeat speakers get labeled automatically. Would need a small store (a JSON file) and an embedding model (pyannote already has one loaded).
- **Translation mode.** Whisper can translate while transcribing (`task="translate"`). Plumb a `--translate` flag through.
- **Streaming / live mode.** Process audio in chunks as it's recorded, emit turns as they complete.
- **Better speaker-count hinting.** Pyannote sometimes over-clusters (splits one person into two labels). A pass to merge short same-speaker fragments separated by short gaps would help.
- **Output format options.** Markdown is the default; JSON, WebVTT, SRT subtitles could be useful for other tooling.
- **Windows setup notes in README.** Install tested on Linux and macOS; Windows-specific gotchas welcome.

## Code of conduct

Be kind, be specific, assume good faith. If someone's PR or issue isn't landing clearly, ask questions rather than closing it.
