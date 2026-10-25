"""
watermark.py - stamps every poster with the "Cantarella Bots" mark.

Three layers, all applied by apply() as the very last step of every render (dataset._render_sync),
so every poster, every download (jpg / png) and every /styles preview carries them:

  1. SEALED BRAND   the brand text is stored AES-256-GCM encrypted. It can only be read with
                    WATERMARK_KEY (a secret that lives in your server environment, never in the repo).
                    A changed / swapped blob fails the GCM check and the bot REFUSES to render.
  2. VISIBLE MARK   a faint diagonal pattern over the whole picture (cannot be cropped away) plus a
                    badge in the bottom-right corner.
  3. INVISIBLE MARK a keyed spread-spectrum signature spread over the whole image. It survives
                    PNG and normal JPEG / Telegram re-compression and lets YOU prove a poster is yours:
                        python watermark.py verify poster.png

Tools
    python watermark.py newkey                 print a fresh random WATERMARK_KEY
    python watermark.py seal "TEXT"            print the sealed blob for TEXT (uses WATERMARK_KEY)
    python watermark.py verify FILE [FILE...]  check whether a picture carries your invisible mark
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import math
import os
import secrets
import sys
from functools import lru_cache

import numpy as np
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import config


class WatermarkError(RuntimeError):
    """Raised when the watermark cannot be applied -> the poster is NOT delivered."""


# base64( nonce[12] + AES-GCM ciphertext + tag ) of the brand text, sealed with WATERMARK_KEY
_SEALED = "dHKLXmx1DN/XEoENKNMUiKw3yShsgsBMQ3gKhJZJW3K9MHL00t7kJF8uVA=="
_AAD = b"cantarella-bots/watermark/v1"

_AMPLITUDE = 3          # invisible mark strength (0-255 luminance steps)
_BLOCK = 4              # invisible mark block size in px (bigger blocks survive JPEG better)
_Z_MIN = 7.0            # verify(): z-score above this = mark present


# ======================================================================
# sealed brand
# ======================================================================
def _master() -> bytes:
    key = config.WATERMARK_KEY
    if not key:
        raise WatermarkError("WATERMARK_KEY is not set - refusing to render un-watermarked posters.")
    return hashlib.sha256(key.encode()).digest()


@lru_cache(maxsize=1)
def _brand() -> str:
    try:
        raw = base64.b64decode(_SEALED)
        return AESGCM(_master()).decrypt(raw[:12], raw[12:], _AAD).decode("utf-8")
    except (InvalidTag, ValueError):
        raise WatermarkError("sealed watermark failed verification (wrong WATERMARK_KEY or tampered blob).")


def self_check() -> str:
    """Call once at start-up: fails fast instead of on the first user's poster."""
    return _brand()


# ======================================================================
# visible mark
# ======================================================================
def _font(size: int):
    for p in (config.FONT_DIR / "Poppins-ExtraBold.ttf", config.BASE_DIR / "Templates" / "fonts" / "Poppins-ExtraBold.ttf",
              "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(str(p), size)
        except Exception:
            continue
    return ImageFont.load_default()


@lru_cache(maxsize=6)
def _tile_layer(w: int, h: int, text: str) -> Image.Image:
    """Faint rotated repeating text over the whole picture (light fill + dark edge = visible on any art)."""
    k = w / 1920
    f = _font(max(10, int(26 * k)))
    label = f"{text}   \u2726   "
    tw = max(1, int(f.getlength(label)))
    big = int(math.hypot(w, h)) + 2 * tw
    canvas = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    row_gap = int(150 * k)
    for i, y in enumerate(range(0, big, row_gap)):
        for x in range(-tw + (i % 2) * tw // 2, big, tw):
            d.text((x, y), label, font=f, anchor="lm", fill=(255, 255, 255, 38),
                   stroke_width=max(1, int(k)), stroke_fill=(0, 0, 0, 30))
    canvas = canvas.rotate(24, resample=Image.BICUBIC)
    left, top = (big - w) // 2, (big - h) // 2
    return canvas.crop((left, top, left + w, top + h))


def _badge(base: Image.Image, text: str):
    k = base.width / 1920
    f = _font(max(11, int(22 * k)))
    label = f"{text}"
    pad_x, pad_y, gap = int(18 * k), int(10 * k), int(10 * k)
    tw = f.getlength(label)
    bh = int(f.size * 1.0) + 2 * pad_y
    icon = int(bh * 0.46)
    bw = int(pad_x + icon + gap + tw + pad_x)
    mx = int(26 * k)
    x1, y1 = base.width - mx, base.height - mx
    x0, y0 = x1 - bw, y1 - bh
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((x0, y0, x1, y1), radius=bh // 2, fill=(14, 18, 58, 168), outline=(255, 255, 255, 70),
                        width=max(1, int(k)))
    cx, cy, r = x0 + pad_x + icon // 2, (y0 + y1) // 2, icon // 2
    pts = []
    for i in range(8):                                   # 4-point sparkle
        a = -math.pi / 2 + i * math.pi / 4
        rad = r if i % 2 == 0 else r * 0.38
        pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    d.polygon(pts, fill=(255, 138, 174, 235))
    d.text((x0 + pad_x + icon + gap, cy), label, font=f, anchor="lm", fill=(255, 255, 255, 235))
    base.alpha_composite(layer)


# ======================================================================
# invisible mark (keyed spread-spectrum, block-constant so it survives JPEG)
# ======================================================================
@lru_cache(maxsize=4)
def _pattern(w: int, h: int) -> np.ndarray:
    seed = int.from_bytes(hmac.new(_master(), f"pattern/{w}x{h}".encode(), hashlib.sha256).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    bh, bw = -(-h // _BLOCK), -(-w // _BLOCK)
    p = rng.choice(np.array([-1.0, 1.0], dtype=np.float32), size=(bh, bw))
    return np.kron(p, np.ones((_BLOCK, _BLOCK), dtype=np.float32))[:h, :w]


def _embed(img: Image.Image) -> Image.Image:
    w, h = img.size
    y, cb, cr = img.convert("YCbCr").split()
    ya = np.asarray(y, dtype=np.float32) + _AMPLITUDE * _pattern(w, h)
    y2 = Image.fromarray(np.clip(np.rint(ya), 0, 255).astype(np.uint8), "L")
    return Image.merge("YCbCr", (y2, cb, cr)).convert("RGB")


def detect(img: Image.Image) -> float:
    """z-score of the invisible mark (needs WATERMARK_KEY and the original pixel size)."""
    w, h = img.size
    y = img.convert("L")
    res = np.asarray(y, dtype=np.float32) - np.asarray(y.filter(ImageFilter.BoxBlur(10)), dtype=np.float32)
    p = _pattern(w, h)
    bh, bw = h // _BLOCK, w // _BLOCK                      # one number per block
    r = res[:bh * _BLOCK, :bw * _BLOCK].reshape(bh, _BLOCK, bw, _BLOCK).mean(axis=(1, 3))
    q = p[:bh * _BLOCK, :bw * _BLOCK].reshape(bh, _BLOCK, bw, _BLOCK).mean(axis=(1, 3))
    n = r.size
    return float((r * q).sum() / (math.sqrt(n) * (r.std() + 1e-6)))


# ======================================================================
# public API
# ======================================================================
def apply(img: Image.Image) -> Image.Image:
    """RGB image in -> watermarked RGB image out. Raises WatermarkError (poster not delivered)."""
    text = _brand()
    base = img.convert("RGBA")
    base.alpha_composite(_tile_layer(base.width, base.height, text))
    _badge(base, text)
    return _embed(base.convert("RGB"))


# ======================================================================
# command line tools
# ======================================================================
def _cli(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "newkey":
        print(secrets.token_urlsafe(32))
        return 0
    if cmd == "seal" and len(argv) > 2:
        nonce = os.urandom(12)
        blob = nonce + AESGCM(_master()).encrypt(nonce, argv[2].encode("utf-8"), _AAD)
        print(base64.b64encode(blob).decode())
        return 0
    if cmd == "verify" and len(argv) > 2:
        for path in argv[2:]:
            z = detect(Image.open(path).convert("RGB"))
            print(f"{path}: z={z:6.1f}  ->  {'MARK FOUND' if z >= _Z_MIN else 'no mark (or resized / cropped)'}")
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(_cli(sys.argv))
