#!/usr/bin/env python3
"""
Builds the day's social-media kit from data.js (everything free, runs in GitHub Actions):

  media/<date>/
    img-1.jpg ... img-4.jpg   1080x1350 cards: the level card + the top 3 power-ups (Bluesky, Threads, Instagram)
    video.mp4                 1080x1920 vertical, ~30-45 s, announcer voiceover + chiptune beat (Reels, Shorts, TikTok)
    post.json                 captions for each platform + file list, read by scripts/post.py

How:
  1. Serves the project folder locally and opens share.html in headless Chromium (Playwright) to capture each frame.
     share.html uses the same model.js as the site, so the numbers always match the website.
  2. Piper (free, open-source text-to-speech) reads an announcer script for each frame.
  3. ffmpeg turns each frame + voice line into a slowly zooming clip, joins them, and mixes in a chiptune
     loop that this script synthesizes itself (no music licensing issues).

Usage:
  python scripts/media.py            # only builds if data.js has drops dated today
  python scripts/media.py --force    # build from whatever data.js has (testing)
"""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import threading
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_URL = "https://wagmisensei-dot.github.io/ai-level"
VOICE = "en_US-ryan-high"          # Piper voice; see https://huggingface.co/rhasspy/piper-voices
VOICE_DIR = ROOT / ".cache" / "piper"
TOP_CARDS = 3                      # cards per post (Bluesky allows 4 images: level card + 3)
FPS = 30


def ffmpeg_exe() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg            # bundled static ffmpeg, so nothing to install system-wide
    return imageio_ffmpeg.get_ffmpeg_exe()


def run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd[:6])}...\n{r.stderr[-1500:]}")


# ---------------------------------------------------------------- 1. frames

class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):  # keep the Actions log clean
        pass


def serve_root() -> tuple[http.server.ThreadingHTTPServer, int]:
    handler = functools.partial(_Quiet, directory=str(ROOT))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def capture_frames(out: Path) -> dict:
    from playwright.sync_api import sync_playwright

    srv, port = serve_root()
    base = f"http://127.0.0.1:{port}/share.html"
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()

            def shot(params: str, w: int, h: int, path: Path, quality: int = 90) -> dict:
                page = browser.new_page(viewport={"width": w, "height": h})
                page.goto(f"{base}?{params}")
                page.wait_for_function("window.SHARE_READY === true", timeout=30000)
                info = page.evaluate("window.SHARE_INFO")
                # Bluesky rejects images over ~1 MB, so step the JPEG quality down until it fits
                for q in (quality, 82, 74, 66):
                    page.screenshot(path=str(path), type="jpeg", quality=q)
                    if path.stat().st_size < 950_000:
                        break
                page.close()
                return info

            info = shot("view=level&format=portrait", 1080, 1350, out / "img-1.jpg")
            top = info["items"][:TOP_CARDS]
            for n, p in enumerate(top, start=2):
                shot(f"view=card&id={p['id']}&format=portrait", 1080, 1350, out / f"img-{n}.jpg")

            frames = [out / "frames" / "f0-level.jpg"]
            frames[0].parent.mkdir(exist_ok=True)
            shot("view=level&format=story", 1080, 1920, frames[0], 92)
            for n, p in enumerate(top, start=1):
                f = out / "frames" / f"f{n}-card.jpg"
                shot(f"view=card&id={p['id']}&format=story", 1080, 1920, f, 92)
                frames.append(f)
            f = out / "frames" / f"f{len(top) + 1}-outro.jpg"
            shot("view=outro&format=story", 1080, 1920, f, 92)
            frames.append(f)
            browser.close()
    finally:
        srv.shutdown()
    info["frames"] = [str(f) for f in frames]
    info["top"] = top
    return info


# ---------------------------------------------------------------- 2. voice

def speakable(text: str) -> str:
    """Make hype copy pleasant for TTS: spell out acronyms, calm down ALL-CAPS, drop emojis/URLs."""
    t = re.sub(r"https?://\S+", "", text)
    t = re.sub(r"[^\w\s.,!?'’:;()\-–%+]", " ", t)                 # emojis and symbols
    t = t.replace("–", ",").replace("+", " plus ")
    t = re.sub(r"\bAI\b", "A.I.", t)
    t = re.sub(r"\bXP\b", "X.P.", t)
    t = re.sub(r"\bLVL\b", "level", t)
    # ALL-CAPS words read better in lower case (TTS may spell them out); keep a few real acronyms
    keep = {"TV", "PC", "3D", "VR", "AR", "PR", "API", "CEO"}
    t = re.sub(r"\b[A-Z][A-Z'\-]+\b", lambda m: m.group(0) if m.group(0) in keep else m.group(0).lower(), t)
    return re.sub(r"\s+", " ", t).strip()


def narration(info: dict) -> list[str]:
    lines = [f"A.I. level update! A.I. has now reached level {info['levelInt']}! "
             f"That's plus {info['delta']:.1f} levels after today's X.P. drop! Here are today's power ups!"]
    for p in info["top"]:
        lines.append(speakable(p["script"]))
    lines.append(f"Only {info['toGo']} levels until A.I. takes over! Follow for your daily A.I. level up!")
    return [speakable(l) for l in lines]


def load_voice():
    from piper import PiperVoice
    model = VOICE_DIR / f"{VOICE}.onnx"
    if not model.exists():
        VOICE_DIR.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ)
        try:                                   # python.org builds on macOS lack root certificates
            import certifi
            env.setdefault("SSL_CERT_FILE", certifi.where())
        except ImportError:
            pass
        r = subprocess.run([sys.executable, "-m", "piper.download_voices", "--download-dir", str(VOICE_DIR), VOICE],
                           capture_output=True, text=True, env=env)
        if r.returncode != 0:
            raise RuntimeError(f"voice download failed:\n{r.stderr[-800:]}")
    return PiperVoice.load(str(model))


def synth(voice, text: str, path: Path) -> float:
    from piper import SynthesisConfig
    cfg = SynthesisConfig(length_scale=0.86, noise_scale=0.75, noise_w_scale=0.9)   # a bit faster, more lively
    with wave.open(str(path), "wb") as wf:
        voice.synthesize_wav(text, wf, syn_config=cfg)
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / wf.getframerate()


# ---------------------------------------------------------------- 3. music + video

def chiptune(path: Path, seconds: float, sr: int = 44100) -> None:
    """A tiny original arcade loop: square-wave arpeggio over a triangle bass, 150 BPM."""
    bpm, step = 150, 60 / 150 / 4                            # sixteenth notes
    chords = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]   # Am F C G
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    n = int(seconds * sr)
    frames = bytearray()
    for i in range(n):
        t = i / sr
        s = int(t / step)
        chord = chords[(s // 16) % 4]
        note = chord[s % 3] + (12 if (s // 3) % 2 else 0)
        local = t - s * step
        env = max(0.0, 1 - local / step) ** 2
        lead = (1 if math.sin(2 * math.pi * hz(note) * t) >= 0 else -1) * 0.22 * env
        bass_f = hz(chord[0] - 12)
        bass = (2 * abs(2 * ((t * bass_f) % 1) - 1) - 1) * 0.30
        kick = math.sin(2 * math.pi * 55 * t) * math.exp(-local * 30) * 0.5 if s % 4 == 0 else 0
        v = max(-1.0, min(1.0, lead + bass + kick))
        frames += struct.pack("<h", int(v * 32767 * 0.6))
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes(bytes(frames))


def build_video(frames: list[str], wavs: list[Path], durs: list[float], out: Path, work: Path) -> None:
    ff = ffmpeg_exe()
    voice_fx = "aecho=0.8:0.6:35:0.22,acompressor=threshold=-18dB:ratio=4:attack=5:release=80,volume=2.2"
    clips = []
    for k, (img, wav, d) in enumerate(zip(frames, wavs, durs)):
        dur = d + 0.6
        nfr = int(dur * FPS)
        clip = work / f"clip{k}.mp4"
        run([ff, "-y", "-i", img, "-i", str(wav), "-filter_complex",
             f"[0:v]scale=1188:2112,zoompan=z='min(1+0.0009*on,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
             f":d={nfr}:s=1080x1920:fps={FPS},format=yuv420p[v];[1:a]{voice_fx},apad,aresample=44100[a]",
             "-map", "[v]", "-map", "[a]", "-t", f"{dur:.2f}", "-c:v", "libx264", "-preset", "veryfast",
             "-pix_fmt", "yuv420p", "-color_range", "tv",          # standard range: Threads/IG/TikTok-safe
             "-crf", "21", "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", str(clip)])
        clips.append(clip)
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{c.name}'\n" for c in clips))
    joined = work / "joined.mp4"
    run([ff, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined)])

    total = sum(d + 0.6 for d in durs)
    music = work / "music.wav"
    chiptune(music, total + 1)
    run([ff, "-y", "-i", str(joined), "-i", str(music), "-filter_complex",
         f"[1:a]volume=0.16,afade=t=out:st={max(0, total - 1.5):.2f}:d=1.5[m];"
         "[0:a][m]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", str(out)])


# ---------------------------------------------------------------- 4. captions

def captions(info: dict, date: str) -> dict:
    lvl, delta, togo = info["levelInt"], info["delta"], info["toGo"]
    head = f"⚡ AI HAS REACHED LEVEL {lvl} (+{delta:.1f})"
    tail = f"👑 {togo} levels until AI TAKES OVER\n{SITE_URL.replace('https://', '')}"

    def build(limit: int, bullet_len: int, extra: str = "") -> str:
        bullets = [f"▶ {p['headline'][:bullet_len].rstrip()}{'…' if len(p['headline']) > bullet_len else ''}"
                   for p in info["top"]]
        while True:
            body = "\n".join(bullets)
            text = f"{head}\n\nToday's power-ups:\n{body}\n\n{tail}{extra}"
            if len(text) <= limit or not bullets:
                return text
            bullets.pop()

    return {
        "date": date,
        "bluesky": build(290, 52),                                  # Bluesky: 300 graphemes
        "threads": build(490, 80, "\n\n#AI"),                       # Threads: 500 characters
        "instagram": build(2000, 120, "\n\nLink in bio 🎮\n#AI #ArtificialIntelligence #AItools #TechNews #LevelUp"),
        "alt": [f"AI Level card: AI has reached level {lvl}, up {delta:.1f} today. {togo} levels until AI takes over."]
               + [f"{p['rarity']} power-up: {p['headline']}. {p['desc']} This means: {p['means']}." for p in info["top"]],
    }


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="build even if data.js has no drops dated today")
    ap.add_argument("--no-video", action="store_true")
    args = ap.parse_args()

    data = json.loads(re.search(r"=\s*(\{.*\})\s*;\s*$", (ROOT / "data.js").read_text(), re.S).group(1))
    import datetime as dt
    today = dt.date.today().isoformat()
    if not args.force and (data.get("demo") or data.get("updated") != today):
        print(f"No new drops today (data.js updated {data.get('updated')}); nothing to build.")
        return 0

    date = data.get("updated") or today
    out = ROOT / "media" / date
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    print("Capturing frames…")
    info = capture_frames(out)
    images = sorted(out.glob("img-*.jpg"))
    print(f"  {len(images)} images, {len(info['frames'])} video frames")

    video = None
    if not args.no_video:
        print("Recording announcer…")
        voice = load_voice()
        work = out / "work"
        work.mkdir()
        lines = narration(info)
        wavs, durs = [], []
        for k, line in enumerate(lines):
            w = work / f"v{k}.wav"
            durs.append(synth(voice, line, w))
            wavs.append(w)
        print(f"  {len(lines)} lines, {sum(durs):.1f}s of speech")
        print("Rendering video…")
        video = out / "video.mp4"
        build_video(info["frames"], wavs, durs, video, work)
        shutil.rmtree(work)
        print(f"  video.mp4 {video.stat().st_size / 1e6:.1f} MB")
    shutil.rmtree(out / "frames", ignore_errors=True)

    post = captions(info, date)
    post["images"] = [p.name for p in images]
    post["video"] = video.name if video else None
    post["narration"] = narration(info) if video else []
    (out / "post.json").write_text(json.dumps(post, indent=2, ensure_ascii=False))
    latest = ROOT / "media" / "latest.json"
    latest.write_text(json.dumps({"date": date, "dir": f"media/{date}"}, indent=2))
    print(f"Done: media/{date}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
