# Code Review Bot

[![CI/CD](https://github.com/bsekinaev/code-review-bot/actions/workflows/deploy.yml/badge.svg)](https://github.com/bsekinaev/code-review-bot/actions)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-37814A?logo=celery&logoColor=white)

GitHub App для автоматизированного анализа Python Pull Request. Сервис объединяет Ruff и GigaChat, анализирует только изменённые строки и публикует результат проверки в Pull Request.

> **Статус:** portfolio project / MVP. Для полноценного запуска требуются GitHub App, PostgreSQL, Redis и учётные данные GigaChat.

## Возможности

- приём GitHub webhook-событий через FastAPI;
- HMAC-проверка подписи webhook'а;
- GitHub App JWT и installation access token;
- парсинг unified diff;
- фильтрация предупреждений Ruff по изменённым строкам;
- AI-анализ изменений через GigaChat;
- публикация результатов в Pull Request;
- Telegram-уведомления;
- сохранение истории проверок в PostgreSQL;
- конфигурация правил через `.codereview.yml`;
- fallback на Ruff при недоступности AI;
- Docker Compose, Alembic, pytest и GitHub Actions.

## Архитектура

```mermaid
flowchart LR
    GH[GitHub Pull Request] -->|Webhook| API[FastAPI]
    API --> SIGN[HMAC verification]
    SIGN --> Q[Redis / Celery]
    Q --> WORKER[Review worker]
    WORKER --> DIFF[Unified diff parser]
    DIFF --> RUFF[Ruff]
    DIFF --> AI[GigaChat]
    WORKER --> DB[(PostgreSQL)]
    WORKER --> COMMENT[GitHub PR comment]
    WORKER --> TG[Telegram notification]
```

FastAPI отвечает за проверку входящего webhook'а и постановку задачи в очередь. Анализ выполняется в Celery-воркере, поэтому HTTP endpoint не блокируется на вызовах GitHub и GigaChat API.

## Ключевые решения

### Diff-aware анализ

Ruff может вернуть предупреждения по всему файлу. Парсер unified diff определяет изменённые строки, после чего замечания фильтруются и относятся только к текущему Pull Request.

### Безопасность webhook'ов

Подпись GitHub проверяется через HMAC до постановки задачи в очередь. Для обращения к GitHub API используется GitHub App JWT и installation token.

### Graceful fallback

Если GigaChat недоступен, статический анализ Ruff продолжает работать. Ошибка AI-интеграции не должна полностью блокировать проверку Pull Request.

### Изоляция данных

Результаты проверок и конфигурация репозитория хранятся в PostgreSQL. Работа с базой выполняется через SQLAlchemy и миграции Alembic.

## Стек

| Область | Технологии |
|---|---|
| Backend | Python 3.12, FastAPI, Uvicorn |
| Queue | Celery, Redis |
| Database | PostgreSQL 16, SQLAlchemy 2.0 async, Alembic |
| Static analysis | Ruff |
| AI | GigaChat API, OAuth2 |
| Integrations | GitHub App, GitHub API, Telegram Bot API |
| HTTP | httpx |
| Tests | pytest, pytest-asyncio, unittest.mock |
| Infrastructure | Docker, Docker Compose, GitHub Actions |

## Быстрый старт

### 1. Клонирование

```bash
git clone https://github.com/bsekinaev/code-review-bot.git
cd code-review-bot
```

### 2. Конфигурация

```bash
cp .env.example .env
```

Заполните параметры GitHub App, PostgreSQL, Redis и GigaChat. Не коммитьте `.env` и приватный ключ GitHub App.

Пример основных переменных:

```env
GITHUB_APP_ID=your_app_id
GITHUB_PRIVATE_KEY_PATH=./private-key.pem
WEBHOOK_SECRET=your_webhook_secret

REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/code_review_bot

AI_ENABLED=true
GIGACHAT_CLIENT_ID=your_client_id
GIGACHAT_CLIENT_SECRET=your_client_secret
GIGACHAT_VERIFY_SSL=true
```

TLS-проверку нельзя отключать в публичном или production-like окружении. При необходимости добавьте доверенный CA bundle.

### 3. Инфраструктура

```bash
docker compose -f docker-compose.dev.yml up -d
```

### 4. Зависимости и миграции

```bash
pip install -r requirements.txt
alembic upgrade head
```

### 5. Запуск

```bash
uvicorn app.main:app --reload --port 8000
```

```bash
celery -A app.core.celery_app worker --loglevel=info --pool=solo
```

Для Linux вместо `--pool=solo` можно использовать стандартный prefork pool.

## Конфигурация репозитория

Правила анализа можно хранить в `.codereview.yml` подключаемого проекта.

```yaml
ruff:
  enabled: true
  select:
    - E
    - F
    - B

ai:
  enabled: true
```

Поддерживаемые поля зависят от текущей схемы конфигурации проекта.

## Тестирование

```bash
pytest -v
```

Тесты покрывают парсинг diff, фильтрацию Ruff, загрузку конфигурации и отдельные интеграционные компоненты.

## CI/CD

GitHub Actions выполняет автоматические проверки проекта и сборку Docker-образа. Конфигурация деплоя требует отдельных repository secrets и целевого окружения.

## Ограничения и roadmap

- [x] HMAC webhook verification
- [x] GitHub App authentication
- [x] diff-aware Ruff analysis
- [x] GigaChat integration and fallback
- [x] PostgreSQL history
- [ ] расширить интеграционные тесты GitHub API
- [ ] добавить идемпотентность повторных delivery webhook'ов
- [ ] добавить наблюдаемость очереди и внешних интеграций
- [ ] подготовить демонстрационный репозиторий с примером Pull Request

## Автор

**Батраз Секинаев** — Python Backend Developer

[GitHub](https://github.com/bsekinaev) · [Telegram](https://t.me/bsekinaev)
