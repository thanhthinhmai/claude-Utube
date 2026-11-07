# Container for one online job (specs/007 contracts/runner.md). Build from the repo root:
#   docker build -f deploy/job.Dockerfile -t studio-job:latest .
# Runs as user 1000 with a read-only root; only /work (the job folder) and /tmp can be written.
FROM ubuntu:24.04

ARG FFMPEG_URL=https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/playwright STUDIO_HOME_DIR=/studio

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git xz-utils python3 python3-venv python3-pip nodejs npm \
      fonts-dejavu fonts-noto-core fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# ffmpeg 7, static build
RUN curl -fsSL "$FFMPEG_URL" -o /tmp/ffmpeg.tar.xz \
    && tar -xJf /tmp/ffmpeg.tar.xz -C /tmp \
    && cp /tmp/ffmpeg-*-static/ffmpeg /tmp/ffmpeg-*-static/ffprobe /usr/local/bin/ \
    && rm -rf /tmp/ffmpeg*

# The studio: code, instructions and skills (read-only at run time)
WORKDIR /studio
COPY bin/ bin/
COPY tools/ tools/
COPY .claude/ .claude/
COPY CLAUDE.md library.lock ./
RUN rm -rf tools/.venv lib && find tools -name __pycache__ -prune -exec rm -rf {} +

# The style library, pinned by library.lock, and its packages; the studio's own venv
RUN sh bin/studio setup || true \
    && test -f lib/lemo-opuscar/AGENTS.md \
    && sh bin/studio deps voice music \
    && sh bin/studio deps learn --extra \
    && sh bin/studio deps online \
    && tools/.venv/bin/python -m pip install --quiet claude-agent-sdk

# Chromium for the library's renderer (Playwright)
RUN cd lib/lemo-opuscar && (test -f package.json && npm ci --omit=dev || true) \
    && npx --yes playwright@1.48.2 install --with-deps chromium \
    && chmod -R a+rX /opt/playwright /studio

RUN useradd --uid 1000 --create-home --home-dir /home/job job 2>/dev/null || usermod -l job -d /home/job ubuntu
USER 1000
WORKDIR /work
ENTRYPOINT ["/studio/tools/.venv/bin/python", "/studio/tools/runner/agent.py"]
