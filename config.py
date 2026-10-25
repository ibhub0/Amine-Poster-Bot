from __future__ import annotations

import os
import re
from pathlib import Path


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _int(name: str, default: int) -> int:
    try:
        return int(_get(name, str(default)))
    except ValueError:
        return default


def _ids(name: str) -> set[int]:
    return {int(x) for x in re.split(r"[,\s]+", _get(name)) if x.isdigit()}


BASE_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------- telegram (Kurigram)
API_ID = _int("API_ID", "")                                  # https://my.telegram.org
API_HASH = _get("API_HASH", "")
BOT_TOKEN = _get("BOT_TOKEN", "") or _get("TELEGRAM_BOT_TOKEN")  # @BotFather
ALLOWED_USERS = _ids("ALLOWED_USERS")                       # comma separated ids; empty = everybody

# ---------------------------------------------------------------- links + images (/start, /help)
MAIN_CHANNEL_URL = _get("MAIN_CHANNEL_URL", "https://t.me/cantarellabots")
SUPPORT_URL = _get("SUPPORT_URL", "https://t.me/CantarellaBotschat")

# /start and /help are sent as a photo, one picked at random from this list
MENU_IMAGES = [
    "https://files.catbox.moe/5oonsm.jpg",
    "https://files.catbox.moe/9ufgme.jpg",
    "https://files.catbox.moe/4b8jvw.jpg",
    "https://files.catbox.moe/bli70r.jpg",
    "https://files.catbox.moe/uce0lw.jpg",
    "https://files.catbox.moe/is7q4q.jpg",
]

# ---------------------------------------------------------------- posters
BRAND_TOP = _get("BRAND_TOP", "ANI")                        # brand on styles 8 and 13
BRAND_BOTTOM = _get("BRAND_BOTTOM", "CROX")
USE_CHARACTER_PNG = _get("USE_CHARACTER_PNG", "1") != "0"   # styles 1, 2, 4, 5: try transparent fanart.tv PNGs
USE_ANILIST_CUTOUT = _get("USE_ANILIST_CUTOUT", "0") == "1"  # also offer an AniList character cut-out (rembg). off = fanart.tv only
FANART_CANDIDATES = _int("FANART_CANDIDATES", 15)           # how many fanart.tv PNGs to offer (styles 1, 2, 4, 5). was 6
POSTER_CHOICES = _int("POSTER_CHOICES", 12)                 # most AniList posters to cycle through (styles 3, 6, 7, 9, 10, 11, 13, 14)
BANNER_CHOICES = _int("BANNER_CHOICES", 12)                 # most AniList banners to cycle through (styles 8, 12)

# small art is grown to a "medium" size (aspect ratio kept, never shrunk). This is the working size
# the poster is drawn from - it has nothing to do with the Telegram upload size.
CHAR_MIN_HEIGHT = _int("CHAR_MIN_HEIGHT", 1400)             # transparent character PNGs (styles 1-7): at least this tall
COVER_MIN_HEIGHT = _int("COVER_MIN_HEIGHT", 1350)           # portrait poster / cover art (styles 8-14)
BANNER_MIN_WIDTH = _int("BANNER_MIN_WIDTH", 1920)           # landscape banner art (styles 8-14)
# a character PNG that comes out short (wide / low image, e.g. a mecha with a long weapon) is grown - same ratio -
# until it is at least CHAR_MEDIUM_FILL of the style's art height; it may use up to CHAR_WIDE_STRETCH x the normal width.
try:
    CHAR_MEDIUM_FILL = min(1.0, max(0.3, float(_get("CHAR_MEDIUM_FILL", "0.75"))))
    CHAR_WIDE_STRETCH = max(1.0, float(_get("CHAR_WIDE_STRETCH", "1.35")))
except ValueError:
    CHAR_MEDIUM_FILL, CHAR_WIDE_STRETCH = 0.75, 1.35
try:
    MAX_UPSCALE = max(1.0, float(_get("MAX_UPSCALE", "4")))  # never enlarge more than this many times
except ValueError:
    MAX_UPSCALE = 4.0
RENDER_WORKERS = _int("RENDER_WORKERS", 2)                  # posters rendered at the same time
SAMPLE_ANIME_ID = _int("SAMPLE_ANIME_ID", 1535)             # AniList id used for the /styles previews
SAMPLES_DIR = BASE_DIR / "samples"                          # samples/style_N.jpg = your own previews

# ---------------------------------------------------------------- character art keys (optional)
FANART_API_KEY = _get("FANART_API_KEY", "")                     # fanart.tv
TMDB_API_KEY = _get("TMDB_API_KEY", "")                         # fallback to find the TVDB id
REMBG_MODEL = _get("REMBG_MODEL")                           # empty = template default (isnet-anime)

# ---------------------------------------------------------------- channels (/addchnl, post button, branding)
# where users' channels are kept. Heroku wipes local files on every restart -> set MONGO_URI there (needs `motor`).
DATA_DIR = Path(_get("DATA_DIR") or (BASE_DIR / "data"))
MONGO_URI = _get("MONGO_URI", "")                               # empty = a json file in DATA_DIR
MONGO_DB = _get("MONGO_DB", "poster_bot")
MAX_CHANNELS = _int("MAX_CHANNELS", 5)                      # channels one user may add
# the bot must hold ALL of these admin rights in a channel before it is accepted (override: comma separated names)
_DEFAULT_RIGHTS = ("can_manage_chat", "can_post_messages", "can_edit_messages", "can_delete_messages",
                   "can_invite_users", "can_change_info", "can_manage_video_chats", "can_promote_members")
CHANNEL_RIGHTS = tuple(x for x in re.split(r"[,\s]+", _get("CHANNEL_REQUIRED_RIGHTS")) if x) or _DEFAULT_RIGHTS

# ---------------------------------------------------------------- server / logging
PORT = _int("PORT", 0)                                      # >0 starts a tiny health-check server
LOG_LEVEL = _get("LOG_LEVEL", "INFO")

# ---------------------------------------------------------------- fonts
FONT_DIR = BASE_DIR / "fonts"

# ---------------------------------------------------------------- values the (unmodified) templates read
os.environ.setdefault("POSTER_FONT_DIR", str(FONT_DIR))
for _k, _v in (("FANART_API_KEY", FANART_API_KEY), ("TMDB_API_KEY", TMDB_API_KEY), ("REMBG_MODEL", REMBG_MODEL)):
    if _v:                                                  # empty -> keep the template's own default
        os.environ[_k] = _v
