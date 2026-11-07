# One image for the web app, the API proxy and the worker (specs/007 tasks T044); compose picks the command.
#   docker build -f deploy/web.Dockerfile -t studio-web:latest .
# The heavy tools (Chromium, voice, film libraries) live in studio-job:*, not here.
FROM python:3.12-slim

ARG FFMPEG_URL=https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
ARG DOCKER_CLI=https://download.docker.com/linux/static/stable/x86_64/docker-27.3.1.tgz
ENV LANG=C.UTF-8 PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl git xz-utils sqlite3 \
    && rm -rf /var/lib/apt/lists/*
# ffprobe (uploads are checked with it) and the Docker command line (the worker talks to the socket filter)
RUN curl -fsSL "$FFMPEG_URL" -o /tmp/ff.tar.xz && tar -xJf /tmp/ff.tar.xz -C /tmp \
    && cp /tmp/ffmpeg-*-static/ffprobe /tmp/ffmpeg-*-static/ffmpeg /usr/local/bin/ && rm -rf /tmp/ff* \
    && curl -fsSL "$DOCKER_CLI" | tar -xz -C /tmp && cp /tmp/docker/docker /usr/local/bin/ && rm -rf /tmp/docker

WORKDIR /studio
COPY bin/ bin/
COPY library.lock ./
COPY tools/requirements-*.txt tools/
RUN (sh bin/studio setup || true) && test -f lib/lemo-opuscar/AGENTS.md && sh bin/studio deps online
# the code last, so a code change does not reinstall the packages
COPY tools/ /tmp/tools/
RUN cp -a /tmp/tools/. tools/ && rm -rf /tmp/tools && find tools -path tools/.venv -prune -o -name __pycache__ -prune -exec rm -rf {} + \
    && chmod -R a+rX /studio
COPY CLAUDE.md ./
COPY deploy/terms.md deploy/terms.md

RUN useradd --uid 1000 --create-home studio
USER 1000
ENV STUDIO_MODE=online STUDIO_DATA=/data
EXPOSE 8787
CMD ["/studio/tools/.venv/bin/python", "-m", "uvicorn", "studio.server:app", "--app-dir", "/studio/tools/studio", \
     "--host", "0.0.0.0", "--port", "8787", "--proxy-headers", "--forwarded-allow-ips", "*"]
