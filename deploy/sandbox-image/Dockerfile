FROM python:3.12-slim

# Playwright chromium + deps for Pattern B (sandboxed browser use)
RUN pip install --no-cache-dir playwright==1.49.1 && \
    playwright install --with-deps chromium

# Non-root worker; the control plane starts containers with user=1000:1000,
# read-only root fs, and a tmpfs at /work - this image assumes nothing else.
RUN useradd -m -u 1000 worker && mkdir -p /work && chown worker:worker /work
COPY browser_step.py /opt/browser_step.py
WORKDIR /work
USER worker
CMD ["sleep", "infinity"]
