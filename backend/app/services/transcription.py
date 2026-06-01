"""Audio transcription service using faster-whisper."""

import os
import time
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy-loaded model
_model = None


def get_model(model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
    global _model
    if _model is None:
        logger.info(f"Loading Whisper model: {model_size} ({device}/{compute_type})")
        from faster_whisper import WhisperModel
        _model = WhisperModel(model_size, device=device, compute_type=compute_type)
    return _model


def transcribe(audio_path: str, model_size: str = "base",
               device: str = "cpu", compute_type: str = "int8") -> dict:
    """Transcribe an audio file. Returns segments and full text."""
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    model = get_model(model_size, device, compute_type)

    logger.info(f"Transcribing: {audio_path}")
    t0 = time.time()

    segments, info = model.transcribe(audio_path, beam_size=5, vad_filter=True)

    result_segments = []
    full_text = []
    for seg in segments:
        result_segments.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
        })
        full_text.append(seg.text.strip())

    elapsed = time.time() - t0
    logger.info(f"Transcribed {Path(audio_path).name} in {elapsed:.1f}s "
                f"({len(result_segments)} segments)")

    return {
        "segments": result_segments,
        "full_text": " ".join(full_text),
        "duration": info.duration if hasattr(info, 'duration') else 0,
        "language": info.language if hasattr(info, 'language') else "unknown",
    }
