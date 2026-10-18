from __future__ import annotations
import logging
import os
import re
import string
import tempfile
from typing import Dict, Any, Optional, Tuple, List

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

# Global singleton instance for WhisperModel
_WHISPER_MODEL: Optional[WhisperModel] = None
DEFAULT_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "tiny.en")


def get_whisper_model(model_size: Optional[str] = None) -> WhisperModel:
    """
    Returns a cached singleton WhisperModel instance.
    Uses 'tiny.en' by default on CPU with int8 quantization for minimal memory
    footprint and sub-second transcription latency.
    """
    global _WHISPER_MODEL
    size = model_size or DEFAULT_MODEL_SIZE
    if _WHISPER_MODEL is None:
        logger.info(f"Initializing faster-whisper model '{size}' on CPU (int8)...")
        _WHISPER_MODEL = WhisperModel(size, device="cpu", compute_type="int8")
    return _WHISPER_MODEL


def transcribe_audio_bytes(
    audio_bytes: bytes,
    filename: str = "audio.webm",
    model_size: Optional[str] = None,
) -> str:
    """
    Transcribes raw audio bytes (WebM, WAV, Ogg, MP3) using faster-whisper.
    Writes bytes safely to a temporary file, transcribes with PyAV decoding,
    and returns the merged transcription string.
    """
    if not audio_bytes or len(audio_bytes.strip()) == 0:
        return ""

    # Determine suffix based on filename or default to webm
    _, ext = os.path.splitext(filename)
    suffix = ext.lower() if ext else ".webm"
    if suffix not in [".webm", ".wav", ".ogg", ".mp3", ".m4a"]:
        suffix = ".webm"

    model = get_whisper_model(model_size)

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
        tmp_path = tmp_file.name
        tmp_file.write(audio_bytes)

    try:
        segments, info = model.transcribe(
            tmp_path,
            beam_size=5,
            language="en" if "en" in (model_size or DEFAULT_MODEL_SIZE) else None,
            vad_filter=True,  # Filter out silence/noise
        )
        text_segments = [s.text.strip() for s in segments if s.text and s.text.strip()]
        transcribed_text = " ".join(text_segments).strip()
        logger.info(f"Transcribed audio ({len(audio_bytes)} bytes) -> '{transcribed_text}'")
        return transcribed_text
    except Exception as e:
        logger.error(f"Error during audio transcription: {e}", exc_info=True)
        raise ValueError(f"Failed to transcribe audio file: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def _normalize_words(text: str) -> List[str]:
    """Normalizes text for word error rate comparison: lowercase, stripped punctuation."""
    text_clean = text.lower()
    text_clean = re.sub(f"[{re.escape(string.punctuation)}]", " ", text_clean)
    return [w for w in text_clean.split() if w]


def compute_transcription_accuracy(reference: str, hypothesis: str) -> Dict[str, Any]:
    """
    Computes transcription accuracy against reference text using Word Error Rate (WER).
    Returns accuracy percentage, word error rate, reference word count, and hypothesis.
    """
    ref_words = _normalize_words(reference)
    hyp_words = _normalize_words(hypothesis)

    r_len = len(ref_words)
    h_len = len(hyp_words)

    if r_len == 0 and h_len == 0:
        return {
            "accuracy_pct": 100.0,
            "word_error_rate": 0.0,
            "ref_word_count": 0,
            "hyp_word_count": 0,
            "reference": reference,
            "hypothesis": hypothesis,
        }

    if r_len == 0:
        return {
            "accuracy_pct": 0.0,
            "word_error_rate": 1.0,
            "ref_word_count": 0,
            "hyp_word_count": h_len,
            "reference": reference,
            "hypothesis": hypothesis,
        }

    # Standard Dynamic Programming Levenshtein distance on words
    dp = [[0] * (h_len + 1) for _ in range(r_len + 1)]
    for i in range(r_len + 1):
        dp[i][0] = i
    for j in range(h_len + 1):
        dp[0][j] = j

    for i in range(1, r_len + 1):
        for j in range(1, h_len + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                substitution = dp[i - 1][j - 1] + 1
                insertion = dp[i][j - 1] + 1
                deletion = dp[i - 1][j] + 1
                dp[i][j] = min(substitution, insertion, deletion)

    word_errors = dp[r_len][h_len]
    wer = round(word_errors / r_len, 4)
    accuracy_pct = round(max(0.0, 100.0 * (1.0 - (word_errors / r_len))), 2)

    return {
        "accuracy_pct": accuracy_pct,
        "word_error_rate": wer,
        "ref_word_count": r_len,
        "hyp_word_count": h_len,
        "reference": reference,
        "hypothesis": hypothesis,
    }
