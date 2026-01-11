FROM mcr.microsoft.com/playwright/python:v1.57.0-jammy

# Définir le fuseau horaire en mode non-interactif
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Installer wkhtmltopdf et ses dépendances
RUN apt-get update && apt-get install -y \
    wkhtmltopdf \
    xfonts-75dpi \
    xfonts-base \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=10000

CMD gunicorn main:app --bind 0.0.0.0:$PORT --timeout 120
