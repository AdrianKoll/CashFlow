# syntax=docker/dockerfile:1
FROM python:3.12-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# postgresql-client fornece o pg_dump usado nas cópias de segurança.
# A versão do cliente precisa ser igual ou mais nova que a do servidor.
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependências primeiro: a camada fica em cache enquanto elas não mudarem.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY run.py .
COPY app ./app
COPY templates ./templates
COPY static ./static

# Usuário sem privilégios; /app/instance guarda as cópias de segurança.
RUN useradd --system --create-home --uid 10001 cashflow \
    && mkdir -p /app/instance \
    && chown -R cashflow:cashflow /app/instance
USER cashflow

ENV CASHFLOW_ENV=production \
    CASHFLOW_SESSION_COOKIE_SECURE=false

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"

# Um worker com várias threads: o limitador de tentativas de login fica em
# memória (um contador por processo) e, com mais workers, cada um teria o seu.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", \
     "--access-logfile", "-", "run:app"]
