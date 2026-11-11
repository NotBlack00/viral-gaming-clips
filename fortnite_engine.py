from __future__ import annotations

import math
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
from scipy.io import wavfile
from scipy.signal import find_peaks

FORTNITE_TERMS = {
    "VITTORIA REALE": (
        "victory royale", "victoryroyale", "vittoria reale", "vittoria royale"
    ),
    "ELIMINAZIONE": (
        "eliminated", "elimination", "eliminato", "eliminata", "ha eliminato",
        "eliminazione", "knocked out", "knocked", "messo ko", "mandato ko"
    ),
    "TOP PLACEMENT": (
        "you placed", "placed #", "sei arrivato", "sei arrivata", "posizione"
    ),
    "REBOOT / REVIVE": (
        "reboot", "revived", "rianimato", "rianimata", "riavviato"
    ),
}


def _extract_audio_scores(video: Path, ffmpeg: str) -> np.ndarray:
    with tempfile.TemporaryDirectory(prefix="vgc_audio_") as tmp:
        wav_path = Path(tmp) / "analysis.wav"
        proc = subprocess.run(
            [ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(video),
             "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav_path)],
            capture_output=True, text=True
        )
        if proc.returncode:
            raise RuntimeError(proc.stderr[-1800:] or "Non riesco a estrarre l'audio.")
        rate, audio = wavfile.read(wav_path)
        if audio.ndim > 1:
            audio = audio[:, 0]
        if not audio.size:
            raise RuntimeError("La traccia audio è vuota.")
        window = int(rate)
        count = max(1, len(audio) // window)
        rms = np.empty(count, dtype=np.float32)
        for i in range(count):
            chunk = audio[i * window:(i + 1) * window].astype(np.float32)
            rms[i] = math.sqrt(float(np.mean(chunk * chunk)) + 1e-9) if chunk.size else 0.0
        return rms


def _normalise(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float32)
    if not values.size:
        return values
    low = float(np.percentile(values, 30))
    high = float(np.percentile(values, 95))
    if high <= low + 1e-6:
        return np.zeros_like(values)
    return np.clip((values - low) / (high - low), 0.0, 1.5)


def _read_ocr_text(engine, image: np.ndarray) -> list[tuple[str, float]]:
    result = engine(image)
    if isinstance(result, tuple):
        result = result[0]
    output: list[tuple[str, float]] = []
    if result is None:
        return output
    if hasattr(result, "txts"):
        texts = getattr(result, "txts") or []
        scores = getattr(result, "scores", None) or []
        for i, value in enumerate(texts):
            score = float(scores[i]) if i < len(scores) else 0.6
            output.append((str(value).lower(), score))
        return output
    if isinstance(result, list):
        for item in result:
            try:
                if isinstance(item, dict):
                    value = item.get("txt", item.get("text", ""))
                    score = float(item.get("score", 0.6))
                else:
                    value = item[1]
                    score = float(item[2]) if len(item) > 2 else 0.6
                output.append((str(value).lower(), score))
            except (IndexError, TypeError, ValueError):
                continue
    return output


def _event_label(text: str) -> str | None:
    compact = " ".join(text.lower().replace("|", " ").split())
    for label, terms in FORTNITE_TERMS.items():
        if any(term in compact for term in terms):
            return label
    return None


def detect_fortnite_moments(
    video: Path,
    ffmpeg: str,
    clip_seconds: int = 30,
    max_clips: int = 12,
    ocr_enabled: bool = True,
    progress_callback: Callable[[float, str], None] | None = None,
) -> tuple[list[dict], list[str]]:
    """Rank candidate moments using Fortnite HUD OCR, motion changes and audio peaks."""
    warnings: list[str] = []
    audio = _extract_audio_scores(video, ffmpeg)
    duration = float(len(audio))
    audio_norm = _normalise(np.convolve(audio, np.ones(5, dtype=np.float32) / 5, mode="same"))

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError("Non riesco ad aprire il video con OpenCV.")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    frame_count = float(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    video_duration = frame_count / fps if fps > 0 and frame_count > 0 else duration
    duration = min(duration, video_duration) if duration > 0 else video_duration
    timeline_size = max(2, int(math.ceil(duration)) + 1)
    motion = np.zeros(timeline_size, dtype=np.float32)
    ocr_hits: list[tuple[float, str, str]] = []
    engine = None

    if ocr_enabled:
        try:
            from rapidocr import RapidOCR
            engine = RapidOCR()
        except Exception as exc:
            warnings.append(f"OCR Fortnite non disponibile ({exc}). Continuo con audio e movimento.")
            engine = None

    sample_step = 2
    sample_times = list(range(0, int(duration), sample_step))
    previous = None
    try:
        for index, second in enumerate(sample_times):
            cap.set(cv2.CAP_PROP_POS_MSEC, second * 1000)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            small = cv2.resize(frame, (320, 180), interpolation=cv2.INTER_AREA)
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            if previous is not None:
                diff = cv2.absdiff(gray, previous)
                motion[min(second, timeline_size - 1)] = float(np.mean(diff))
            previous = gray

            if engine is not None and second % 4 == 0:
                height, width = frame.shape[:2]
                hud = frame[:max(1, int(height * 0.62)), :width]
                if width > 1280:
                    new_h = int(hud.shape[0] * (1280 / width))
                    hud = cv2.resize(hud, (1280, new_h), interpolation=cv2.INTER_AREA)
                try:
                    texts = _read_ocr_text(engine, hud)
                    joined = " ".join(value for value, confidence in texts if confidence >= 0.35)
                    label = _event_label(joined)
                    if label:
                        ocr_hits.append((float(second), label, joined[:220]))
                except Exception as exc:
                    warnings.append(f"Un fotogramma OCR è stato saltato: {exc}")
            if progress_callback and index % 5 == 0:
                progress_callback((index + 1) / max(1, len(sample_times)), "Analisi fotogrammi Fortnite")
    finally:
        cap.release()

    motion_norm = _normalise(np.convolve(motion, np.ones(3, dtype=np.float32) / 3, mode="same"))
    scores = np.zeros(timeline_size, dtype=np.float32)
    audio_len = min(len(audio_norm), timeline_size)
    scores[:audio_len] += audio_norm[:audio_len] * 1.15
    scores += motion_norm * 0.85

    for event_time, _, _ in ocr_hits:
        center = int(round(event_time))
        for offset, weight in [(-2, 1.5), (-1, 3.0), (0, 7.0), (1, 4.0), (2, 2.0)]:
            position = center + offset
            if 0 <= position < timeline_size:
                scores[position] += weight

    if not scores.size or float(np.max(scores)) < 0.08:
        warnings.append("Non ho rilevato segnali abbastanza forti per proporre clip affidabili.")
        if progress_callback:
            progress_callback(1.0, "Analisi completata")
        return [], warnings

    min_distance = max(8, int(clip_seconds * 0.65))
    peaks, _ = find_peaks(scores, distance=min_distance, prominence=0.15)
    if len(peaks) == 0:
        peaks = np.argsort(scores)[::-1][:max_clips * 3]
    ranked = sorted((int(p) for p in peaks), key=lambda p: float(scores[p]), reverse=True)

    audio_cut = float(np.percentile(audio_norm, 82)) if audio_norm.size else 1.0
    motion_cut = float(np.percentile(motion_norm, 82)) if motion_norm.size else 1.0
    moments: list[dict] = []
    half_before = int(clip_seconds * 0.58)

    for peak in ranked:
        start = max(0.0, float(peak - half_before))
        end = min(duration, start + clip_seconds)
        start = max(0.0, end - clip_seconds)
        if end - start < min(clip_seconds * 0.65, 10):
            continue
        if any(not (end <= item["start"] or start >= item["end"]) for item in moments):
            continue

        nearby = [hit for hit in ocr_hits if abs(hit[0] - peak) <= 6]
        label = nearby[0][1] if nearby else "AZIONE INTENSA"
        reasons = []
        if nearby:
            reasons.append("Testo HUD Fortnite: " + ", ".join(dict.fromkeys(hit[1] for hit in nearby)))
        if peak < len(audio_norm) and audio_norm[peak] >= audio_cut:
            reasons.append("Picco audio")
        if peak < len(motion_norm) and motion_norm[peak] >= motion_cut:
            reasons.append("Movimento rapido a schermo")
        if not reasons:
            reasons.append("Combinazione di segnali visivi e audio")
        moments.append({
            "start": start,
            "end": end,
            "event_time": float(peak),
            "score": round(float(scores[peak]), 2),
            "label": label,
            "reasons": reasons,
            "ocr": nearby[0][2] if nearby else "",
        })
        if len(moments) >= max_clips:
            break

    moments.sort(key=lambda item: item["start"])
    if not ocr_hits and ocr_enabled and engine is not None:
        warnings.append("Non ho letto parole chiave del kill feed/Vittoria Royale: i candidati usano soprattutto audio e movimento.")
    if not moments:
        warnings.append("Non ho trovato picchi sufficienti; prova ad aumentare il numero massimo di clip.")
    if progress_callback:
        progress_callback(1.0, "Analisi completata")
    return moments, warnings
