# The studio's own Linux for the Windows desktop app (specs/016 research R1). Build with
# desktop/core-build/build-linux.sh, which sends `git archive` of the repo as the build context.
# The result is exported (docker export) and imported by the app with `wsl --import ClaudeUtube`.
# No models inside: the app downloads them at setup (R3).
FROM ubuntu:24.04

ARG FFMPEG_URL=https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
ARG NODE_VERSION=22.12.0
ARG CORE_VERSION=0.0.0-dev
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git xz-utils python3 python3-venv python3-pip \
      bubblewrap socat fontconfig fonts-dejavu fonts-noto-core fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# Node 20+ (the library's renderer); Ubuntu's own nodejs is 18
RUN curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" -o /tmp/node.tar.xz \
    && tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 && rm /tmp/node.tar.xz && node --version

# ffmpeg 7, static build (GPL-3.0; the source link is in CREDITS)
RUN curl -fsSL "$FFMPEG_URL" -o /tmp/ffmpeg.tar.xz \
    && tar -xJf /tmp/ffmpeg.tar.xz -C /tmp \
    && mkdir -p /usr/local/share/doc/ffmpeg \
    && cp /tmp/ffmpeg-*-static/ffmpeg /tmp/ffmpeg-*-static/ffprobe /usr/local/bin/ \
    && cp /tmp/ffmpeg-*-static/GPLv3.txt /tmp/ffmpeg-*-static/readme.txt /usr/local/share/doc/ffmpeg/ \
    && rm -rf /tmp/ffmpeg*

# The default user of the Linux is "studio" (uid 1000), as WSL expects
RUN usermod -l studio -d /home/studio -m ubuntu && groupmod -n studio ubuntu \
    && printf '[user]\ndefault=studio\n[boot]\nsystemd=false\n[interop]\nappendWindowsPath=false\n' > /etc/wsl.conf

USER studio
WORKDIR /home/studio/claude-Utube
# Only what the install reads first, so a code change does not reinstall every package
COPY --chown=studio:studio bin/ bin/
COPY --chown=studio:studio library.lock ./
COPY --chown=studio:studio tools/requirements-*.txt tools/
RUN sh bin/studio setup || true \
    && test -f lib/lemo-opuscar/AGENTS.md \
    && sh bin/studio deps voice music \
    && sh bin/studio deps learn --extra \
    && sh bin/studio deps online \
    && rm -f lib/lemo-opuscar/core/tts/*.onnx lib/lemo-opuscar/core/tts/*.bin \
    && rm -rf /home/studio/.cache/huggingface /home/studio/.cache/pip /home/studio/.cache/uv /home/studio/.npm

# The full Chromium too: on WSL2 the GPU is reachable only from a headful browser on the WSLg display (specs/019 R1, R9)
RUN cd lib/lemo-opuscar && node node_modules/playwright-core/cli.js install chromium

# System libraries Chromium needs (both builds), and Mesa's d3d12 driver for WSLg (installed at build time only)
USER root
RUN cd lib/lemo-opuscar && node node_modules/playwright-core/cli.js install-deps chromium-headless-shell chromium \
    && apt-get update && apt-get install -y --no-install-recommends libgl1-mesa-dri libegl-mesa0 \
    && rm -rf /var/lib/apt/lists/*

USER studio
COPY --chown=studio:studio . /tmp/src/
RUN cp -a /tmp/src/. . && rm -rf /tmp/src \
    && echo "$CORE_VERSION" > .core-version
