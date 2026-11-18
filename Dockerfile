FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data

WORKDIR /srv
# Time zone data, so TZ in .env is honoured (daily run at the right local hour)
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY .streamlit ./.streamlit

# Run as an ordinary user, not root
RUN useradd --uid 1000 --create-home sophos && mkdir -p /data && chown sophos:sophos /data
USER sophos

EXPOSE 8501
CMD ["streamlit", "run", "app/dashboard.py"]
