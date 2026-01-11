FROM mcr.microsoft.com/playwright/python:v1.57.0-jammy

# Installer wkhtmltopdf et ses dépendances
RUN apt-get update && apt-get install -y \
    wkhtmltopdf \
    xfonts-75dpi \
    xfonts-base \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=10000

CMD gunicorn main:app --bind 0.0.0.0:$PORT --timeout 120
