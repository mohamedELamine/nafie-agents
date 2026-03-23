FROM python:3.12-slim

WORKDIR /app

RUN groupadd -r agent && useradd -r -g agent agent

COPY pyproject.toml .
RUN pip install --no-cache-dir -e . --break-system-packages 2>/dev/null || pip install --no-cache-dir -e .

COPY . .
RUN chown -R agent:agent /app
USER agent

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
