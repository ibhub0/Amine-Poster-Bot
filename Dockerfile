FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# DejaVu = last-resort font the templates fall back to
RUN apt-get update \
 && apt-get install -y --no-install-recommends fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# pre-download Poppins / Lora / Anton / Noto Sans JP ... (retried at start-up if the build has no internet)
RUN python -c "import dataset; print('missing fonts:', dataset.ensure_fonts())"

RUN useradd -m bot && chown -R bot:bot /app
USER bot

CMD ["python", "main.py"]
