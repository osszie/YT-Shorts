"""Reframe a landscape clip to vertical 9:16, following the speaker.

Dynamic face tracking (STRATEGY §8): we cut the segment, then compute a smoothed
face-position track with OpenCV's bundled Haar cascade. The Remotion `Clip`
composition uses that track to PAN the crop frame-by-frame (smooth follow). The
FFmpeg fallback does a single face-centered crop (median of the track).

No OpenCV / no faces → empty track → centered framing. `crop_window` is pure and
unit-tested; everything else shells out to ffmpeg/opencv.
"""
from __future__ import annotations

import subprocess

from ..media import probe

TARGET_W, TARGET_H = 1080, 1920
ASPECT = 9 / 16  # width / height


def crop_window(w: int, h: int, face_cx: float = 0.5, aspect: float = ASPECT) -> tuple[int, int, int, int]:
    """Even (cw, ch, cx, cy) crop of WxH at the target aspect, centered on face_cx."""
    if w <= 0 or h <= 0:
        return 0, 0, 0, 0
    if w / h >= aspect:
        ch = h
        cw = min(w, int(round(h * aspect)))
        cx = max(0, min(int(round(face_cx * w - cw / 2)), w - cw))
        cy = 0
    else:
        cw = w
        ch = min(h, int(round(w / aspect)))
        cx = 0
        cy = max(0, (h - ch) // 2)
    cw -= cw % 2
    ch -= ch % 2
    return cw, ch, cx, cy


def face_track(video: str, step: float = 0.25, smooth: int = 5) -> list[dict]:
    """Smoothed [{t, cx}] track of the dominant face's normalized x over the clip.

    Empty if OpenCV is unavailable or no faces are found.
    """
    try:
        import cv2
    except Exception:
        return []
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        return []
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        n = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        duration = (n / fps) if n else 0.0
        raw: list[tuple[float, float]] = []
        t = 0.0
        while duration == 0.0 or t < duration:
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
            ok, frame = cap.read()
            if not ok:
                break
            fh, fw = frame.shape[:2]
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(gray, 1.2, 5, minSize=(60, 60))
            if len(faces):
                x, _, bw, _ = max(faces, key=lambda f: f[2] * f[3])
                raw.append((round(t, 2), (x + bw / 2) / fw))
            t += step
    finally:
        cap.release()
    if not raw:
        return []
    # Moving-average smoothing on cx.
    cxs = [c for _, c in raw]
    out = []
    half = max(1, smooth) // 2
    last_t = None
    for i, (tt, _) in enumerate(raw):
        lo, hi = max(0, i - half), min(len(cxs), i + half + 1)
        cx = sum(cxs[lo:hi]) / (hi - lo)
        if last_t is not None and tt <= last_t:
            tt = last_t + 0.001       # keep strictly increasing for interpolation
        out.append({"t": round(tt, 3), "cx": round(cx, 4)})
        last_t = tt
    return out


def median_cx(track: list[dict]) -> float:
    if not track:
        return 0.5
    xs = sorted(p["cx"] for p in track)
    return xs[len(xs) // 2]


def cut(src: str, start: float, end: float, out: str) -> str:
    """Cut [start,end] from src into a re-encoded segment (frame-accurate)."""
    probe.require("ffmpeg")
    cmd = ["ffmpeg", "-y", "-ss", str(start), "-to", str(end), "-i", src,
           "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-c:a", "aac", "-b:a", "160k", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"clip cut failed:\n{r.stderr[-500:]}")
    return out


def static_crop(segment: str, out: str, face_cx: float = 0.5) -> str:
    """Single face-centered 9:16 crop of an already-cut segment (FFmpeg fallback)."""
    probe.require("ffmpeg")
    w, h = probe.dimensions(segment)
    cw, ch, cx, cy = crop_window(w, h, face_cx)
    vf = f"crop={cw}:{ch}:{cx}:{cy},scale={TARGET_W}:{TARGET_H},setsar=1"
    cmd = ["ffmpeg", "-y", "-i", segment, "-vf", vf, "-c:v", "libx264",
           "-preset", "fast", "-crf", "23", "-c:a", "copy", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"static crop failed:\n{r.stderr[-500:]}")
    return out


def reframe(src: str, start: float, end: float, out: str) -> tuple[str, bool]:
    """Convenience (and FFmpeg fallback): cut + single face-centered crop."""
    import os
    seg = out + ".seg.mp4"
    cut(src, start, end, seg)
    track = face_track(seg)
    static_crop(seg, out, median_cx(track))
    try:
        os.remove(seg)
    except OSError:
        pass
    return out, bool(track)
