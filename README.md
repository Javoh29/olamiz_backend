# Rento — backend

Маркетплейс аренды строительного инструмента в Узбекистане (rento.uz).
Модульный монолит: FastAPI (REST API + Telegram-webhook + SSR-витрина + SQLAdmin) и ARQ worker.

Документация — в [docs/](docs/) (источник истины, читать перед задачей): продукт, архитектура,
backend, frontend, дизайн, реестр решений. Контекст для Claude — [CLAUDE.md](CLAUDE.md).

## Запуск в Docker Compose

```bash
cd deploy
cp .env.example .env      # заполнить секреты (JWT_SECRET, TG_BOT_TOKEN, SMS, …)
docker compose up --build
```

Поднимает postgres:16, redis, minio, api (uvicorn), worker (arq), nginx (порт 80).

- API: http://localhost/api/v1/health · Swagger: http://localhost/api/docs
- SSR-витрина: http://localhost/ · Админка: http://localhost/admin
- MinIO console: http://localhost:9001

## Локальная разработка (без Docker для приложения)

Нужен [uv](https://docs.astral.sh/uv/) и Python 3.12+.

```bash
# инфраструктура — из compose
cd deploy && docker compose up -d postgres redis minio && cd ..

cd backend
uv sync                                   # venv + зависимости (включая dev)
uv run uvicorn app.main:app --reload      # API на http://127.0.0.1:8000
uv run arq app.worker.WorkerSettings      # worker (отдельный терминал)
```

`DATABASE_URL`/`REDIS_URL` по умолчанию смотрят на localhost — совпадает с портами compose.
Переопределение — через env или `backend/.env`.

## Миграции

```bash
cd backend
uv run alembic revision --autogenerate -m "…"   # любое изменение моделей = миграция
uv run alembic upgrade head
```

## Проверки (перед коммитом)

```bash
cd backend
uv run ruff check .           # lint
uv run ruff format --check .  # формат
uv run mypy                   # типы (strict на app/domain)
uv run pytest                 # тесты
```
