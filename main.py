import asyncio
import logging
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from pyrogram import Client, enums, idle

import config   # first: it prepares the environment the templates read
import chnl
import cmds
import dataset

logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                    level=config.LOG_LEVEL)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
log = logging.getLogger("main")


class _Health(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


def _start_health_server(port: int):
    srv = HTTPServer(("0.0.0.0", port), _Health)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    log.info("health server on :%s", port)


async def amain():
    if not (config.BOT_TOKEN and config.API_ID and config.API_HASH):
        sys.exit("BOT_TOKEN, API_ID and API_HASH must be set.")

    missing = await asyncio.to_thread(dataset.ensure_fonts)      # no-op when the fonts are already there
    if missing:
        log.warning("fonts missing (posters fall back to DejaVu): %s", ", ".join(missing))

    if config.PORT:
        _start_health_server(config.PORT)

    app = Client("poster-bot", api_id=config.API_ID, api_hash=config.API_HASH, bot_token=config.BOT_TOKEN,
                 in_memory=True, parse_mode=enums.ParseMode.HTML, workers=16)
    chnl.register(app)       # before cmds: while a flow waits for text, these handlers must see it first
    cmds.register(app)
    await app.start()
    await cmds.post_start(app)
    log.info("bot started - %d poster styles", len(dataset.POSTERS))
    await idle()
    await app.stop()


if __name__ == "__main__":
    asyncio.run(amain())
