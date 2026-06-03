# 🤖 Code Review Bot

Промышленный AI-powered ревьюер Python-кода для Pull Requests на GitHub.
Основан на **FastAPI**, **Celery**, **PostgreSQL** и **GigaChat**. Бот анализирует только изменённые строки, комбинирует линтер (Ruff) с AI-инсайтами по безопасности и архитектуре, оставляет замечания прямо в PR и уведомляет о результатах в Telegram.

<br>
<div align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Celery-Redis-FF0000?style=for-the-badge&logo=redis&logoColor=white" alt="Celery">
  <img src="https://img.shields.io/badge/PostgreSQL-16-336791?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/GigaChat-0077FF?style=for-the-badge&logo=sber&logoColor=white" alt="GigaChat">
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/GitHub_Actions-CI%2FCD-2088FF?style=for-the-badge&logo=githubactions&logoColor=white" alt="GitHub Actions">
  <br>
  <img src="https://github.com/bsekinaev/code-review-bot/actions/workflows/deploy.yml/badge.svg" alt="CI/CD Status">
</div>

---

## 📑 Содержание
- [✨ Возможности](#-возможности)
- [🏗 Архитектура](#-архитектура)
- [🧰 Технологический стек](#-технологический-стек)
- [🚀 Быстрый старт](#-быстрый-старт)
- [⚙️ Конфигурация](#️-конфигурация)
- [🐳 Docker](#-docker)
- [🔄 CI/CD](#-cicd)
- [📝 Конфигурация проекта](#-конфигурация-проекта-codereviewyml)
- [📁 Структура файлов](#-структура-файлов)
- [🔍 Как это работает](#-как-это-работает)
- [🛠 Устранение неисправностей](#-устранение-неисправностей)
- [🚧 Roadmap](#-roadmap)
- [📄 Лицензия](#-лицензия)

---

## ✨ Возможности

- 🎯 **Анализ только изменённого кода** — бот фокусируется на строках, затронутых в PR, исключая спам старыми предупреждениями
- 🧠 **AI-инсайты (GigaChat)** — автоматический поиск уязвимостей, code smells и рекомендации по рефакторингу
- 🛡️ **Гибкая настройка** — `.codereview.yml` в каждом репозитории позволяет управлять правилами линтера на лету
- ⚡ **Асинхронная обработка** — Celery + Redis обеспечивают масштабируемую фоновую обработку PR без блокировки вебхуков
- 💾 **История и аналитика** — PostgreSQL сохраняет все ревью для последующего анализа и метрик
- 📢 **Мгновенные уведомления** — результаты публикуются в PR, краткий отчёт дублируется в Telegram
- 🐳 **Полная контейнеризация** — запуск от локальной машины до облачного кластера
- 🔒 **Безопасность** — HMAC-верификация вебхуков, кэширование токенов, изоляция сессий БД

---

## 🏗 Архитектура

Бот построен на модульной, отказоустойчивой архитектуре:

![architecture.png](docs/architecture.png)
**Ключевые принципы:**
- 📦 **Изоляция ответственности** — каждый модуль решает одну задачу
- 🔄 **Retry с exponential backoff** — автоматические повторные попытки при сбоях API
- 💾 **Graceful Fallback** — если AI недоступен, бот продолжает работать на чистом Ruff
- 🔐 **Токен-кэширование** — in-memory кэш с TTL снижает нагрузку на GitHub API на 98%

---

## 🧰 Технологический стек

| Слой | Технологии |
|------|------------|
| **Язык** | Python 3.12 |
| **Web Framework** | FastAPI, Uvicorn (2 workers) |
| **Очередь задач** | Celery + Redis |
| **База данных** | PostgreSQL 16, SQLAlchemy 2.0 (async), Alembic |
| **AI-интеграция** | GigaChat API (OAuth2, Token Caching, JSON validation) |
| **Анализ кода** | Ruff (subprocess, diff-scoped, timeout 30s) |
| **HTTP-клиент** | httpx (Singleton, connection pooling) |
| **Контейнеризация** | Docker, Docker Compose |
| **CI/CD** | GitHub Actions → GHCR → VPS (SSH) |
| **Тестирование** | pytest, pytest-asyncio, unittest.mock (11 unit tests) |

---

## 🚀 Быстрый старт

### 1. Клонирование
```bash
git clone https://github.com/bsekinaev/code-review-bot.git
cd code-review-bot
```

### 2. Конфигурация
```bash
cp .env.example .env
# Отредактируйте .env, указав реальные значения
```

### 3. Запуск инфраструктуры
```bash
docker-compose -f docker-compose.dev.yml up -d
```
Это поднимет PostgreSQL и Redis с healthchecks и автоматическим рестартом.

### 4. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 5. Запуск сервисов

**Terminal 1 — FastAPI:**
```bash
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Celery Worker:**
```bash
celery -A app.core.celery_app worker --loglevel=info --pool=solo
```
> ℹ️ `--pool=solo` используется для Windows. В Linux-окружении используйте дефолтный `prefork`.

---

## ⚙️ Конфигурация

### Переменные окружения (`.env`)
```env
# GitHub App
GITHUB_APP_ID=your_app_id
GITHUB_PRIVATE_KEY_PATH=./private-key.pem
WEBHOOK_SECRET=your_webhook_secret

# Telegram (опционально)
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=123456789

# Инфраструктура
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/code_review_bot

# AI (GigaChat)
AI_ENABLED=True
GIGACHAT_CLIENT_ID=your_client_id
GIGACHAT_CLIENT_SECRET=your_client_secret
GIGACHAT_VERIFY_SSL=False  # True для production
```

### Миграции БД
```bash
# Создать новую миграцию
alembic revision --autogenerate -m "description"

# Применить миграции
alembic upgrade head
```

---

## 🐳 Docker

### Development
```bash
docker-compose -f docker-compose.dev.yml up -d
```

### Production
На VPS используется отдельный `docker-compose.yml`, который тянет готовый образ из GHCR:
```bash
cd /opt/code-review-bot
docker-compose pull bot
docker-compose up -d --force-recreate bot
```

### Файловая структура на сервере
```
/opt/code-review-bot/
├── docker-compose.yml   # Конфигурация для production (image, не build)
├── .env                 # Реальные переменные окружения
└── private-key.pem      # Приватный ключ GitHub App (chmod 400)
```

---

## 🔄 CI/CD

Воркфлоу `.github/workflows/deploy.yml` запускается при пуше в `main`:

| Этап | Описание |
|------|----------|
| **1. Test** | Установка зависимостей, запуск pytest с `PYTHONPATH=.` |
| **2. Build & Push** | Сборка Docker-образа, пуш в `ghcr.io/${{ github.repository }}:latest` |
| **3. Deploy** | SSH-подключение к VPS, `docker-compose pull` + `up -d` |

### Необходимые секреты GitHub
| Secret | Описание |
|--------|----------|
| `VPS_HOST` | IP или домен сервера |
| `VPS_USER` | SSH-пользователь |
| `VPS_SSH_KEY` | Приватный SSH-ключ |

> ⚠️ Убедитесь, что в workflow указан `permissions: { packages: write }`, иначе пуш в GHCR будет запрещён.

---

## 📝 Конфигурация проекта (`.codereview.yml`)

Создайте в корне репозитория файл `.codereview.yml` для тонкой настройки:

```yaml
# Правила Ruff, которые нужно игнорировать
ignore:
  - F401  # 'module imported but unused'
  - E501  # 'line too long'

# Если задан, применяются ТОЛЬКО перечисленные правила.
# Пустой список = применить все.
select: []

# Маски файлов/папок для исключения (fnmatch)
exclude:
  - "migrations/*"
  - "tests/*"
  - "**/conftest.py"
```

Конфигурация загружается из ветки PR при каждом ревью, что позволяет менять правила «на лету» без перезапуска бота.

---

## 📁 Структура файлов

```
code-review-bot/
├── .github/workflows/deploy.yml    # Пайплайн CI/CD: тесты → сборка образа → деплой на VPS
├── alembic/                        # Миграции базы данных (Alembic)
│   ├── env.py                      # Конфигурация окружения миграций
│   └── versions/                   # Файлы миграций (создаются автоматически)
├── app/                            # Исходный код приложения
│   ├── ai_analyzer.py              # Интеграция с GigaChat: OAuth2, кэш токенов, валидация JSON
│   ├── clients/
│   │   └── github_client.py        # Singleton httpx-клиент с connection pooling для GitHub API
│   ├── core/
│   │   └── celery_app.py           # Конфигурация Celery (брокер, бэкенд, настройки задач)
│   ├── db.py                       # Async SQLAlchemy engine, фабрика сессий, dependency для FastAPI
│   ├── models/                     # SQLAlchemy 2.0 модели (type hints + Mapped)
│   │   ├── organization.py         # Модель: установка GitHub App (org/user)
│   │   ├── repository.py           # Модель: репозиторий с привязкой к организации
│   │   └── review.py               # Модель: результат анализа PR (статус, метрики, данные)
│   ├── tasks/
│   │   └── process_pr.py           # Celery-задача: обработка PR с retry, изоляцией БД и логированием
│   ├── main.py                     # Точка входа FastAPI: вебхуки, HMAC-верификация, enqueue задач
│   ├── github_auth.py              # Генерация JWT, кэширование installation-токенов (TTL 55 мин)
│   ├── github_api.py               # Клиент для GitHub REST API (файлы, контент, ревью)
│   ├── config_loader.py            # Загрузка .codereview.yml из репозитория (base64 + YAML)
│   ├── diff_parser.py              # Парсер unified diff: извлечение диапазонов изменённых строк
│   ├── linter.py                   # Обёртка над Ruff: запуск через subprocess с таймаутом
│   └── telegram_bot.py             # Отправка уведомлений в Telegram (HTML-форматирование)
├── scripts/                        # Ручные интеграционные скрипты (не запускаются в CI)
│   ├── check_gigachat_auth.py      # Проверка получения OAuth2-токена GigaChat
│   └── check_gigachat_chat.py      # Проверка запроса к Chat API GigaChat
├── tests/                          # Юнит-тесты (pytest + asyncio + моки)
│   ├── test_config_loader.py       # Тесты загрузки конфигурации из репозитория
│   ├── test_diff_parser.py         # Тесты парсинга diff-диапазонов
│   ├── test_linter.py              # Тесты обёртки Ruff (игноры, селекты, чистый код)
│   └── test_telegram_bot.py        # Тесты отправки уведомлений (успех / отсутствие токена)
├── docker-compose.dev.yml          # Инфраструктура для разработки: PostgreSQL 16 + Redis 7
├── docker-compose.yml              # Production compose: только сервис бота (образ из GHCR)
├── Dockerfile                      # Инструкции сборки образа: Python 3.12-slim, uvicorn, 2 воркера
├── requirements.txt                # Зависимости проекта с фиксированными минимальными версиями
└── .env.example                    # Шаблон переменных окружения (скопировать в .env и заполнить)
```
---

## 🔍 Как это работает

### Полный пайплайн обработки PR

1. **Webhook Delivery** — GitHub отправляет POST на `/webhook` с JSON payload
2. **HMAC Verification** — приложение проверяет подпись `X-Hub-Signature-256` через `hmac.compare_digest` (защита от timing attacks)
3. **Task Enqueue** — для событий `pull_request` (opened/synchronize/reopened) задача отправляется в Redis через `process_pr_task.delay(data)`
4. **FastAPI Response** — мгновенный ответ `200 OK` GitHub, вебхук не блокируется
5. **Celery Execution** — воркер берёт задачу из очереди:
   - Создаёт изолированную `AsyncSession` (не использует FastAPI `Depends`)
   - Создаёт/находит `Organization` и `Repository` в БД
   - Создаёт запись `Review` со статусом `processing`
6. **Config Loading** — запрашивает `.codereview.yml` из ветки PR через GitHub API
7. **File Processing** — для каждого Python-файла:
   - Загружает контент, запускает `ruff check --output-format=json` (timeout 30s)
   - Парсит diff, фильтрует проблемы только по изменённым строкам
   - Если включён AI → отправляет патч в GigaChat, парсит JSON-ответ
8. **Result Publishing** — формирует Markdown-комментарий с разделами `Linter (Ruff)` и `AI Insights`
9. **DB Commit** — сохраняет статус, метрики и сырые данные в PostgreSQL
10. **Notifications** — отправляет краткий отчёт в Telegram

### Обработка отказов

| Сценарий | Поведение |
|----------|-----------|
| GitHub API недоступен | Celery retry с exponential backoff (30s → 60s → 120s), статус `failed` в БД |
| GigaChat timeout/error | Graceful fallback: AI-секция пропускается, Ruff-результаты публикуются |
| Невалидный JSON от AI | `_clean_json()` убирает markdown-обёртки, `json.loads` в `try/except` |
| Дубликат вебхука | Celery `task_acks_late=True` + idempotency на уровне БД (уникальные `pr_number` + `commit_sha`) |

---

## 🛠 Устранение неисправностей

| Проблема | Решение |
|----------|---------|
| **Тесты падают в CI** | Убедитесь, что в `deploy.yml` установлен `PYTHONPATH: .`. Проверьте моки для `config()`. |
| **`denied: installation not allowed...`** | Добавьте `permissions: { packages: write }` в `build-and-deploy` job. |
| **Бот не публикует ревью** | Проверьте права GitHub App: `Contents: Read & Write`, `Pull requests: Read & Write`. Убедитесь, что App установлен в репозиторий. |
| **Celery не обрабатывает задачи** | Убедитесь, что Redis запущен и `REDIS_URL` корректен. Проверьте логи воркера: `celery -A app.core.celery_app worker --loglevel=debug`. |
| **GigaChat возвращает 401** | Проверьте `GIGACHAT_CLIENT_ID/SECRET` в `.env`. Токен кэшируется 29 мин; при 401 кэш автоматически очищается. |
| **`UnicodeDecodeError` на Windows** | Для Alembic используется `psycopg2`. Задайте `$env:PGCLIENTENCODING="UTF8"` перед запуском `alembic upgrade head`. |
| **Телеграм уведомления не приходят** | Проверьте `TELEGRAM_BOT_TOKEN` и `CHAT_ID`. Бот должен быть добавлен в чат с правами на отправку сообщений. |

---

## 🚧 Roadmap

| Приоритет | Фича | Статус |
|-----------|------|--------|
| 🔴 High | Inline comments на конкретных строках PR (`pull_request_review.comments[]`) | 🚧 In Progress |
| 🔴 High | Prometheus метрики (`pr_processed_total`, `ai_analysis_duration`) | 📋 Planned |
| 🟡 Medium | Кэширование AI-анализа по хэшу патча (Redis, TTL 24h) | 📋 Planned |
| 🟡 Medium | Multi-tenant SaaS обёртка (тарифы, Stripe, dashboard) | 💡 Idea |
| 🟢 Low | Поддержка других языков (TypeScript, Go) и линтеров | 💡 Idea |

---

## 📄 Лицензия

Этот проект распространяется под лицензией [MIT License](LICENSE).

---

## 👤 Автор

**Batraz Sekinaev**
- 🐙 GitHub: [@bsekinaev](https://github.com/bsekinaev)
- 💼 LinkedIn: [Batraz Sekinaev](https://linkedin.com/in/bsekinaev)
- ✉️ Telegram: [@bsekinaev](https://t.me/bsekinaev)

*Python Backend Developer • AI Automation Enthusiast • Building resilient systems*
