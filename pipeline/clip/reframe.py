"""Reframe a landscape clip to vertical 9:16, centered on the speaker.

Face-aware crop (STRATEGY §8 decision: face-tracking from day 1): we sample the
segment, detect faces with OpenCV's bundled Haar cascade, and crop the 9:16
window around the speaker. No OpenCV / no face found → graceful center crop.

`crop_window` is pure (unit-tested without ffmpeg/opencv); `reframe` runs ffmpeg.
"""
from __future__ import annotations

import subprocess

from ..media import probe

TARGET_W, TARGET_H = 1080, 1920
ASPECT = 9 / 16  # width / height


def crop_window(w: int, h: int, face_cx: float = 0.5, aspect: float = ASPECT) -> tuple[int, int, int, int]:
    """Return an even (cw, ch, cx, cy) crop of WxH at the target aspect, centered
    horizontally on `face_cx` (0..1)."""
    if w <= 0 or h <= 0:
        return 0, 0, 0, 0
    if w / h >= aspect:                       # landscape → crop a vertical slice
        ch = h
        cw = min(w, int(round(h * aspect)))
        cx = int(round(face_cx * w - cw / 2))
        cx = max(0, min(cx, w - cw))
        cy = 0
    else:                                     # tall/square → crop height
        cw = w
        ch = min(h, int(round(w / aspect)))
        cx = 0
        cy = max(0, (h - ch) // 2)
    cw -= cw % 2
    ch -= ch % 2
    return cw, ch, cx, cy


def detect_face_center_x(src: str, start: float, end: float, samples: int = 15) -> float | None:
    """Median normalized x (0..1) of the dominant face across the segment, or
    None if OpenCV is unavailable or no faces are found."""
    try:
        import cv2
    except Exception:
        return None
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        return None
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    xs: list[float] = []
    span = max(0.1, end - start)
    try:
        for i in range(samples):
            t = start + span * (i + 0.5) / samples
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
            ok, frame = cap.read()
            if not ok:
                continue
            fh, fw = frame.shape[:2]
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(gray, 1.2, 5, minSize=(60, 60))
            if len(faces):
                x, y, bw, bh = max(faces, key=lambda f: f[2] * f[3])
                xs.append((x + bw / 2) / fw)
    finally:
        cap.release()
    if not xs:
        return None
    xs.sort()
    return xs[len(xs) // 2]


def reframe(src: str, start: float, end: float, out: str) -> tuple[str, bool]:
    """Cut [start,end] from `src` and render a 1080x1920 clip centered on the
    speaker. Returns (out_path, used_face_tracking)."""
    probe.require("ffmpeg")
    w, h = probe.dimensions(src)
    face_cx = detect_face_center_x(src, start, end)
    cw, ch, cx, cy = crop_window(w, h, face_cx if face_cx is not None else 0.5)
    vf = f"crop={cw}:{ch}:{cx}:{cy},scale={TARGET_W}:{TARGET_H},setsar=1"
    cmd = ["ffmpeg", "-y", "-ss", str(start), "-to", str(end), "-i", src,
           "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", "23",
           "-c:a", "aac", "-b:a", "160k", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"reframe failed:\n{r.stderr[-600:]}")
    return out, face_cx is not None
