from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile

import config

log = logging.getLogger("chstore")

_users: dict[int, dict] = {}                 # cache (the json backend keeps everything here)
_lock = asyncio.Lock()
_coll = None                                 # mongo collection
_ready = False


def _blank() -> dict:
    return {"channels": [], "brand": ""}


async def _init() -> None:
    global _ready, _coll
    if _ready:
        return
    _ready = True
    if config.MONGO_URI:
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            _coll = AsyncIOMotorClient(config.MONGO_URI)[config.MONGO_DB]["poster_users"]
            log.info("channels are stored in MongoDB (%s)", config.MONGO_DB)
            return
        except Exception as e:
            log.warning("MONGO_URI is set but MongoDB can't be used (%s) -> json file instead", e)
    path = config.DATA_DIR / "users.json"
    try:
        if path.exists():
            _users.update({int(k): v for k, v in json.loads(path.read_text("utf-8")).items()})
    except Exception as e:
        log.warning("could not read %s: %s", path, e)
    log.info("channels are stored in %s", path)


def _write_json() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=config.DATA_DIR, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in _users.items()}, f, ensure_ascii=False)
    os.replace(tmp, config.DATA_DIR / "users.json")


async def _get(uid: int) -> dict:
    await _init()
    if uid not in _users:
        doc = await _coll.find_one({"_id": uid}) if _coll is not None else None
        if doc:
            doc.pop("_id", None)
        _users[uid] = {**_blank(), **(doc or {})}
    return _users[uid]


async def _save(uid: int) -> None:
    async with _lock:
        if _coll is not None:
            await _coll.replace_one({"_id": uid}, {"_id": uid, **_users[uid]}, upsert=True)
        else:
            await asyncio.to_thread(_write_json)


# ---------------------------------------------------------------- reading
async def channels(uid: int) -> list[dict]:
    return list((await _get(uid))["channels"])


async def get_channel(uid: int, chat_id: int) -> dict | None:
    return next((c for c in await channels(uid) if c["id"] == chat_id), None)


async def get_brand(uid: int) -> str:
    return (await _get(uid)).get("brand") or ""


# ---------------------------------------------------------------- writing
async def add_channel(uid: int, ch: dict) -> None:
    d = await _get(uid)
    d["channels"] = [c for c in d["channels"] if c["id"] != ch["id"]]
    d["channels"].append({"id": ch["id"], "title": ch["title"], "username": ch.get("username")})
    await _save(uid)


async def remove_channel(uid: int, chat_id: int) -> bool:
    d = await _get(uid)
    before = len(d["channels"])
    d["channels"] = [c for c in d["channels"] if c["id"] != chat_id]
    if len(d["channels"]) == before:
        return False
    await _save(uid)
    return True


async def set_brand(uid: int, text: str) -> None:
    (await _get(uid))["brand"] = text
    await _save(uid)
