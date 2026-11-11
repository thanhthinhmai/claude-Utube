# The license server of the desktop app (specs/017). Build from the repo root:
#   docker build -f deploy/license/license.Dockerfile -t claude-utube-license .
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 LICENSE_DATA=/data
COPY tools/license/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY tools/license/ /app/
RUN useradd --uid 1000 --create-home license && mkdir -p /data && chown 1000:1000 /data
USER 1000
WORKDIR /app
EXPOSE 8899
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8899/health', timeout=4)"
CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "8899"]
