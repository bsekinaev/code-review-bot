# 🤖 Code Review Bot

Автоматический ревьюер Python-кода в Pull Request.
Основан на FastAPI и Ruff.

## Как запустить
1. pip install -r requirements.txt
2. Создать .env с WEBHOOK_SECRET, GITHUB_APP_ID, GITHUB_PRIVATE_KEY_PATH
3. uvicorn app.main:app --reload
4. Для вебхуков использовать smee.io

### Docker
docker-compose up --build

## Тесты
pytest tests/