from __future__ import annotations

import inspect
import re

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

try:
    from pyrogram.enums import ButtonStyle
except Exception:                                   # old build without button styles
    ButtonStyle = None

_STYLE_OK = ButtonStyle is not None and "style" in inspect.signature(InlineKeyboardButton.__init__).parameters

_SC = str.maketrans("abcdefghijklmnopqrstuvwxyz", "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ")
_TAGS = re.compile(r"(<[^>]+>|&[a-zA-Z0-9#]+;)")


def sc(text: str) -> str:
    """'Hello <b>World</b>' -> 'ʜᴇʟʟᴏ <b>ᴡᴏʀʟᴅ</b>'  (tags and &entities untouched)."""
    return "".join(p if i % 2 else p.lower().translate(_SC) for i, p in enumerate(_TAGS.split(text)))


def bq(text: str, expandable: bool = False) -> str:
    return f"<blockquote{' expandable' if expandable else ''}>{text}</blockquote>"


# colours
BLUE, GREEN, RED = "primary", "success", "danger"


def btn(text: str, data: str | None = None, *, url: str | None = None, color: str | None = None,
        raw: bool = False) -> InlineKeyboardButton:
    """raw=True keeps the label exactly as given (anime titles, user text)."""
    label = text if raw else sc(text)
    kw = {}
    if color and _STYLE_OK:
        kw["style"] = getattr(ButtonStyle, color.upper())
    if url:
        return InlineKeyboardButton(label, url=url, **kw)
    return InlineKeyboardButton(label, callback_data=data, **kw)


def kb(*rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([list(r) for r in rows])
