# Container for one online job (specs/007 contracts/runner.md). Build from the repo root:
#   docker build -f deploy/job.Dockerfile -t studio-job:latest .
# Runs as user 1000 with a read-only root; only /work (the job folder) and /tmp can be written.
FROM ubuntu:24.04

ARG FFMPEG_URL=https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
ARG NODE_VERSION=22.12.0
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/playwright STUDIO_HOME_DIR=/studio

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git xz-utils python3 python3-venv python3-pip \
      fonts-dejavu fonts-noto-core fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# Node 20+ (the library's renderer); Ubuntu's own nodejs is 18
RUN curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" -o /tmp/node.tar.xz \
    && tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 && rm /tmp/node.tar.xz && node --version

# ffmpeg 7, static build
RUN curl -fsSL "$FFMPEG_URL" -o /tmp/ffmpeg.tar.xz \
    && tar -xJf /tmp/ffmpeg.tar.xz -C /tmp \
    && cp /tmp/ffmpeg-*-static/ffmpeg /tmp/ffmpeg-*-static/ffprobe /usr/local/bin/ \
    && rm -rf /tmp/ffmpeg*

# The style library, pinned by library.lock, and every package. Only what the install reads is copied
# first, so changing the studio's code later does not reinstall all of this.
WORKDIR /studio
COPY bin/ bin/
COPY library.lock ./
COPY tools/requirements-*.txt tools/
RUN sh bin/studio setup || true \
    && test -f lib/lemo-opuscar/AGENTS.md \
    && sh bin/studio deps voice music \
    && sh bin/studio deps learn --extra \
    && sh bin/studio deps online \
    && tools/.venv/bin/python -m pip install --quiet claude-agent-sdk

# System libraries Chromium needs; everything readable by the job user
RUN cd lib/lemo-opuscar && node node_modules/playwright-core/cli.js install-deps chromium-headless-shell \
    && rm -rf /var/lib/apt/lists/* && chmod -R a+rX /opt/playwright /studio

# The studio: code, instructions and skills (read-only at run time)
COPY tools/ /tmp/tools/
RUN cp -a /tmp/tools/. tools/ && rm -rf /tmp/tools && find tools -path tools/.venv -prune -o -name __pycache__ -prune -exec rm -rf {} + \
    && chmod -R a+rX tools
COPY CLAUDE.md ./
COPY .claude/skills/style-learn/ .claude/skills/style-learn/

RUN useradd --uid 1000 --create-home --home-dir /home/job job 2>/dev/null || usermod -l job -d /home/job ubuntu
USER 1000
WORKDIR /work
ENTRYPOINT ["/studio/tools/.venv/bin/python", "/studio/tools/runner/agent.py"]
