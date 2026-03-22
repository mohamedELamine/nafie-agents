FROM python:3.11-slim

WORKDIR /app

# تثبيت التبعيات النظامية
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libmagic1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# تثبيت متطلبات Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ الكود
COPY . .

# مستخدم غير root للأمان
RUN useradd -m -u 1000 agent && chown -R agent:agent /app
USER agent

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
