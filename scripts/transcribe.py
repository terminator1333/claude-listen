"""Audio -> speaker-labeled transcript.

Pipeline:
  1. faster-whisper transcribes audio to word-level segments.
  2. pyannote.audio diarizes speakers (default on; --no-diarize to skip).
  3. Each word is assigned to the diarization segment it overlaps most.
  4. Words are grouped into contiguous speaker turns.
  5. Writes transcript.json, transcript.md, metadata.json to --output-dir.

Env:
  HF_TOKEN   required for diarization. Get at hf.co/settings/tokens and
             accept the ToS at hf.co/pyannote/speaker-diarization-3.1.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import timedelta
from pathlib import Path


def format_timestamp(seconds: float) -> str:
    total = int(timedelta(seconds=int(seconds)).total_seconds())
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _read_hf_cached_token() -> str | None:
    """Fall back to the token stored by `huggingface-cli login`."""
    candidates = [
        Path.home() / ".cache" / "huggingface" / "token",
        Path.home() / ".huggingface" / "token",
    ]
    for path in candidates:
        if path.exists():
            token = path.read_text().strip()
            if token:
                return token
    return None


def detect_device(arg: str) -> str:
    if arg != "auto":
        return arg
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


def decode_audio_numpy(audio_path: Path, sample_rate: int = 16000):
    """Decode any audio format to mono float32 numpy at `sample_rate`.

    Goes through PyAV (bundled by faster-whisper), so m4a/mp3/flac/etc. all work
    without needing a system ffmpeg binary or a torchaudio backend dance.
    """
    from faster_whisper.audio import decode_audio

    return decode_audio(str(audio_path), sampling_rate=sample_rate)


def transcribe_words(
    waveform, model_name: str, device: str, language: str | None
) -> tuple[list[dict], dict]:
    from faster_whisper import WhisperModel

    compute_type = "float16" if device == "cuda" else "int8"
    model = WhisperModel(model_name, device=device, compute_type=compute_type)

    segments, info = model.transcribe(
        waveform,
        word_timestamps=True,
        language=language,
        vad_filter=True,
    )
    words: list[dict] = []
    for seg in segments:
        if not seg.words:
            continue
        for w in seg.words:
            words.append(
                {
                    "start": float(w.start),
                    "end": float(w.end),
                    "text": w.word.strip(),
                    "confidence": float(w.probability),
                }
            )
    meta = {
        "language": info.language,
        "language_probability": float(info.language_probability),
        "duration": float(info.duration),
    }
    return words, meta


def diarize(
    waveform, sample_rate: int, device: str, num_speakers: int | None, hf_token: str
) -> list[dict]:
    import torch
    from pyannote.audio import Pipeline

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=hf_token,
    )
    if pipeline is None:
        raise RuntimeError(
            "pyannote returned no pipeline. Most likely causes:\n"
            "  - ToS not accepted. Visit https://hf.co/pyannote/speaker-diarization-3.1\n"
            "    and also https://hf.co/pyannote/segmentation-3.0 and click 'Agree'.\n"
            "  - HF token lacks read access, or is expired.\n"
            "The script cannot continue without the diarization model. "
            "Re-run with --no-diarize for a single-speaker transcript."
        )
    if device == "cuda":
        pipeline.to(torch.device("cuda"))

    # Pass waveform as a dict so pyannote skips its own audio loader (which uses
    # torchaudio's soundfile backend and can't read m4a).
    waveform_t = torch.from_numpy(waveform).unsqueeze(0)  # (1, num_samples)
    audio_input = {"waveform": waveform_t, "sample_rate": sample_rate}

    kwargs = {}
    if num_speakers is not None:
        kwargs["num_speakers"] = num_speakers
    diarization = pipeline(audio_input, **kwargs)

    segments: list[dict] = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append(
            {
                "start": float(turn.start),
                "end": float(turn.end),
                "speaker": str(speaker),
            }
        )
    return segments


def assign_speakers(words: list[dict], segments: list[dict]) -> list[dict]:
    if not segments:
        for w in words:
            w["speaker"] = "SPEAKER_00"
        return words
    for w in words:
        best_speaker = None
        best_overlap = 0.0
        for seg in segments:
            overlap = max(0.0, min(w["end"], seg["end"]) - max(w["start"], seg["start"]))
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = seg["speaker"]
        w["speaker"] = best_speaker or "UNKNOWN"
    return words


def group_into_turns(words: list[dict], gap_threshold: float = 1.5) -> list[dict]:
    """A turn is a run of same-speaker words with no gap longer than gap_threshold."""
    if not words:
        return []
    turns: list[dict] = []
    current = {
        "speaker": words[0]["speaker"],
        "start": words[0]["start"],
        "end": words[0]["end"],
        "words": [words[0]],
    }
    for w in words[1:]:
        same_speaker = w["speaker"] == current["speaker"]
        gap = w["start"] - current["end"]
        if same_speaker and gap < gap_threshold:
            current["words"].append(w)
            current["end"] = w["end"]
        else:
            turns.append(current)
            current = {
                "speaker": w["speaker"],
                "start": w["start"],
                "end": w["end"],
                "words": [w],
            }
    turns.append(current)
    for t in turns:
        t["text"] = " ".join(w["text"] for w in t["words"]).strip()
    return turns


def render_markdown(turns: list[dict], audio_meta: dict) -> str:
    lines = ["# Transcript", ""]
    dur = format_timestamp(audio_meta.get("duration", 0.0))
    lang = audio_meta.get("language", "unknown")
    lines.append(f"*Duration: {dur} · Language: {lang}*")
    lines.append("")
    for t in turns:
        ts = format_timestamp(t["start"])
        lines.append(f"### {t['speaker']} [{ts}]")
        lines.append(t["text"])
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Transcribe audio with speaker diarization.")
    ap.add_argument("--audio", required=True, type=Path, help="Path to audio file.")
    ap.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory for output files (created if missing).",
    )
    ap.add_argument(
        "--model",
        default="small",
        choices=["tiny", "base", "small", "medium", "large-v2", "large-v3"],
        help="faster-whisper model size (default: small).",
    )
    ap.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    ap.add_argument(
        "--language",
        default=None,
        help="Language code (e.g. 'en'). Default: auto-detect.",
    )
    ap.add_argument(
        "--num-speakers",
        type=int,
        default=None,
        help="Force a specific speaker count (default: infer).",
    )
    ap.add_argument(
        "--no-diarize",
        action="store_true",
        help="Skip diarization; everyone labeled SPEAKER_00.",
    )
    args = ap.parse_args()

    if not args.audio.exists():
        print(f"ERROR: audio file not found: {args.audio}", file=sys.stderr)
        return 2
    args.output_dir.mkdir(parents=True, exist_ok=True)

    device = detect_device(args.device)
    print(f"[listen] device={device} model={args.model} audio={args.audio}", file=sys.stderr)

    # Transcription checkpoint: if a prior run cached words for the same audio
    # and model, reuse them. Lets us retry diarization without re-transcribing.
    cache_path = args.output_dir / "_transcription_cache.json"
    cached = None
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text())
            if (
                cached.get("audio_path") == str(args.audio.resolve())
                and cached.get("model") == args.model
            ):
                words = cached["words"]
                audio_meta = cached["audio_meta"]
                print(
                    f"[listen] reusing cached transcription ({len(words)} words) from {cache_path}",
                    file=sys.stderr,
                )
            else:
                cached = None
        except (json.JSONDecodeError, KeyError):
            cached = None

    # Decode the audio once (PyAV handles m4a/mp3/wav/etc.) and share the
    # numpy array between transcription and diarization. Avoids torchaudio's
    # soundfile backend which doesn't support compressed formats.
    sample_rate = 16000
    print(f"[listen] decoding audio at {sample_rate} Hz...", file=sys.stderr)
    waveform = decode_audio_numpy(args.audio, sample_rate=sample_rate)
    print(
        f"[listen] decoded {len(waveform) / sample_rate:.1f}s of audio",
        file=sys.stderr,
    )

    if cached is None:
        t0 = time.time()
        print("[listen] transcribing...", file=sys.stderr)
        words, audio_meta = transcribe_words(waveform, args.model, device, args.language)
        print(
            f"[listen] transcribed {len(words)} words in {time.time() - t0:.1f}s",
            file=sys.stderr,
        )
        cache_path.write_text(
            json.dumps(
                {
                    "audio_path": str(args.audio.resolve()),
                    "model": args.model,
                    "words": words,
                    "audio_meta": audio_meta,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    segments: list[dict] = []
    if not args.no_diarize:
        hf_token = (
            os.environ.get("HF_TOKEN")
            or os.environ.get("HUGGING_FACE_HUB_TOKEN")
            or _read_hf_cached_token()
        )
        if not hf_token:
            print(
                "ERROR: HF token required for diarization.\n"
                "  1. Create a token at https://hf.co/settings/tokens\n"
                "  2. Accept ToS at https://hf.co/pyannote/speaker-diarization-3.1\n"
                "  3. Either `huggingface-cli login` or export HF_TOKEN=<token>\n"
                "Or pass --no-diarize to skip speaker separation.",
                file=sys.stderr,
            )
            return 3
        t1 = time.time()
        print("[listen] diarizing...", file=sys.stderr)
        segments = diarize(waveform, sample_rate, device, args.num_speakers, hf_token)
        n_speakers = len({s["speaker"] for s in segments})
        print(
            f"[listen] diarized into {n_speakers} speaker(s) in {time.time() - t1:.1f}s",
            file=sys.stderr,
        )

    words = assign_speakers(words, segments)
    turns = group_into_turns(words)

    metadata = {
        **audio_meta,
        "model": args.model,
        "device": device,
        "diarized": not args.no_diarize,
        "num_speakers": len({w["speaker"] for w in words}),
        "num_turns": len(turns),
        "audio_path": str(args.audio.resolve()),
    }

    transcript_json = args.output_dir / "transcript.json"
    transcript_md = args.output_dir / "transcript.md"
    metadata_json = args.output_dir / "metadata.json"

    transcript_json.write_text(
        json.dumps(
            {"turns": turns, "diarization_segments": segments},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    transcript_md.write_text(render_markdown(turns, audio_meta), encoding="utf-8")
    metadata_json.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    # stdout: one path per line, for the skill to parse.
    print(str(transcript_md))
    print(str(transcript_json))
    print(str(metadata_json))
    return 0


if __name__ == "__main__":
    sys.exit(main())
