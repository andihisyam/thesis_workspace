FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /opt/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    biber \
    texlive-xetex \
    texlive-lang-other \
    texlive-latex-extra \
    texlive-fonts-recommended \
    fonts-lmodern \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements.txt
COPY requirements-v2.txt requirements-v2.txt
RUN pip install --no-cache-dir -r backend/requirements.txt -r requirements-v2.txt

COPY . .

ENV PORT=8001
EXPOSE 8001

CMD ["sh", "-c", "uvicorn backend_v2.main:app --host 0.0.0.0 --port ${PORT}"]
