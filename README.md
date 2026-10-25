# 🎬 Anime Poster & Thumbnail Bot

<div align="center">

[![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Telegram](https://img.shields.io/badge/Telegram-Channel-2CA5E0?logo=telegram&logoColor=white)](https://t.me/cantarellabots)
[![Support](https://img.shields.io/badge/Telegram-Support%20Chat-0088cc?logo=telegram&logoColor=white)](https://t.me/CantarellaBotschat)
[![Library](https://img.shields.io/badge/Library-Kurigram%20%2F%20Pyrogram-blue)](https://github.com/Kurigram/Kurigram)
[![Engine](https://img.shields.io/badge/Image%20Engine-Pillow-yellow)](https://python-pillow.org/)

An advanced Telegram bot that transforms anime metadata from **AniList** and **fanart.tv** into **13 high-definition poster and thumbnail styles** with automated typography, character art selection, custom button presets, channel branding, and direct-to-channel broadcast publishing.

---

### 📢 Official Channel & Credits
Maintained and presented by **Cantarella Bots**:
- **Main Channel**: [Cantarella Bots (@cantarellabots)](https://t.me/cantarellabots)
- **Support Group**: [Cantarella Bots Chat (@CantarellaBotschat)](https://t.me/CantarellaBotschat)

---

</div>

## ✨ Key Features

- **13 Professional Poster Styles**:
  - Full HD (1920×1080) and HD (1280×720) layouts designed for anime release channels and indexing hubs.
  - Diverse aesthetics: character PNG hero cards, streaming Netflix-style layouts, neon banners, minimal light cards, and bold typography.
- **Dynamic Art & Character Selection**:
  - Seamlessly cycles through transparent character cutouts from **fanart.tv** (or AniList cutout via `rembg`).
  - Allows browsing and switching alternative official posters and high-resolution landscape banners from AniList.
- **Custom Channel Branding**:
  - Automatically renders your channel title or custom branding onto the poster using native typography, custom color palettes, and balanced two-tone typography.
  - Automatically updates across all templates whenever you add your channel or edit your branding.
- **Direct-to-Channel Publishing (`📣 Post to Channel`)**:
  - Attach rich formatted captions with preserved Telegram entities (bold, italic, spoiler, custom emoji, blockquotes).
  - Add custom inline URL buttons using simple syntax: `Text - https://link`.
  - Preview before posting and broadcast directly to verified channels.
- **Strict Channel Admin Verification**:
  - Validates that the bot possesses requisite channel management rights.
  - Ensures only channel owners and administrators can publish posters to their channels.
- **Interactive UI & Live Previews**:
  - Smooth Telegram menu navigation with styled inline buttons, small-caps styling, and real-time photo swaps.
  - Built-in `/styles` viewer to flip through every style preview with caching.
- **High-Quality Export**:
  - Generates instant JPEG previews for chat interactions.
  - One-click `📁 Full Quality File` button delivers uncompressed PNG files as documents.
- **Multi-Layered Watermark Protection**:
  - Cryptographically sealed branding (AES-256-GCM).
  - Spread-spectrum invisible watermark verification (`watermark.py verify`).
- **Flexible Storage Backends**:
  - Auto-selects MongoDB (`motor`) if `MONGO_URI` is provided, otherwise falls back to local JSON storage (`data/users.json`).
- **Production-Ready**:
  - Built-in lightweight HTTP health-check server (`PORT`) for cloud container platforms (Render, Koyeb, Railway, Heroku).
  - Pre-packaged `Dockerfile` with automatic Google Fonts download (`ensure_fonts`).

---

## 🤖 Bot Commands

| Command | Description |
| :--- | :--- |
| `/start` | Launch the bot, initialize user session, and display the main menu |
| `/help` | View command guide, usage tips, and support links |
| `/poster <anime>` | Instantly search AniList and generate a poster for the specified anime |
| `/styles` | Interactive carousel previewing all 13 styles |
| `/addchnl` | Register a Telegram channel (bot must be administrator) |
| `/mychnls` | List your registered channels with real-time rights validation |
| `/removechnl` | Unlink a registered channel |

> **Tip**: You can also simply send any anime title directly in the private chat, and the bot will launch the search picker automatically!

---

## ⚙️ Configuration & Environment Variables

Create a `.env` file or define these variables in your deployment environment:

### 🔑 Essential Credentials

| Variable | Description | Default | Required |
| :--- | :--- | :--- | :---: |
| `API_ID` | Telegram API ID from [my.telegram.org](https://my.telegram.org) | None | **Yes** |
| `API_HASH` | Telegram API Hash from [my.telegram.org](https://my.telegram.org) | None | **Yes** |
| `BOT_TOKEN` | Telegram Bot Token from [@BotFather](https://t.me/BotFather) | None | **Yes** |
| `WATERMARK_KEY` | Secret master key used for sealing watermarks | None | Optional |

### 🛠 Channels & Database Settings

| Variable | Description | Default |
| :--- | :--- | :--- |
| `MONGO_URI` | MongoDB connection URI (e.g. `mongodb+srv://...`) | *Empty (uses JSON)* |
| `MONGO_DB` | MongoDB database name | `poster_bot` |
| `DATA_DIR` | Local storage folder for `users.json` when MongoDB is not configured | `./data` |
| `MAX_CHANNELS` | Maximum channels a user can register | `5` |
| `ALLOWED_USERS` | Comma-separated user IDs for private bot mode (leave blank for public access) | *Empty (public)* |

### 🎨 Rendering & Art Options

| Variable | Description | Default |
| :--- | :--- | :--- |
| `BRAND_TOP` | Top word for two-tone brand lockups (Styles 8 & 13) | `ANI` |
| `BRAND_BOTTOM` | Bottom word for two-tone brand lockups (Styles 8 & 13) | `CROX` |
| `FANART_API_KEY` | [fanart.tv](https://fanart.tv/) API key for character art | *Pre-configured* |
| `TMDB_API_KEY` | TMDB API key used for fallback title matching | *Pre-configured* |
| `USE_CHARACTER_PNG` | Enable fanart.tv transparent character search (`1` or `0`) | `1` |
| `USE_ANILIST_CUTOUT` | Cut out AniList characters using `rembg` (`1` or `0`) | `0` |
| `FANART_CANDIDATES` | Maximum fanart.tv transparent PNGs to fetch per anime | `15` |
| `POSTER_CHOICES` | Maximum AniList alternative posters to index | `12` |
| `BANNER_CHOICES` | Maximum AniList alternative landscape banners to index | `12` |
| `RENDER_WORKERS` | Number of simultaneous background render workers | `2` |

### 🌐 Links & Hosting

| Variable | Description | Default |
| :--- | :--- | :--- |
| `MAIN_CHANNEL_URL` | Channel link displayed in the help menu | `https://t.me/cantarellabots` |
| `SUPPORT_URL` | Support chat link displayed in the help menu | `https://t.me/CantarellaBotschat` |
| `PORT` | Health-check port (binds `0.0.0.0:PORT` when set > 0) | `0` (disabled) |
| `LOG_LEVEL` | Logging level (`INFO`, `DEBUG`, `WARNING`, `ERROR`) | `INFO` |

---

## 🚀 Installation & Local Setup

### 1. Clone the Repository

```bash
git clone https://github.com/abhinai2244/Anime-Poster-Bot
cd Anime-Poster-Bot
```

### 2. Set Up a Python Virtual Environment

```bash
python -m venv venv

# Windows:
.\venv\Scripts\activate

# Linux / macOS:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create an environment file or set variables directly:

```bash
# Linux/macOS
export API_ID=1234567
export API_HASH="your_api_hash_here"
export BOT_TOKEN="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"

# Windows PowerShell
$env:API_ID="1234567"
$env:API_HASH="your_api_hash_here"
$env:BOT_TOKEN="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
```

### 5. Download Required Fonts

The bot checks and downloads required Google Fonts automatically on first start, but you can trigger it in advance:

```bash
python -c "import dataset; print('Missing fonts:', dataset.ensure_fonts())"
```

### 6. Run the Bot

```bash
python main.py
```

---

## 🐳 Docker Deployment

The project includes an optimized `Dockerfile` based on `python:3.11-slim`:

### Build Docker Image

```bash
docker build -t anime-poster-bot .
```

### Run Container

```bash
docker run -d \
  --name poster-bot \
  --restart unless-stopped \
  -e API_ID="1234567" \
  -e API_HASH="your_api_hash" \
  -e BOT_TOKEN="your_bot_token" \
  -e MONGO_URI="mongodb+srv://..." \
  -e PORT="8080" \
  -p 8080:8080 \
  anime-poster-bot
```

---

## ☁️ Cloud Platform Deployment

### Deploy to Heroku
A `Procfile` is included:
```text
worker: python main.py
```
1. Create a new Heroku app.
2. In **Settings** > **Config Vars**, add `API_ID`, `API_HASH`, `BOT_TOKEN`, and `MONGO_URI`.
3. Connect your Git repository and deploy.
4. Ensure the `worker` dyno is turned ON in the **Resources** tab.

### Deploy to Render / Koyeb / Railway
1. Set the build command: `pip install -r requirements.txt`
2. Set the start command: `python main.py`
3. Set the environment variable `PORT=8080` (or the port required by your host) to activate the internal health-check server.
4. Add your Telegram credentials (`API_ID`, `API_HASH`, `BOT_TOKEN`).

---

## 🛡️ Watermark & Security Tools

The `watermark.py` utility allows inspecting, creating keys, and verifying posters:

```bash
# Generate a fresh random WATERMARK_KEY
python watermark.py newkey

# Seal custom text using WATERMARK_KEY
python watermark.py seal "Cantarella Bots"

# Verify if an image contains your invisible spread-spectrum signature
python watermark.py verify poster.png
```

---

## 👥 Credits & Channel Links

- **Main Channel**: [Cantarella Bots (@cantarellabots)](https://t.me/cantarellabots)
- **Community Chat**: [Cantarella Bots Chat (@CantarellaBotschat)](https://t.me/CantarellaBotschat)
- **Data Providers**:
  - [AniList GraphQL API](https://anilist.gitbook.io/anilist-apiv2-docs/) for media metadata and covers.
  - [fanart.tv](https://fanart.tv/) for transparent anime character PNGs.
- **Telegram Framework**: Built with [Kurigram / Pyrogram](https://github.com/Kurigram/Kurigram).

---

<div align="center">
Made with ❤️ by <a href="https://t.me/cantarellabots"><b>Cantarella Bots</b></a>
</div>
