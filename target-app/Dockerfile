FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEMOAPP_HOST=0.0.0.0

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10002 \
       --shell /usr/sbin/nologin demoapp

COPY --chown=demoapp:demoapp app.py ./app.py

USER demoapp

EXPOSE 5001

CMD ["python", "app.py"]
