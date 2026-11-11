from __future__ import annotations

import math
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import streamlit as st
from scipy.io import wavfile
from scipy.signal import find_peaks

APP_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = APP_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
MAX_VIDEO_BYTES = 100 * 1024 * 1024
MAX_VIDEO_SECONDS = 180


def run_ffmpeg(args: list[str]) -> None:
    proc = subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", *args],
                          capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(proc.stderr[-2500:] or "Errore FFmpeg")


def probe_duration(path: Path) -> float:
    proc = subprocess.run([FFMPEG, "-hide_banner", "-i", str(path)],
                          capture_output=True, text=True)
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", proc.stderr)
    if not match:
        raise RuntimeError("Non riesco a leggere la durata del video.")
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def audio_highlights(path: Path, clip_len: int, limit: int) -> list[tuple[float, float]]:
    with tempfile.TemporaryDirectory() as tmp:
        wav_path = Path(tmp) / "audio.wav"
        run_ffmpeg(["-i", str(path), "-vn", "-ac", "1", "-ar", "16000",
                    "-c:a", "pcm_s16le", str(wav_path)])
        rate, audio = wavfile.read(wav_path)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        audio = audio.astype(np.float32)
        if audio.size == 0:
            raise RuntimeError("La traccia audio è vuota.")
        window = rate
        count = len(audio) // window
        rms = np.array([
            math.sqrt(float(np.mean(audio[i * window:(i + 1) * window] ** 2)) + 1e-9)
            for i in range(count)
        ])
        if len(rms) < 3:
            raise RuntimeError("Video troppo breve per analizzare l'audio.")
        smooth = np.convolve(rms, np.ones(5) / 5, mode="same")
        threshold = max(float(np.percentile(smooth, 78)), float(np.mean(smooth) * 1.35))
        peaks, _ = find_peaks(smooth, height=threshold, distance=max(clip_len // 2, 8),
                              prominence=max(float(np.std(smooth) * 0.25), 1.0))
        if len(peaks) == 0:
            peaks = np.argsort(smooth)[::-1][:limit]
        ranked = sorted(peaks.tolist(), key=lambda p: smooth[p], reverse=True)
        duration = len(audio) / rate
        chosen: list[tuple[float, float]] = []
        for peak in ranked:
            start = max(0.0, peak - clip_len * 0.45)
            end = min(duration, start + clip_len)
            start = max(0.0, end - clip_len)
            if end - start < min(clip_len * 0.65, 10):
                continue
            if any(not (end <= a or start >= b) for a, b in chosen):
                continue
            chosen.append((start, end))
            if len(chosen) >= limit:
                break
        return sorted(chosen)


def ass_time(seconds: float) -> str:
    cs = max(0, int(round(seconds * 100)))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, c = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def make_ass(path: Path, segments) -> None:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Viral,Arial,66,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,2,2,70,70,260,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for seg in segments:
        caption_text = (seg.text or "").strip().replace("\\", "").replace("{", "").replace("}", "")
        if not caption_text:
            continue
        caption_text = re.sub(r"\s+", " ", caption_text).replace(",", r"\,")
        words = caption_text.split()
        chunks = [" ".join(words[i:i + 6]) for i in range(0, len(words), 6)]
        span = (float(seg.end) - float(seg.start)) / max(1, len(chunks))
        for i, chunk in enumerate(chunks):
            a = ass_time(float(seg.start) + i * span)
            b = ass_time(float(seg.start) + (i + 1) * span)
            lines.append(f"Dialogue: 0,{a},{b},Viral,,0,0,0,,{chunk}\n")
    path.write_text("\n".join(lines), encoding="utf-8-sig")


def transcribe(video: Path, start: float, end: float, model_name: str):
    from faster_whisper import WhisperModel
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    with tempfile.TemporaryDirectory() as tmp:
        wav_path = Path(tmp) / "clip.wav"
        run_ffmpeg(["-ss", str(start), "-i", str(video), "-t", str(end - start),
                    "-vn", "-ac", "1", "-ar", "16000", str(wav_path)])
        segments, _ = model.transcribe(str(wav_path), language="it", vad_filter=True,
                                       beam_size=3)
        return list(segments)


def render_clip(source: Path, start: float, end: float, destination: Path,
                caption_segments=None):
    filters = ("scale=1080:1920:force_original_aspect_ratio=increase,"
               "crop=1080:1920,setsar=1")
    if caption_segments is not None:
        ass_path = destination.with_suffix(".ass")
        make_ass(ass_path, caption_segments)
        escaped = str(ass_path.resolve()).replace("\\", "/").replace(":", r"\:")
        filters += f",subtitles='{escaped}'"
    run_ffmpeg(["-ss", str(start), "-i", str(source), "-t", str(end - start),
                "-vf", filters, "-map", "0:v:0", "-map", "0:a?",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
                "-pix_fmt", "yuv420p", "-y", str(destination)])


st.set_page_config(page_title="VIRAL GAMING CLIPS", page_icon="🎮", layout="centered")
st.title("🎮 VIRAL GAMING CLIPS")
st.caption("Versione web di prova · Aprila da tablet, telefono o PC")
st.info(
    "Questa versione gratuita è pensata per test brevi: video fino a 100 MB e 3 minuti. "
    "Cerca picchi di energia audio, non riconosce ancora con certezza kill, vittorie o battute virali."
)
st.warning(
    "Il video viene caricato ed elaborato sul server Streamlit, non direttamente sul tablet. "
    "Per questa prova evita video privati o contenuti che non vuoi caricare online."
)

uploaded = st.file_uploader(
    "Scegli una registrazione gaming (MP4, MKV, MOV o WEBM)",
    type=["mp4", "mkv", "mov", "webm"],
    max_upload_size=100,
)
col1, col2 = st.columns(2)
with col1:
    clip_len = st.slider("Durata di ogni clip", 15, 40, 25)
with col2:
    clip_count = st.slider("Numero massimo di clip", 1, 5, 3)

with st.expander("Sottotitoli automatici in italiano"):
    captions = st.checkbox("Trascrivi e inserisci sottotitoli", value=False)
    model_name = st.selectbox("Modello Whisper", ["tiny", "base"], index=0,
                              disabled=not captions)
    st.caption("La trascrizione può richiedere più tempo e risorse; per il primo test lasciala disattivata.")

if uploaded:
    st.write(f"File selezionato: **{uploaded.name}** · {uploaded.size / (1024**2):.1f} MB")
    if uploaded.size > MAX_VIDEO_BYTES:
        st.error("Il file supera il limite di 100 MB. Per la prova scegli un video più breve o più compresso.")
    elif st.button("Crea le mie clip", type="primary", use_container_width=True):
        suffix = Path(uploaded.name).suffix.lower() or ".mp4"
        source = OUTPUT_DIR / ("video_sorgente" + suffix)
        try:
            with st.spinner("Caricamento temporaneo del video..."):
                uploaded.seek(0)
                with source.open("wb") as destination_file:
                    shutil.copyfileobj(uploaded, destination_file, length=1024 * 1024)

            duration = probe_duration(source)
            st.write(f"Durata rilevata: **{duration:.0f} secondi**")
            if duration > MAX_VIDEO_SECONDS:
                raise RuntimeError("Per questa prova il video deve durare al massimo 3 minuti.")
            if duration < clip_len:
                raise RuntimeError("Il video è più corto della durata scelta per ogni clip.")

            with st.spinner("Analizzo l'audio e cerco i momenti candidati..."):
                moments = audio_highlights(source, clip_len, clip_count)
            if not moments:
                st.warning("Non ho trovato momenti adatti. Prova un'altra registrazione.")
            else:
                st.success(f"Trovati {len(moments)} momenti candidati.")
                progress = st.progress(0)
                results = []
                for idx, (start, end) in enumerate(moments, 1):
                    name = f"clip_{idx:02d}_{int(start):05d}s.mp4"
                    target = OUTPUT_DIR / name
                    subtitle_segments = None
                    if captions:
                        with st.spinner(f"Creo i sottotitoli della clip {idx}/{len(moments)}..."):
                            subtitle_segments = transcribe(source, start, end, model_name)
                    with st.spinner(f"Esporto la clip {idx}/{len(moments)}..."):
                        render_clip(source, start, end, target, subtitle_segments)
                    results.append((target, start, end))
                    progress.progress(idx / len(moments))

                st.success("Clip pronte: scaricale singolarmente o tutte insieme.")
                for target, start, end in results:
                    st.write(f"**{target.name}** · {int(start)}s – {int(end)}s")
                    st.video(str(target))
                    with target.open("rb") as clip_file:
                        st.download_button(
                            f"Scarica {target.name}", clip_file,
                            file_name=target.name, mime="video/mp4", key=target.name,
                            use_container_width=True,
                        )

                zip_path = OUTPUT_DIR / "tutte_le_clip.zip"
                with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                    for target, _, _ in results:
                        archive.write(target, arcname=target.name)
                with zip_path.open("rb") as zip_file:
                    st.download_button(
                        "Scarica tutte le clip (ZIP)", zip_file,
                        file_name=zip_path.name, mime="application/zip",
                        use_container_width=True,
                    )
        except Exception as exc:
            st.error(f"Non sono riuscito a completare l'elaborazione: {exc}")
        finally:
            if source.exists():
                source.unlink(missing_ok=True)

st.divider()
st.caption("Prototipo gratuito. I file caricati e generati sono temporanei sul server e non vanno considerati come archivio permanente.")
