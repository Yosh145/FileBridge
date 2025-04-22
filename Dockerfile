FROM python:3.11-slim

WORKDIR /app
COPY . /app
RUN apt-get update && \
    apt-get install -y libxcb-xinerama0 libxkbcommon-x11-0 && \
    python -m venv .venv && \
    . .venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

ENTRYPOINT ["/app/.venv/bin/python", "src/filebridge.py"]
