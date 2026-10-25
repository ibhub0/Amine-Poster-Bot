"""chnl.py - channel help: /addchnl  /removechnl  /mychnls   +   the 📣 post to channel button   +   poster branding

  /addchnl     user adds a channel. The bot only accepts it when
                 - the bot is an admin there with ALL rights in config.CHANNEL_RIGHTS (full admin)
                 - the user is the owner / an admin of that channel too (nobody can post into somebody else's channel)
  /removechnl  remove a channel
  /mychnls     list channels (live rights check) and remove them
  📣 button    under every poster: poster -> post text -> inline buttons -> preview -> sent to the channel
  🏷 branding  in the options of every poster: the user's channel branding text. It is printed on EVERY poster, written
               in that poster's own typography and colours (chname.py). The first channel a user adds sets it.

The post text keeps its Telegram formatting exactly: the entities of the message the user sends (bold, italic, underline,
strike, spoiler, code, links, blockquote, expandable blockquote, custom emoji) are copied as they are, so any unicode
font the user pastes in works too.
Buttons: one per line  `Text - https://link`  and `Text 1 - https://a | Text 2 - https://b` for two in one row.
"""
from __future__ import annotations

import asyncio
import html
import logging
import re
from urllib.parse import urlparse

from pyrogram import enums, filters
from pyrogram.errors import RPCError
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.types import InlineKeyboardMarkup

import chname
import chstore
import cmds
import config
from ui import BLUE, GREEN, RED, bq, btn, kb, sc

log = logging.getLogger("chnl")

CAPTION_MAX = 1024                       # telegram's caption limit; longer text is sent as a second message
MAX_ROWS, MAX_PER_ROW = 10, 4
MODES = ("addchnl", "branding", "ptext", "pbtns")

RIGHT_LABELS = {
    "can_manage_chat": "manage channel",
    "can_post_messages": "post messages",
    "can_edit_messages": "edit messages of others",
    "can_delete_messages": "delete messages of others",
    "can_invite_users": "add subscribers / invite users",
    "can_change_info": "change channel info",
    "can_manage_video_chats": "manage live streams",
    "can_promote_members": "add new admins",
    "can_pin_messages": "pin messages",
}


# ======================================================================
# checking a channel
# ======================================================================
def parse_ref(text: str):
    """@name / t.me/name / t.me/c/123/4 / -1001234567890  ->  something get_chat() takes (None = not understood)"""
    parts = (text or "").split()
    if len(parts) != 1:                                    # a sentence is not a channel
        return None
    t = parts[0]
    if re.fullmatch(r"-?\d{5,}", t):
        return int(t)
    m = re.match(r"^(?:https?://)?(?:t|telegram)\.me/c/(\d+)", t, re.I)
    if m:
        return int("-100" + m.group(1))
    m = re.match(r"^(?:https?://)?(?:t|telegram)\.me/([A-Za-z][\w]{3,})", t, re.I)
    if m and m.group(1).lower() not in ("joinchat", "addlist", "s"):
        return m.group(1)
    m = re.fullmatch(r"@?([A-Za-z][\w]{3,})", t)
    return m.group(1) if m else None


def _label(right: str) -> str:
    return RIGHT_LABELS.get(right, right.replace("can_", "").replace("_", " "))


async def bot_missing_rights(client, chat_id: int) -> tuple[bool, list[str]]:
    """-> (bot is an administrator there, labels of the required rights it does NOT have)"""
    me = await client.get_chat_member(chat_id, "me")
    if me.status != enums.ChatMemberStatus.ADMINISTRATOR:
        return False, [_label(r) for r in config.CHANNEL_RIGHTS]
    priv = me.privileges
    return True, [_label(r) for r in config.CHANNEL_RIGHTS if not getattr(priv, r, False)]


async def verify(client, user_id: int, ref) -> tuple[dict | None, str | None]:
    """Everything that must be true before a channel is accepted / posted into.
    -> ({"id", "title", "username"}, None)  or  (None, <html error text>)"""
    try:
        chat = await client.get_chat(ref)
    except (RPCError, KeyError, ValueError):
        return None, bq(sc("😕 i can't find that channel.\n"
                           "add me to it as an admin first, then send its @username, its link or forward a post from it."))
    if chat.type != enums.ChatType.CHANNEL:
        return None, bq(sc("😕 that is not a channel. only channels can be added."))
    title = html.escape(chat.title or "channel")

    try:
        is_admin, missing = await bot_missing_rights(client, chat.id)
    except (RPCError, KeyError, ValueError):
        return None, bq(sc("⚠️ i'm not in ") + f"<b>{title}</b>" + sc(". add me as an admin with all rights, then try again."))
    if not is_admin:
        return None, bq(sc("⚠️ i'm not an admin in ") + f"<b>{title}</b>" + sc(". make me an admin with all rights, then try again."))
    if missing:
        return None, bq(sc("⚠️ i'm an admin in ") + f"<b>{title}</b>" + sc(", but i need FULL admin rights. missing:\n") +
                        "\n".join("• " + sc(m) for m in missing) + "\n" + sc("turn them on and send the channel again."))

    try:                                                      # the user must be allowed to post there
        um = await client.get_chat_member(chat.id, user_id)
    except (RPCError, KeyError, ValueError):
        return None, bq(sc("⛔ you are not an admin of ") + f"<b>{title}</b>" + sc(". only its admins can use it with me."))
    if um.status == enums.ChatMemberStatus.OWNER:
        pass
    elif um.status == enums.ChatMemberStatus.ADMINISTRATOR and getattr(um.privileges, "can_post_messages", False):
        pass
    else:
        return None, bq(sc("⛔ you must be the owner or an admin with the right to post in ") + f"<b>{title}</b>" + sc("."))
    return {"id": chat.id, "title": chat.title or "channel", "username": chat.username}, None


def post_link(chat_id: int, username: str | None, msg_id: int) -> str:
    if username:
        return f"https://t.me/{username}/{msg_id}"
    return f"https://t.me/c/{str(chat_id).replace('-100', '', 1)}/{msg_id}"


# ======================================================================
# buttons typed by the user
# ======================================================================
def _norm_url(u: str) -> str | None:
    u = u.strip()
    if u.startswith("@") and len(u) > 4:
        u = "https://t.me/" + u[1:]
    elif re.match(r"^(t|telegram)\.me/", u, re.I):
        u = "https://" + u
    elif not re.match(r"^[a-z][a-z0-9+.\-]*://", u, re.I) and "." in u and " " not in u:
        u = "https://" + u
    p = urlparse(u)
    if p.scheme == "tg":
        return u if p.netloc else None
    if p.scheme not in ("http", "https") or "." not in p.netloc or " " in u:
        return None
    return u


def parse_buttons(text: str) -> tuple[list[list[tuple[str, str]]], list[str]]:
    """'Watch - https://a.com | Join - t.me/x' per line  ->  (rows of (label, url), problems)"""
    rows: list[list[tuple[str, str]]] = []
    errors: list[str] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        row = []
        for part in re.split(r"\s+\|\s+", line):
            m = re.match(r"^(.*\S)\s+[-–—]\s+(\S+)$", part.strip())
            url = _norm_url(m.group(2)) if m else None
            if not m or not url:
                errors.append(line if len(line) < 60 else line[:57] + "…")
                row = []
                break
            label = m.group(1).strip()
            if len(label) > 60:
                errors.append(label[:40] + "… (button text is too long)")
                row = []
                break
            row.append((label, url))
        if row:
            if len(row) > MAX_PER_ROW:
                errors.append(f"max {MAX_PER_ROW} buttons in one row")
            else:
                rows.append(row)
    if len(rows) > MAX_ROWS:
        errors.append(f"max {MAX_ROWS} rows of buttons")
    return rows, errors


def to_markup(rows) -> InlineKeyboardMarkup | None:
    if not rows:
        return None
    return InlineKeyboardMarkup([[btn(label, url=url, raw=True) for label, url in row] for row in rows])


# ======================================================================
# sending the post (used for the preview AND for the channel - so they are identical)
# ======================================================================
def _strip_custom_emoji(ents):
    return [e for e in (ents or []) if e.type != enums.MessageEntityType.CUSTOM_EMOJI] or None


async def publish(client, chat_id: int, jpg: bytes, text: str, ents, markup) -> list:
    """photo + text (with the user's own entities) + url buttons.
    text longer than a caption allows -> the photo goes first, the text (with the buttons) as the next message."""
    async def go(t: str, e):
        out = []
        if t and len(t) > CAPTION_MAX:
            out.append(await client.send_photo(chat_id, cmds._bio(jpg, "poster.jpg")))
            out.append(await client.send_message(chat_id, t, entities=e, parse_mode=enums.ParseMode.DISABLED,
                                                 reply_markup=markup, disable_web_page_preview=True))
        else:
            out.append(await client.send_photo(chat_id, cmds._bio(jpg, "poster.jpg"), caption=t or None,
                                               caption_entities=e, parse_mode=enums.ParseMode.DISABLED,
                                               reply_markup=markup))
        return out
    try:
        return await go(text, ents or None)
    except RPCError:
        if ents and any(e.type == enums.MessageEntityType.CUSTOM_EMOJI for e in ents):   # bots can't always use them
            return await go(text, _strip_custom_emoji(ents))
        raise


# ======================================================================
# keyboards + texts
# ======================================================================
def _cancel_kb(*extra):
    return kb(*extra, [btn("✖️ cancel", "ch_cancel", color=RED)])


def _chan_line(i: int, c: dict, status: str) -> str:
    who = f" · @{c['username']}" if c.get("username") else ""
    return f"<b>{i}. {html.escape(c['title'])}</b>{html.escape(who)}   {status}"


async def _statuses(client, chans: list[dict]) -> list[str]:
    async def one(c):
        try:
            is_admin, missing = await bot_missing_rights(client, c["id"])
            return "✅" + sc(" full rights") if is_admin and not missing else "⚠️" + sc(" missing rights")
        except Exception:
            return "⚠️" + sc(" can't check")
    return list(await asyncio.gather(*[one(c) for c in chans]))


async def _list_view(client, uid: int):
    chans = await chstore.channels(uid)
    if not chans:
        return (bq(sc("📣 you have no channels yet.\nadd one with /addchnl - then you can post your posters to it "
                      "with the 📣 button under every poster.")),
                kb([btn("➕ add channel", "ch_add", color=GREEN)]))
    stats = await _statuses(client, chans)
    body = "\n".join(_chan_line(i, c, stats[i - 1]) for i, c in enumerate(chans, 1))
    brand = await chstore.get_brand(uid)
    text = (bq(sc(f"📣 your channels ({len(chans)}/{config.MAX_CHANNELS})") + "\n\n" + body) + "\n" +
            bq(sc("🏷 poster branding: ") + (f"<b>{html.escape(brand)}</b>" if brand else sc("not set")) + "\n" +
               sc("change it in ⚙️ options under any poster.")))
    rows = [[btn(f"🗑 {i}. {c['title']}"[:40], f"ch_rm:{c['id']}", raw=True, color=RED)] for i, c in enumerate(chans, 1)]
    rows.append([btn("➕ add channel", "ch_add", color=GREEN)])
    return text, kb(*rows)


async def _send_list(client, uid: int, chat_id: int, edit=None):
    text, markup = await _list_view(client, uid)
    if edit is not None:
        await cmds._edit(edit, text, markup)
    else:
        await client.send_message(chat_id, text, reply_markup=markup)


ADD_TEXT = bq(
    sc("➕ add a channel\n\n"
       "1️⃣ add me to your channel as an admin with ALL rights (full admin)\n"
       "2️⃣ send me the channel here: its @username, its link, or forward any post from it\n\n"
       "you have to be an admin of that channel too."))


# ======================================================================
# /addchnl  /removechnl  /mychnls
# ======================================================================
async def _add_channel(client, uid: int, cid: int, ref) -> None:
    ud = cmds._ud(uid)
    chans = await chstore.channels(uid)
    if len(chans) >= config.MAX_CHANNELS and not any(isinstance(ref, int) and c["id"] == ref for c in chans):
        await client.send_message(cid, bq(sc(f"⚠️ you can add up to {config.MAX_CHANNELS} channels. remove one first with /removechnl.")))
        return
    wait = await client.send_message(cid, bq(sc("🔎 checking the channel and my rights…")))
    info, err = await verify(client, uid, ref)
    if err:
        ud["await"] = "addchnl"                                  # let them fix it and send again
        await cmds._edit(wait, err, _cancel_kb())
        return
    await chstore.add_channel(uid, info)
    ud["await"] = None
    note = ""
    if not await chstore.get_brand(uid):                          # first channel -> its name becomes the poster branding
        brand = chname.clean(info["title"])
        if brand:
            await chstore.set_brand(uid, brand)
            note = ("\n" + sc("🏷 poster branding set to ") + f"<b>{html.escape(brand)}</b>. " +
                    sc("change it anytime in ⚙️ options under any poster."))
    await cmds._edit(wait, bq(sc("✅ channel added\n") + f"<b>{html.escape(info['title'])}</b>\n" +
                              sc("i have full admin rights there.") + note + "\n\n" +
                              sc("make a poster and press 📣 post to channel.")),
                     kb([btn("📣 my channels", "ch_list", color=BLUE)]))


async def cmd_addchnl(client, message):
    uid, cid = message.from_user.id, message.chat.id
    ud = cmds._ud(uid)
    args = message.command[1:] if message.command else []
    if args:
        ref = parse_ref(args[0])
        if ref is None:
            await message.reply_text(ADD_TEXT, reply_markup=_cancel_kb())
            ud["await"] = "addchnl"
            return
        await _add_channel(client, uid, cid, ref)
        return
    ud["await"] = "addchnl"
    await message.reply_text(ADD_TEXT, reply_markup=_cancel_kb())


def _find(chans: list[dict], token: str) -> dict | None:
    token = token.strip().lstrip("@")
    if token.lstrip("-").isdigit():
        n = int(token)
        if 1 <= n <= len(chans):
            return chans[n - 1]
        return next((c for c in chans if c["id"] == n), None)
    return next((c for c in chans if (c.get("username") or "").lower() == token.lower()), None)


async def _remove_view(uid: int):
    chans = await chstore.channels(uid)
    if not chans:
        return bq(sc("📣 you have no channels to remove.")), kb([btn("➕ add channel", "ch_add", color=GREEN)])
    rows = [[btn(f"🗑 {c['title']}"[:40], f"ch_rmv:{c['id']}", raw=True, color=RED)] for c in chans]
    rows.append([btn("✖️ close", "ch_cancel", color=BLUE)])
    return bq(sc("🗑 which channel should i remove?")), kb(*rows)


async def cmd_removechnl(client, message):
    uid = message.from_user.id
    args = message.command[1:] if message.command else []
    if args:
        chans = await chstore.channels(uid)
        c = _find(chans, args[0])
        if not c:
            await message.reply_text(bq(sc("😕 i don't have that channel. use /mychnls to see your channels.")))
            return
        await chstore.remove_channel(uid, c["id"])
        await message.reply_text(bq(sc("🗑 removed ") + f"<b>{html.escape(c['title'])}</b>"))
        return
    text, markup = await _remove_view(uid)
    await message.reply_text(text, reply_markup=markup)


async def cmd_mychnls(client, message):
    await _send_list(client, message.from_user.id, message.chat.id)


# ======================================================================
# posting a poster to a channel  (the 📣 button under every poster)
# ======================================================================
def _pf(uid: int) -> dict:
    return cmds._ud(uid).setdefault("pf", {})


def _post_head(ud: dict, ch: dict | None) -> str:
    a = ud.get("anime")
    bits = []
    if a is not None:
        bits.append(f"🎬 <b>{html.escape(a.title)}</b> · " + sc(f"style {ud.get('style')}"))
    if ch:
        bits.append(sc("📣 ") + f"<b>{html.escape(ch['title'])}</b>")
    return "\n".join(bits)


async def start_post(client, uid: int, cid: int) -> None:
    ud = cmds._ud(uid)
    last = ud.get("last")
    if last is None or ud.get("anime") is None:
        await client.send_message(cid, bq(sc("🖼 make a poster first: send an anime name (or /poster naruto), pick a style, "
                                             "then press 📣 post to channel.")))
        return
    chans = await chstore.channels(uid)
    if not chans:
        await client.send_message(cid, bq(sc("📣 add a channel first with /addchnl - i need to be a full admin there.")),
                                  reply_markup=kb([btn("➕ add channel", "ch_add", color=GREEN)]))
        return
    ud["pf"] = {"jpg": last.jpg, "text": "", "ents": None, "rows": [], "msgs": []}
    ud["await"] = None
    if len(chans) == 1:
        ud["pf"]["chat_id"] = chans[0]["id"]
        await _ask_text(client, uid, cid)
        return
    rows = [[btn(c["title"][:40], f"ch_pick:{c['id']}", raw=True, color=BLUE)] for c in chans]
    rows.append([btn("✖️ cancel", "ch_cancel", color=RED)])
    await client.send_message(cid, bq(_post_head(ud, None) + "\n" + sc("📣 post to which channel?")), reply_markup=kb(*rows))


async def _ask_text(client, uid: int, cid: int) -> None:
    ud = cmds._ud(uid)
    pf = ud["pf"]
    ud["await"] = "ptext"
    ch = await chstore.get_channel(uid, pf["chat_id"])
    await client.send_message(
        cid,
        bq(_post_head(ud, ch) + "\n\n" +
           sc("✍️ now send the post text.\n"
              "bold, italic, underline, strike, spoiler, code, links, quotes, expandable quotes, any unicode font - "
              "everything you format in telegram stays exactly as you send it.")),
        reply_markup=_cancel_kb([btn("⏭ no text", "ch_skiptext", color=BLUE)]))


async def _ask_buttons(client, uid: int, cid: int) -> None:
    cmds._ud(uid)["await"] = "pbtns"
    example = ("Watch now - https://example.com/anime\n"
               "Join - t.me/yourchannel | Support - t.me/yourgroup")
    await client.send_message(
        cid,
        bq(sc("🔘 now send the inline buttons, one row per line:\n") +
           f"<code>{html.escape(example)}</code>\n" +
           sc("format: text - link   ·   two buttons in one row: separate them with  |\n"
              f"up to {MAX_ROWS} rows, {MAX_PER_ROW} buttons per row.")),
        reply_markup=_cancel_kb([btn("⏭ no buttons", "ch_skipbtn", color=BLUE)]))


async def _show_preview(client, uid: int, cid: int) -> None:
    ud = cmds._ud(uid)
    pf = ud["pf"]
    ud["await"] = None
    for mid in pf.get("msgs", []) + ([pf["ctl"]] if pf.get("ctl") else []):         # drop the old preview
        await cmds._safe_delete(client, cid, mid)
    pf["msgs"], pf["ctl"] = [], None
    try:
        sent = await publish(client, cid, pf["jpg"], pf["text"], pf["ents"], to_markup(pf["rows"]))
    except RPCError as e:
        log.warning("preview failed: %s", e)
        await client.send_message(cid, bq(sc("⚠️ telegram refused that text / buttons: ") + html.escape(str(e)[:150]) + "\n" +
                                          sc("send the text again.")), reply_markup=_cancel_kb())
        ud["await"] = "ptext"
        return
    pf["msgs"] = [m.id for m in sent]
    pf["review"] = True
    ch = await chstore.get_channel(uid, pf["chat_id"])
    split = len(sent) > 1
    ctl = await client.send_message(
        cid,
        bq(sc("👆 this is exactly how the post will look.\n") + sc("send it to ") +
           f"<b>{html.escape((ch or {}).get('title', 'the channel'))}</b>?" +
           (("\n" + sc(f"(text is longer than {CAPTION_MAX} characters, so the photo and the text go as two messages)"))
            if split else "")),
        reply_markup=kb([btn("✅ post to channel", "ch_go", color=GREEN)],
                        [btn("✏️ text", "ch_edtext", color=BLUE), btn("🔘 buttons", "ch_edbtn", color=BLUE)],
                        [btn("✖️ cancel", "ch_cancel", color=RED)]))
    pf["ctl"] = ctl.id


async def _send_to_channel(client, uid: int, cid: int, ctl_msg) -> None:
    ud = cmds._ud(uid)
    pf = ud.get("pf") or {}
    if not pf.get("chat_id"):
        await cmds._edit(ctl_msg, bq(sc("session expired. press 📣 post to channel under a poster again.")))
        return
    if pf.get("sending"):
        return
    pf["sending"] = True
    try:
        await cmds._edit(ctl_msg, bq(sc("🔎 checking my rights…")))
        info, err = await verify(client, uid, pf["chat_id"])         # rights can change after /addchnl
        if err:
            await cmds._edit(ctl_msg, err, _cancel_kb())
            return
        await cmds._edit(ctl_msg, bq(sc("📤 posting…")))
        try:
            sent = await publish(client, pf["chat_id"], pf["jpg"], pf["text"], pf["ents"], to_markup(pf["rows"]))
        except RPCError as e:
            log.warning("post failed: %s", e)
            await cmds._edit(ctl_msg, bq(sc("⚠️ telegram refused the post: ") + html.escape(str(e)[:200])),
                             kb([btn("🔁 try again", "ch_go", color=GREEN), btn("✖️ cancel", "ch_cancel", color=RED)]))
            return
        link = post_link(info["id"], info["username"], sent[-1].id)
        await cmds._edit(ctl_msg, bq(sc("✅ posted to ") + f"<b>{html.escape(info['title'])}</b>"),
                         kb([btn("🔗 open post", url=link, color=BLUE)], [btn("📣 post another", "ch_post", color=GREEN)]))
        ud.pop("pf", None)
        ud["await"] = None
    finally:
        pf["sending"] = False


# ======================================================================
# text typed by the user (only while a flow is waiting for it)
# ======================================================================
async def _handle_add_input(client, message) -> None:
    uid, cid = message.from_user.id, message.chat.id
    fc = getattr(message, "forward_from_chat", None)
    ref = fc.id if fc is not None else parse_ref(message.text or "")
    if ref is None:
        await message.reply_text(bq(sc("😕 i couldn't read that. send the channel @username, its link, or forward a post from it.")),
                                 reply_markup=_cancel_kb())
        return
    await _add_channel(client, uid, cid, ref)


async def on_mode_text(client, message):
    uid, cid = message.from_user.id, message.chat.id
    ud = cmds._ud(uid)
    mode = ud.get("await")

    if mode == "addchnl":
        await _handle_add_input(client, message)

    elif mode == "branding":
        text = chname.clean(message.text)
        if not text:
            await message.reply_text(bq(sc("😕 send some normal letters (emoji can't be drawn on a poster). "
                                           f"up to {chname.LIMIT} characters.")), reply_markup=_cancel_kb())
            return
        await _apply_brand(client, uid, cid, text, extra_delete=[message.id])

    elif mode == "ptext":
        pf = ud.get("pf")
        if not pf:
            ud["await"] = None
            return
        pf["text"] = message.text or ""
        pf["ents"] = list(message.entities) if message.entities else None     # untouched: offsets stay valid
        if pf.get("review"):
            await _show_preview(client, uid, cid)
        else:
            await _ask_buttons(client, uid, cid)

    elif mode == "pbtns":
        pf = ud.get("pf")
        if not pf:
            ud["await"] = None
            return
        rows, errors = parse_buttons(message.text or "")
        if errors or not rows:
            bad = "\n".join("• " + html.escape(e) for e in errors[:5]) or sc("no button found")
            await message.reply_text(
                bq(sc("⚠️ i couldn't use these lines:\n") + bad + "\n\n" + sc("one per line:  text - link   (two in a row: text - link | text - link)")),
                reply_markup=_cancel_kb([btn("⏭ no buttons", "ch_skipbtn", color=BLUE)]))
            return
        pf["rows"] = rows
        await _show_preview(client, uid, cid)


async def on_mode_forward(client, message):
    await _handle_add_input(client, message)


# ======================================================================
# poster branding
# ======================================================================
async def _apply_brand(client, uid: int, cid: int, text: str, extra_delete=()) -> None:
    """save the branding ('' = none), clean the editor up and redraw the poster the user is looking at"""
    ud = cmds._ud(uid)
    await chstore.set_brand(uid, text)
    ud["await"] = None
    for mid in [ud.pop("brmsg", None), *extra_delete]:
        if mid:
            await cmds._safe_delete(client, cid, mid)
    if ud.get("anime") is not None:
        await cmds.generate(client, uid, cid, panel=True)


# ======================================================================
# inline buttons  (callback data "ch_...")
# ======================================================================
async def on_cb(client, cq):
    uid, msg = cq.from_user.id, cq.message
    cid = msg.chat.id
    ud = cmds._ud(uid)
    data = cq.data
    arg = data.split(":", 1)[1] if ":" in data else ""
    cmd = data.split(":", 1)[0]

    if cmd == "ch_cancel":
        await cq.answer()
        was = ud.get("await")
        ud["await"] = None
        pf = ud.pop("pf", None) or {}
        for mid in pf.get("msgs", []):
            await cmds._safe_delete(client, cid, mid)
        if was == "branding":
            await cmds._safe_delete(client, cid, msg.id)
        else:
            await cmds._edit(msg, bq(sc("✖️ cancelled.")))

    elif cmd == "ch_add":
        await cq.answer()
        ud["await"] = "addchnl"
        await client.send_message(cid, ADD_TEXT, reply_markup=_cancel_kb())

    elif cmd == "ch_list":
        await cq.answer()
        await _send_list(client, uid, cid, edit=msg)

    elif cmd == "ch_brand":                                       # ⚙️ options -> 🏷 branding
        await cq.answer()
        ud["await"] = "branding"
        ud["pmsg"] = msg.id                                       # the poster that gets redrawn with the new branding
        cur = await chstore.get_brand(uid)
        chans = (await chstore.channels(uid))[:5]
        rows = [[btn(f"➕ {c['title']}"[:40], f"ch_brpick:{c['id']}", raw=True, color=BLUE)] for c in chans]
        if cur:
            rows.append([btn("🗑 remove branding", "ch_brclr", color=RED)])
        rows.append([btn("✖️ cancel", "ch_cancel", color=RED)])
        m = await client.send_message(
            cid,
            bq(sc("🏷 send your channel branding text.\n"
                  "it is printed on every poster, written in that poster's own style - its font and its colours.\n"
                  f"up to {chname.LIMIT} characters, no emoji.") +
               ("\n\n" + sc("now: ") + f"<b>{html.escape(cur)}</b>" if cur else "") +
               ("\n" + sc("or tap one of your channels:") if chans else "")),
            reply_markup=kb(*rows))
        ud["brmsg"] = m.id

    elif cmd == "ch_brpick":
        c = await chstore.get_channel(uid, int(arg))
        text = chname.clean(c["title"]) if c else ""
        if not text:
            await cq.answer(sc("that name has no letters a poster can show"), show_alert=True)
            return
        await cq.answer(sc("rendering…"))
        await _apply_brand(client, uid, cid, text)

    elif cmd == "ch_brclr":
        await cq.answer(sc("branding removed"))
        await _apply_brand(client, uid, cid, "")

    elif cmd in ("ch_rm", "ch_rmv"):                              # ch_rm: from /mychnls   ch_rmv: from /removechnl
        c = await chstore.get_channel(uid, int(arg))
        if c and await chstore.remove_channel(uid, c["id"]):
            await cq.answer(sc("🗑 removed"))
        else:
            await cq.answer(sc("channel not found"), show_alert=True)
        if cmd == "ch_rmv":
            text, markup = await _remove_view(uid)
            await cmds._edit(msg, text, markup)
        else:
            await _send_list(client, uid, cid, edit=msg)

    # ---- posting
    elif cmd == "ch_post":
        await cq.answer()
        await start_post(client, uid, cid)

    elif cmd == "ch_pick":
        pf = ud.get("pf")
        if not pf:
            await cq.answer(sc("session expired"), show_alert=True)
            return
        await cq.answer()
        pf["chat_id"] = int(arg)
        await cmds._safe_delete(client, cid, msg.id)
        await _ask_text(client, uid, cid)

    elif cmd == "ch_skiptext":
        pf = ud.get("pf")
        if not pf:
            await cq.answer(sc("session expired"), show_alert=True)
            return
        await cq.answer()
        pf["text"], pf["ents"] = "", None
        await cmds._safe_delete(client, cid, msg.id)
        if pf.get("review"):
            await _show_preview(client, uid, cid)
        else:
            await _ask_buttons(client, uid, cid)

    elif cmd == "ch_skipbtn":
        pf = ud.get("pf")
        if not pf:
            await cq.answer(sc("session expired"), show_alert=True)
            return
        await cq.answer()
        pf["rows"] = []
        await cmds._safe_delete(client, cid, msg.id)
        await _show_preview(client, uid, cid)

    elif cmd == "ch_edtext":
        if not ud.get("pf"):
            await cq.answer(sc("session expired"), show_alert=True)
            return
        await cq.answer()
        await _ask_text(client, uid, cid)

    elif cmd == "ch_edbtn":
        if not ud.get("pf"):
            await cq.answer(sc("session expired"), show_alert=True)
            return
        await cq.answer()
        await _ask_buttons(client, uid, cid)

    elif cmd == "ch_go":
        if not ud.get("pf"):
            await cq.answer(sc("session expired"), show_alert=True)
            return
        await cq.answer(sc("posting…"))
        await _send_to_channel(client, uid, cid, msg)

    else:
        await cq.answer()


# ======================================================================
# wiring
# ======================================================================
def _mode_filter(*modes):
    return filters.create(lambda _, __, m: bool(m.from_user) and cmds.STATE[m.from_user.id].get("await") in modes)


def commands() -> list[tuple[str, str]]:
    return [("addchnl", "Add your channel (I must be full admin)"),
            ("removechnl", "Remove a channel"),
            ("mychnls", "Your channels")]


def register(app):
    """call BEFORE cmds.register(): these handlers must see the text first while a flow is waiting for it"""
    app.add_handler(MessageHandler(cmd_addchnl, filters.command("addchnl")))
    app.add_handler(MessageHandler(cmd_removechnl, filters.command("removechnl")))
    app.add_handler(MessageHandler(cmd_mychnls, filters.command("mychnls")))
    app.add_handler(MessageHandler(on_mode_text, filters.private & filters.create(cmds._not_command) & _mode_filter(*MODES)))
    app.add_handler(MessageHandler(on_mode_forward, filters.private & filters.forwarded & ~filters.text & _mode_filter("addchnl")))
    app.add_handler(CallbackQueryHandler(on_cb, filters.regex(r"^ch_")))
