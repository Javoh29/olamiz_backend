# Rento — архитектура (MVP)

Версия: 1.0 · Июль 2026

## 1. Общая картина

Модульный монолит на Python + мобильный клиент на Flutter. Один репозиторий, один
деплой-юнит на VPS в Узбекистане.

```
                    ┌─────────────────────────────────────────────┐
                    │              VPS (Узбекистан)                │
 Flutter app ──────▶│  nginx                                       │
 (клиент)           │   ├─ FastAPI-приложение (uvicorn)            │
                    │   │   ├─ /api/v1/...   REST для mobile       │
 Google/браузер ───▶│   │   ├─ /             SSR-витрина (Jinja2)  │
 (SEO-витрина)      │   │   ├─ /admin        SQLAdmin              │
                    │   │   └─ /tg/webhook   aiogram 3 (бот)       │
 Telegram ─────────▶│   ├─ ARQ worker (эскалации, автозавершение)  │
 (бот прокатчика)   │   ├─ PostgreSQL 16                           │
                    │   ├─ Redis (ARQ, кэш)                        │
 Eskiz/PlayMobile ◀─│   └─ MinIO (S3: фото карточек и чек-листов)  │
 (SMS, исходящие)   └─────────────────────────────────────────────┘
```

- **API, бот, SSR и админка — одно FastAPI-приложение**, общий domain-слой. Бот подключён
  через webhook (не polling) — живёт в том же процессе.
- **ARQ worker** — отдельный процесс в том же Compose: отложенные задачи эскалаций,
  истечение заявок, автозавершение сделок, пересчёт метрик.
- Всё в Docker Compose. Бэкапы Postgres — pg_dump по крону на отдельный диск/бакет
  (внутри УЗ — требование ПД).

## 2. Модули domain-слоя

```
domain/
├── users          # клиенты: OTP-аутентификация, профиль, рейтинг клиента
├── suppliers      # прокатчики: онбординг (создаются из админки), точки, привязка TG
├── catalog        # категории (управляются платформой), карточки (listing), модерация, units
├── booking        # сделки: статусная машина, проверка доступности, отмены
├── checklists     # чек-листы выдачи/возврата, фото
├── reviews        # двойные слепые отзывы, рейтинги, «соответствует фото»
├── notifications  # эскалации TG→SMS(→звонок), шаблоны ru/uz, лог отправок
├── disputes       # споры и их разбор
└── geo            # регион → город → район
```

Правило: `api/`, `bot/`, `web/`, `admin/` — тонкие адаптеры, вся логика в `domain/`.
Смена статуса сделки — только через методы статусной машины `domain/booking`.

## 3. Модель данных (основные сущности)

```
regions ─< cities ─< districts

users(id, phone UNIQUE, name?, client_rating, deals_count, created_at)
offer_acceptances(user_id | supplier_id, offer_version, accepted_at)

suppliers(id, display_name, legal_type[individual|legal], phone, district_id,
          address, has_delivery, tg_chat_id?, status[active|paused],
          response_median_sec?, requests_count, rating, created_at)
  # паспорт/ИНН/реквизиты — отдельная таблица supplier_private с ограниченным доступом

categories(id, parent_id?, name_ru, name_uz, slug UNIQUE, depth<=3, sort)

listings(id, supplier_id, category_id, title, description, price_per_day,
         deposit_kind[money|passport|none], deposit_amount?, quantity,
         status[draft|moderation|active|hidden], rating, fits_photo_pct, slug UNIQUE)
listing_photos(id, listing_id, url, sort)

units(id, listing_id, inventory_no?, status[active|repair|retired])
  # в MVP создаются автоматически по quantity, наружу не видны

bookings(id, listing_id, client_id, supplier_id, date_start, date_end,
         status, client_comment?, cancel_reason?,
         created_at, first_action_at?, confirmed_at?, issued_at?,
         returned_at?, closed_at?, closed_by_admin?, admin_log?)

checklist_reports(id, booking_id, kind[issue|return], party[client|supplier],
                  checks jsonb, created_at)
checklist_photos(id, report_id, url)

reviews(id, booking_id, author[client|supplier],
        target[supplier|listing|client], stars, matches_photo?, text?,
        created_at, published_at?)   # двойная слепая публикация

disputes(id, booking_id, opened_by, reason, status[open|resolved],
         resolution?, admin_id?, created_at, resolved_at?)

notifications_log(id, booking_id?, recipient, channel[tg|sms|call],
                  template, status[sent|failed], sent_at)
```

Ключевые ограничения:
- Телефон прокатчика клиенту отдаётся ТОЛЬКО при `booking.status ∈ {confirmed, active, ...}` —
  проверка на уровне API-схем (в Pydantic-ответах поле условное), не на фронте.
- `supplier_private` (паспорт/ИНН) — недоступна из публичного API вообще, только админка.

## 4. Статусная машина сделки

```
pending ──confirm──▶ confirmed ──issue(чек-лист)──▶ active ──return ok──▶ completed
   │                    │                              │
   │ decline            │ cancel (клиент/прокатчик,    │ return с проблемой
   ├──▶ declined        │  с причиной)                 ├──▶ dispute ──админ──▶ completed
   │ timeout 24h        ├──▶ cancelled                 │                       или cancelled
   └──▶ expired         │                              │ 3 дня после date_end
                        │                              └──▶ auto-completed (+уведомления)
```

- `pending` НЕ резервирует остаток. Резервируют только `confirmed` и `active`.
- Подтверждение — в транзакции: `SELECT ... FOR UPDATE` по listing, пересчёт пересечений
  дат confirmed/active-броней; если занято ≥ quantity → авто-отказ «на эти даты всё занято».
- Пересечение дат: [date_start, date_end) — стандартная полуоткрытая логика.
- Любой переход пишется в лог (кто, когда, из какого статуса в какой, причина).
- Принудительное закрытие админом — из любого статуса, с обязательным `admin_log`.

## 5. Доступность и календарь

Доступность карточки на даты [s, e):
`booked = COUNT(bookings WHERE listing_id=X AND status IN (confirmed, active)
AND date_start < e AND date_end > s)`; свободно, если `booked < quantity`.

Календарь в боте прокатчика (MVP) — список: «сегодня выдать: …», «сегодня принять: …»,
«ближайшие брони: …». Визуальный календарь — v1.1.

## 6. Уведомления и эскалация (ARQ)

При создании заявки:
1. t=0 — Telegram-пуш прокатчику (inline-кнопки «Подтвердить/Отклонить»).
2. t=+3 мин — если `first_action_at IS NULL` → SMS.
3. t=+7 мин — автозвонок (v1.1; провайдер телефонии — тот же SMS-шлюз или отдельно).
4. t=+15 мин — клиенту в app: «Прокатчик пока не ответил, посмотрите похожие» + подборка.
5. t=+24 ч — заявка → `expired`, уведомления обеим сторонам.

Все интервалы — конфиг (`settings`), не хардкод. Каждая отправка — запись в
`notifications_log`. SMS-шаблоны — ru/uz, короткие (стоимость!).

Другие задачи worker'а: автозавершение сделок (+3 дня после date_end), напоминания
об отзыве, публикация слепых отзывов (по факту обоих или через 7 дней), пересчёт
`response_median_sec` (по последним 20 заявкам) и рейтингов.

## 7. Ранжирование выдачи каталога (MVP)

Простая взвешенная формула, коэффициенты в конфиге:

```
score = w1 * response_speed_score   # быстрее отвечает — выше
      + w2 * rating_score           # рейтинг прокатчика и карточки
      + w3 * completeness_score     # качество карточки (фото, описание)
      - w4 * cancel_rate            # отмены прокатчиком — вниз
```

Новички (нет истории) получают нейтральные значения — не топить и не поднимать.
Формула — в одном месте (`domain/catalog/ranking.py`), обязательно с тестами.

## 8. API, бот, SSR — детали

Полные контракты, флоу и сценарии бота — в `docs/backend.md`
(эндпоинты, транзакция подтверждения, FSM чек-листов, SEO-требования витрины).

## 9. Flutter app — детали

Структура, карта экранов, UX-требования и работа с фото — в `docs/frontend.md`;
визуальные токены и правила — в `docs/design.md`.

## 10. Нефункциональные требования

- **ПД в УЗ:** Postgres, MinIO, бэкапы — только на серверах в Узбекистане. Внешние
  сервисы не получают ПД (в FCM — только токены и booking_id, без имён/телефонов).
- **Нагрузка MVP смешная** (десятки сделок/день) — оптимизировать не надо, но:
  индексы на bookings(listing_id, status, date_start, date_end), listings(category_id,
  district), полнотекст по title — сразу.
- **Наблюдаемость:** structlog (JSON), Sentry (self-hosted или без ПД в событиях),
  healthcheck-эндпоинт, uptime-мониторинг.
- **Секреты** — из env, не в репозитории. Один `deploy/.env.example` как контракт.
- **Тесты:** обязательны на статусную машину, проверку доступности (гонки!),
  эскалации, скрытие телефона. Остальное — по мере.
- OTP: rate limit на телефон и IP; коды 6 цифр, TTL 5 мин; сообщения через
  конфигурируемый SMS-провайдер (интерфейс `SmsGateway`, реализации Eskiz/PlayMobile).

## 11. Чего НЕ делать в MVP (осознанно)

- Платежи, эскроу, холд залога — фаза N (не проектировать сейчас, не блокировать потом).
- Микросервисы, Kubernetes, брокеры сообщений — нет.
- Свои приложения для прокатчика — нет, только Telegram-бот.
- Flutter Web — фаза 2+ (app.rento.uz), витрина остаётся SSR HTML.
- PostGIS/гео-радиусы — район как справочник достаточен.
- Чат клиент↔прокатчик внутри платформы — после подтверждения есть телефоны; чат — потом.
