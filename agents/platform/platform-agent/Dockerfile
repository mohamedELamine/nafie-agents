FROM python:3.12-slim

# بيانات وصفية
LABEL maintainer="Nafic Platform Team <hello@nafic.com>"
LABEL description="Platform Agent — وكيل المنصة لمنظومة نافع"

# متغيرات البناء
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# تثبيت التبعيات النظامية اللازمة لـ psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# تثبيت Python dependencies أولاً (layer caching)
COPY pyproject.toml .
RUN pip install --upgrade pip && pip install -e .

# نسخ الكود
COPY . .

# مستخدم غير root للأمان
RUN addgroup --system platform && adduser --system --ingroup platform platform
USER platform

# تشغيل الـ migrations ثم الـ server
EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
