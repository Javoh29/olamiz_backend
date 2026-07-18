# Olamiz backend — рабочие заметки

Журнал инженерных решений и договорённостей по ходу разработки. НЕ дублирует `docs/`
(там продуктовый источник истины и решения D1–D21). Сюда пишем: технические решения,
инфраструктуру, отложенное и открытые вопросы, краткий журнал сессий.

## Инфраструктура (dev)

Docker на машине разработки не установлен → Postgres/Redis/MinIO подняты через Homebrew.
Прод остаётся на `deploy/docker-compose.yml`.

- **Postgres 16** (`brew services start postgresql@16`), роль/БД `olamiz`;
  тестовая БД `olamiz_test` создаётся автоматически в `tests/conftest.py`.
- **Redis** (`brew services start redis`) — OTP, rate-limit, ARQ (позже).
- **MinIO** (`brew services start minio`) — S3-хранилище фото; бакет `olamiz`.
  API `:9000`, консоль `:9001`, ключи по умолчанию `minioadmin/minioadmin`.

Команды (из `backend/`): `uv sync`, `uv run ruff check .`, `uv run mypy`, `uv run pytest`,
`uv run alembic upgrade head`, `uv run python -m app.seed`.

## Технические решения

- **Enum** — VARCHAR + CHECK (`native_enum=False, create_constraint=True`), не native PG ENUM:
  проще миграции при изменении набора значений. Применяется ко всем статус-полям.
- **naming_convention** в `Base.metadata` (pk/fk/uq/ck/ix) — детерминированные имена констрейнтов.
- **Сиды** — идемпотентные seed-скрипты (`app/seed`, `python -m app.seed`), не data-миграции.
- **Время** — UTC в БД (`TimestampMixin`), отображение Asia/Tashkent.
- **Auth**: OTP в Redis (6 цифр, TTL 5 мин, rate-limit 3/тел + 10/IP в час, лимит попыток ввода);
  JWT HS256 (pyjwt), access 30 мин / refresh 30 дн. Дефолт `JWT_SECRET` удлинён до 32+ байт.
- **Оферта**: `GET /auth/offer` (версия); `verify` для нового клиента требует
  `offer_accepted` + `offer_version` (проверка ДО расхода OTP-кода); подписанная версия
  фиксируется в `offer_acceptances`.
- **Ошибки API** — единый формат `{code, message_ru, message_uz}`.
- **Тексты пользователю** — в словаре `core/i18n` (ru/uz), не хардкод.
- **Тесты**: тестовая БД с savepoint-rollback на тест, `fakeredis` вместо Redis, httpx ASGI.
- **Добавленные зависимости**: `pyjwt` (runtime), `fakeredis` (dev).

## Порядок модулей (domain)

geo ✓ → suppliers ✓ → users/auth ✓ → catalog (категории ✓, listings/units — в работе) →
booking (статусная машина) → checklists → reviews → notifications → disputes.

## Отложено / открытые вопросы

- nginx-домены `olamiz.uz` + `beramiz.uz` (beramiz в v1.0 — редирект/заглушка) — отложено.
- Реальные SMS-провайдеры (Eskiz/PlayMobile) — сейчас `LogSmsGateway`-заглушка.
- Скрытие телефона прокатчика (backend.md §10.3) — тестируется полноценно после booking.
- Папка репозитория называется `rento_backend` — переименование силами владельца после сессии.

## Журнал сессий

### 2026-07-17 … 2026-07-18
- Инициализация backend (скелет FastAPI/ARQ/deploy), доки перенесены в git.
- Ребренд Rento → Olamiz/Beramiz (D21).
- Модули: geo (+сиды Ташкент/12 районов), suppliers (+supplier_private), users/auth
  (OTP/JWT/me, явный акцепт оферты), catalog·категории (+сиды дерева инструмента).
- Введён `naming_convention`, миграции перегенерированы.
- Dev-инфра поднята через brew (Postgres/Redis/MinIO), т.к. Docker не установлен.
