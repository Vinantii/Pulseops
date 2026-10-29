FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 \
       --shell /usr/sbin/nologin pulseops \
    && mkdir -p /data \
    && chown -R pulseops:pulseops /app /data

COPY --chown=pulseops:pulseops app.py monitor.py recovery.py incident_store.py ./
COPY --chown=pulseops:pulseops templates ./templates
COPY --chown=pulseops:pulseops static ./static

USER pulseops

EXPOSE 5000

CMD ["gunicorn", "--workers", "1", "--threads", "4", "--bind", "0.0.0.0:5000", "app:app"]
