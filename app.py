from __future__ import annotations

import hmac
import os
import re
import shutil
import socket
import sys
import subprocess
import tempfile
import zipfile
from pathlib import Path

import imageio_ffmpeg
import streamlit as st

from fortnite_engine import detect_fortnite_moments

APP_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = APP_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)
FFMPEG = shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()
MAX_UPLOAD_MB = 4096


def detect_encoder() -> tuple[list[str], bool]:
    try:
        result = subprocess.run([FFMPEG, "-hide_banner", "-encoders"],
                                capture_output=True, text=True, timeout=20)
        if "h264_nvenc" in (result.stdout + result.stderr):
            return ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "22"], True
    except Exception:
        pass
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "21"], False


VIDEO_ENCODER_ARGS, NVENC_DETECTED = detect_encoder()


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


def get_local_ips() -> list[str]:
    try:
        addresses = socket.gethostbyname_ex(socket.gethostname())[2]
        return sorted({ip for ip in addresses if ip.startswith(("192.168.", "10.", "172."))
                       and not ip.endswith(".1")})
    except OSError:
        return []


def pick_file_on_pc() -> str:
    picker_script = r'''
import tkinter as tk
from tkinter import filedialog
root = tk.Tk()
root.withdraw()
root.attributes("-topmost", True)
selected = filedialog.askopenfilename(
    title="Scegli la registrazione Fortnite sul PC",
    filetypes=[("Video", "*.mp4 *.mkv *.mov *.webm"), ("Tutti i file", "*.*")]
)
root.destroy()
print(selected)
'''
    proc = subprocess.run([sys.executable, "-c", picker_script],
                          capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or "Finestra di selezione non disponibile.")
    return proc.stdout.strip()


@st.cache_resource(show_spinner="Caricamento del modello Whisper...")
def get_whisper_model(model_name: str):
    from faster_whisper import WhisperModel
    return WhisperModel(model_name, device="cpu", compute_type="int8")


def transcribe(video: Path, start: float, end: float, model_name: str):
    model = get_whisper_model(model_name)
    with tempfile.TemporaryDirectory(prefix="vgc_caption_") as tmp:
        wav_path = Path(tmp) / "clip.wav"
        run_ffmpeg(["-ss", str(start), "-i", str(video), "-t", str(end - start),
                    "-vn", "-ac", "1", "-ar", "16000", str(wav_path)])
        segments, _ = model.transcribe(str(wav_path), language="it", vad_filter=True,
                                       beam_size=3, word_timestamps=True)
        return list(segments)


def ass_time(seconds: float) -> str:
    cs = max(0, int(round(seconds * 100)))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, c = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def clean_ass_text(value: str) -> str:
    return (value or "").replace("\\", "").replace("{", "").replace("}", "").replace("\n", " ").strip()


def make_ass(path: Path, segments, event_label: str, event_time: float) -> None:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Viral,Arial,62,&H00FFFFFF,&H0000D7FF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,6,2,2,70,70,270,1
Style: ViralTitle,Arial,88,&H0000D7FF,&H00FFFFFF,&H00101010,&H90000000,-1,0,0,0,100,100,0,0,1,8,3,8,70,70,0,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    title = clean_ass_text(event_label.upper())
    if title:
        lines.append(
            f"Dialogue: 1,0:00:00.10,0:00:01.45,ViralTitle,,0,0,0,,"
            f"{{\\an8\\pos(540,250)\\fad(120,220)\\fscx112\\fscy112}}{title}\n"
        )

    for seg in segments or []:
        words = getattr(seg, "words", None) or []
        if words:
            karaoke = []
            for word in words:
                word_text = clean_ass_text(getattr(word, "word", ""))
                if not word_text:
                    continue
                duration = max(1, int(round((float(word.end) - float(word.start)) * 100)))
                karaoke.append(f"{{\\kf{duration}}}{word_text}")
            text_line = " ".join(karaoke)
        else:
            text_line = clean_ass_text(getattr(seg, "text", ""))
        if not text_line:
            continue
        start = float(getattr(seg, "start", 0))
        end = float(getattr(seg, "end", start + 0.5))
        lines.append(
            f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Viral,,0,0,0,,{text_line}\n"
        )
    path.write_text("".join(lines), encoding="utf-8-sig")


def render_clip(source: Path, start: float, end: float, event_time: float,
                event_label: str, destination: Path, style: str,
                caption_segments=None) -> None:
    ass_path = destination.with_suffix(".ass")
    make_ass(ass_path, caption_segments, event_label, event_time - start)
    escaped = str(ass_path.resolve()).replace("\\", "/").replace(":", r"\:")

    if style == "Fortnite Hype (zoom + shake + flash)":
        impact = max(0.0, event_time - start)
        flash_start = max(0.0, impact - 0.08)
        flash_end = impact + 0.12
        shake_start = max(0.0, impact - 0.18)
        shake_end = impact + 0.32
        filter_graph = (
            "[0:v]split=2[bg][fg];"
            "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,gblur=sigma=22[bg2];"
            "[fg]scale=iw*1.07:ih*1.07,"
            "crop=iw/1.07:ih/1.07:"
            f"x='(iw-ow)/2+if(between(t,{shake_start:.3f},{shake_end:.3f}),sin(t*95)*10,0)':"
            f"y='(ih-oh)/2+if(between(t,{shake_start:.3f},{shake_end:.3f}),cos(t*105)*10,0)',"
            "scale=1080:1920:force_original_aspect_ratio=decrease[fg2];"
            "[bg2][fg2]overlay=(W-w)/2:(H-h)/2,setsar=1,"
            f"eq=brightness=0.16:enable='between(t,{flash_start:.3f},{flash_end:.3f})',"
            "unsharp=5:5:0.7:3:3:0.0,"
            f"subtitles='{escaped}'[v]"
        )
    else:
        filter_graph = (
            "[0:v]split=2[bg][fg];"
            "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,gblur=sigma=22[bg2];"
            "[fg]scale=1080:1920:force_original_aspect_ratio=decrease[fg2];"
            "[bg2][fg2]overlay=(W-w)/2:(H-h)/2,setsar=1,"
            f"subtitles='{escaped}'[v]"
        )

    command = [
        "-ss", str(start), "-i", str(source), "-t", str(end - start),
        "-filter_complex", filter_graph, "-map", "[v]", "-map", "0:a?",
        *VIDEO_ENCODER_ARGS,
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
        "-pix_fmt", "yuv420p", "-y", str(destination)
    ]
    try:
        run_ffmpeg(command)
    except RuntimeError:
        if not NVENC_DETECTED:
            raise
        cpu_command = [
            "-ss", str(start), "-i", str(source), "-t", str(end - start),
            "-filter_complex", filter_graph, "-map", "[v]", "-map", "0:a?",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
            "-pix_fmt", "yuv420p", "-y", str(destination)
        ]
        run_ffmpeg(cpu_command)


st.set_page_config(page_title="VIRAL GAMING CLIPS", page_icon="🎮", layout="centered")

# Accesso remoto protetto: la password viene generata dal launcher Windows
# e non è salvata nel repository.
ACCESS_PASSWORD = os.environ.get("VGC_ACCESS_PASSWORD", "")
if not ACCESS_PASSWORD:
    st.error("Avvio non valido: manca la protezione di accesso. Avvia VIRAL GAMING CLIPS.exe.")
    st.stop()

if not st.session_state.get("vgc_authenticated", False):
    st.title("🔐 Accesso a VIRAL GAMING CLIPS")
    entered = st.text_input("Password temporanea mostrata sul PC che ospita l'app", type="password")
    if st.button("ACCEDI", type="primary", use_container_width=True):
        if hmac.compare_digest(entered, ACCESS_PASSWORD):
            st.session_state["vgc_authenticated"] = True
            st.rerun()
        else:
            st.error("Password non corretta.")
    st.caption("Il collegamento remoto è temporaneo e resta attivo soltanto mentre il PC ospitante è acceso.")
    st.stop()

st.title("🎮 VIRAL GAMING CLIPS")
st.caption("Motore Windows remoto · Analisi Fortnite · Clip verticali automatiche")
st.success("Connessione remota protetta attiva. Il PC ospitante esegue analisi e montaggio: non serve essere sulla stessa rete Wi-Fi.")
st.info("Il video selezionato dal disco resta sul PC che esegue l'app. I collegamenti e i download passano attraverso il tunnel Internet temporaneo.")

st.info(
    "La selezione Fortnite combina lettura OCR del kill feed/Vittoria Royale, "
    "movimento a schermo e picchi audio. È un sistema automatico di ranking: "
    "non garantisce di riconoscere ogni kill o momento divertente. Controlla l'anteprima."
)

source_mode = st.radio(
    "Dove si trova il video?",
    ["Il video è già sul PC Windows (consigliato per file grandi)",
     "Carica il video dal dispositivo che stai usando"],
    index=0
)
source_path = None
uploaded = None
temporary_source = False

if source_mode.startswith("Il video"):
    if "pc_video_path" not in st.session_state:
        st.session_state["pc_video_path"] = ""
    if st.button("SCEGLI VIDEO DAL PC", use_container_width=True):
        try:
            selected_path = pick_file_on_pc()
            if selected_path:
                st.session_state["pc_video_path"] = selected_path
        except Exception as exc:
            st.error(f"Non riesco ad aprire la finestra dei file sul PC: {exc}")
    path_text = st.text_input(
        "Percorso completo del video sul PC (oppure usa il pulsante sopra)",
        placeholder=r"C:\Users\Nome\Videos\Fortnite\registrazione.mp4",
        key="pc_video_path"
    )
    if path_text.strip():
        source_path = Path(path_text.strip().strip('"')).expanduser()
        if not source_path.is_file():
            st.error("Non trovo il file sul PC. Controlla il percorso.")
            source_path = None
        else:
            st.caption(f"File trovato: {source_path.name} · {source_path.stat().st_size / (1024**3):.2f} GB")
    st.caption("Se apri il pannello dal tablet, premi SCEGLI VIDEO DAL PC: la finestra di selezione si apre sul computer Windows. Il file resta sul disco del PC.")
else:
    uploaded = st.file_uploader(
        "Seleziona la registrazione Fortnite",
        type=["mp4", "mkv", "mov", "webm"],
        max_upload_size=MAX_UPLOAD_MB,
    )
    if uploaded:
        st.caption(f"{uploaded.name} · {uploaded.size / (1024**3):.2f} GB")

st.divider()
col1, col2 = st.columns(2)
with col1:
    clip_len = st.slider("Durata clip (secondi)", 15, 60, 30)
with col2:
    clip_count = st.slider("Numero massimo di clip", 1, 30, 10)

st.subheader("Riconoscimento Fortnite")
ocr_enabled = st.checkbox("Leggi kill feed e scritte HUD (OCR)", value=True)
st.caption("Cerca parole come Eliminated, Knocked, Victory Royale e alcune varianti italiane. La lingua dell'interfaccia del gioco influenza i risultati.")

st.subheader("Montaggio automatico")
style = st.selectbox(
    "Stile grafico",
    ["Fortnite Hype (zoom + shake + flash)", "Pulito (sfondo sfocato + sottotitoli)"],
    index=0
)
captions = st.checkbox("Aggiungi sottotitoli italiani parola per parola", value=False)
model_name = st.selectbox("Modello sottotitoli", ["tiny", "base", "small"], index=0,
                          disabled=not captions)
st.caption("I sottotitoli usano Whisper. La prima esecuzione scarica il modello sul PC.")

if st.button("ANALIZZA FORTNITE E CREA LE CLIP", type="primary", use_container_width=True):
    if source_path is None and uploaded is None:
        st.error("Seleziona un video oppure inserisci il percorso di un file sul PC.")
    else:
        working_source = source_path
        if uploaded is not None:
            suffix = Path(uploaded.name).suffix.lower() or ".mp4"
            working_source = OUTPUT_DIR / ("upload_fortnite" + suffix)
            temporary_source = True
        try:
            if temporary_source and uploaded is not None:
                with st.spinner("Trasferimento del video al PC..."):
                    uploaded.seek(0)
                    with working_source.open("wb") as output_file:
                        shutil.copyfileobj(uploaded, output_file, length=4 * 1024 * 1024)

            duration = probe_duration(working_source)
            st.write(f"Durata video: **{duration / 60:.1f} minuti**")
            st.write(f"Dimensione: **{working_source.stat().st_size / (1024**3):.2f} GB**")

            analysis_progress = st.progress(0)
            analysis_status = st.empty()

            def update_progress(value: float, message: str):
                analysis_progress.progress(min(1.0, max(0.0, value)))
                analysis_status.caption(message)

            with st.spinner("Analisi Fortnite: audio, movimento e HUD..."):
                moments, warnings = detect_fortnite_moments(
                    working_source, FFMPEG, clip_len, clip_count,
                    ocr_enabled=ocr_enabled, progress_callback=update_progress
                )
            for warning in warnings:
                st.warning(warning)

            if moments:
                st.success(f"Ho trovato {len(moments)} momenti candidati. Ecco il punteggio e il motivo della selezione:")
                results = []
                export_progress = st.progress(0)
                for idx, moment in enumerate(moments, 1):
                    start, end = moment["start"], moment["end"]
                    event_time = moment["event_time"]
                    safe_label = re.sub(r"[^A-Za-z0-9_-]+", "_", moment["label"].lower())
                    target = OUTPUT_DIR / f"fortnite_{idx:02d}_{int(start):06d}s_{safe_label}.mp4"
                    subtitle_segments = None
                    if captions:
                        with st.spinner(f"Trascrizione clip {idx}/{len(moments)}..."):
                            subtitle_segments = transcribe(working_source, start, end, model_name)
                    with st.spinner(f"Montaggio clip {idx}/{len(moments)}..."):
                        render_clip(working_source, start, end, event_time,
                                    moment["label"], target, style, subtitle_segments)
                    results.append((target, moment))
                    export_progress.progress(idx / len(moments))

                st.success("Montaggio completato. Le clip sono file MP4 separati.")
                for target, moment in results:
                    with st.expander(
                        f"{moment['label']} · {int(moment['start'])}s–{int(moment['end'])}s · score {moment['score']}",
                        expanded=True
                    ):
                        st.write("**Perché è stata scelta:** " + " · ".join(moment["reasons"]))
                        if moment.get("ocr"):
                            st.caption("Testo HUD letto: " + moment["ocr"])
                        st.video(str(target))
                        with target.open("rb") as clip_file:
                            st.download_button(
                                f"Scarica {target.name}", clip_file,
                                file_name=target.name, mime="video/mp4",
                                key=target.name, use_container_width=True
                            )

                zip_path = OUTPUT_DIR / "fortnite_clips.zip"
                with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                    for target, _ in results:
                        archive.write(target, arcname=target.name)
                with zip_path.open("rb") as zip_file:
                    st.download_button(
                        "SCARICA TUTTE LE CLIP (ZIP)", zip_file,
                        file_name=zip_path.name, mime="application/zip",
                        use_container_width=True
                    )
                st.caption(f"Cartella locale di output: {OUTPUT_DIR}")
        except Exception as exc:
            st.error(f"Elaborazione non completata: {exc}")
        finally:
            if temporary_source and working_source and working_source.exists():
                working_source.unlink(missing_ok=True)

st.divider()
st.caption("Elaborazione sul PC Windows. I video selezionati tramite percorso non vengono copiati o cancellati; i caricamenti temporanei vengono rimossi a fine elaborazione.")
