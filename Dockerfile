FROM python:3.12-slim
WORKDIR /code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Railway provides PORT at runtime.  The FastAPI lifespan also starts the bot
# polling task, so the public domain and Telegram bot share one deployment.
CMD ["sh", "-c", "uvicorn app.admin:app --host 0.0.0.0 --port ${PORT:-8000}"]
