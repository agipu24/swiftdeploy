FROM python:3.11-slim
WORKDIR /app
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ .
RUN chown -R appuser /app
USER appuser
EXPOSE 3000
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:3000/healthz')" || exit 1
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:3000", "--workers", "2"]
