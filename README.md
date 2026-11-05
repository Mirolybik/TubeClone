# TubeClone — клон YouTube на FastAPI + React

Полнофункциональный видеосервис: загрузка и потоковая раздача видео, публичные,
приватные и скрытые ролики, каналы, подписки, плейлисты, комментарии, реакции,
история просмотров, жалобы и панели модератора/администратора.

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.x, PostgreSQL 16, JWT, ffmpeg.
- **Frontend:** React 18 + Vite + React Router, тёмная тема в стиле YouTube
  (Roboto, плоские цвета, без градиентов и размытия).
- **Мониторинг:** Prometheus + Grafana, готовый дашборд подключается автоматически.
- **Тесты:** pytest + httpx, 61 проверка API, сервисов и метрик.
- **Swagger:** `http://localhost:<порт>/docs` (OAuth2 password flow).
- **Запуск одной командой:** `./run.sh`.
- **Хранилище:** локальная файловая система в Docker-томе, раздача через HTTP Range.

---

## Быстрый старт

Требуется установленный Docker с плагином Compose.

```bash
cd youtube-clone
./run.sh
```

Скрипт:

1. проверяет наличие Docker и `docker compose`;
2. создаёт `.env` с настройками по умолчанию, если его нет;
3. собирает образ (frontend + backend) и поднимает PostgreSQL, приложение,
   Prometheus и Grafana;
4. при первом запуске создаёт демо-пользователей, видео, комментарии, жалобы и плейлисты.

После старта:

| Что | Адрес |
|---|---|
| Приложение | `http://localhost:8000` |
| Swagger UI | `http://localhost:8000/docs` |
| ReDoc | `http://localhost:8000/redoc` |
| Health-check | `http://localhost:8000/api/health` |
| Метрики Prometheus | `http://localhost:8000/metrics` |
| Prometheus | `http://localhost:9090` |
| Grafana | `http://localhost:3000` (`admin` / `admin`) |

> В текущем рабочем окружении порт `8000` занят другим сервисом, поэтому в `.env`
> указан `APP_PORT=8010`. Проверить фактический порт: `cat .env`.
> Если порт занят, измените `APP_PORT` в `.env` и перезапустите `./run.sh`.
>
> Порт `9090` тоже занят, поэтому Prometheus в `.env` слушает `PROMETHEUS_PORT=9091`
> (`http://localhost:9091`). Grafana остаётся на `3000`.

### Команды управления

```bash
./run.sh          # собрать и запустить (то же, что ./run.sh up)
./run.sh down     # остановить контейнеры
./run.sh logs     # логи приложения в реальном времени
./run.sh reset    # остановить и удалить БД, медиафайлы и данные мониторинга
./run.sh test     # запустить pytest в отдельном контейнере
```

Полный сброс демо-данных:

```bash
./run.sh reset
./run.sh
```

---

## Мониторинг: Prometheus и Grafana

Приложение отдаёт метрики на `GET /metrics` в формате Prometheus. Сбор
настроен в `monitoring/prometheus/prometheus.yml`, дашборд и datasource
провижнятся в Grafana автоматически — вручную ничего импортировать не нужно.

- **Prometheus:** `http://localhost:9090` (порт задаётся `PROMETHEUS_PORT`).
- **Grafana:** `http://localhost:3000` (порт задаётся `GRAFANA_PORT`).
  Логин и пароль по умолчанию — `admin` / `admin`, меняются через
  `GRAFANA_ADMIN_USER` и `GRAFANA_ADMIN_PASSWORD` в `.env`.
- Дашборд **TubeClone — сервис и бизнес-метрики** лежит в папке `TubeClone`
  и открывается как домашний.

Что показывает дашборд:

| Блок | Панели |
|---|---|
| Обзор API | RPS, доля ошибок 5xx, p95 задержки, запросы в работе, всего запросов, uptime |
| Трафик и задержки | RPS по кодам ответа и эндпоинтам, p50/p95/p99, распределение задержки |
| Бизнес-метрики | загрузки, просмотры, регистрации, жалобы, входы, активность, объём загрузок |
| Процесс | параллельные запросы, RSS и виртуальная память |

Метрики приложения:

- `tubeclone_http_requests_total{method,path,status}` — HTTP-запросы к API;
- `tubeclone_http_request_duration_seconds{method,path}` — гистограмма задержки;
- `tubeclone_http_requests_in_progress` — запросы, выполняющиеся сейчас;
- `tubeclone_videos_uploaded_total`, `tubeclone_upload_bytes_total` — загрузки;
- `tubeclone_video_views_total` — отмеченные просмотры;
- `tubeclone_user_logins_total{result}`, `tubeclone_user_registrations_total` — входы и регистрации;
- `tubeclone_reports_created_total{category}` — жалобы по категориям.

---

## Тесты

Тесты используют настоящий FastAPI-стек через `TestClient`, но работают на
SQLite и без демо-данных, поэтому не трогают рабочую PostgreSQL и медиатеку.

```bash
./run.sh test
```

Команда собирает отдельный образ (`target: test`), устанавливает
`backend/requirements-dev.txt` и запускает pytest. Локально:

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
```

Покрытие:

- аутентификация: регистрация, вход по username/email, выход, профиль, OAuth2 token;
- доступ к видео: public/unlisted/private/hidden, allowlist, роли, владелец;
- стриминг: полный ответ, `Range` (включая suffix), `416`, приватный кэш;
- загрузка: форматы, пустой файл, превью, обновление и удаление;
- реакции, просмотры, история, комментарии и ответы;
- каналы, подписки, лента, поиск, плейлисты;
- модерация: жалобы, скрытие/восстановление, resolve с hide;
- админка: статистика, роли, блокировки;
- сервисы: `MediaService`, `VideoStreamer`, `AccessPolicy`;
- метрики: `/metrics`, HTTP-счётчики и бизнес-счётчики.

---

## Демо-аккаунты

Вход возможен по **username** или **email**. Пароли одинаковы для всех способов входа.

| Логин | Пароль | Роль | Что показывает |
|---|---|---|---|
| `admin` | `Admin123!` | администратор | статистика, пользователи, роли, блокировки |
| `moderator` | `Moder123!` | модератор | жалобы, скрытие/восстановление видео |
| `creator` | `Creator123!` | пользователь-автор | свои видео, приватный доступ, плейлисты |
| `maria` | `Maria123!` | пользователь-автор | второй канал с видео |
| `user` | `User123!` | пользователь | просмотр, лайки, комментарии, подписки |

Демо-видео генерируются через ffmpeg при первом запуске: однотонные обложки
без градиентов, чтобы интерфейс выглядел строго. Среди них есть:

- **приватный** ролик «Приватный влог: только для своих» — доступен владельцу
  (`creator`), пользователям из allowlist (`user`, `maria`), модераторам и админам;
- **unlisted** ролик «Секреты монтажа видео» — не попадает в ленту/поиск, но
  открывается по прямой ссылке;
- **скрытый** ролик «Скрытый ролик: пример модерации» — виден владельцу и
  модераторам, но не зрителям.

---

## Роли и права

| Возможность | Пользователь | Модератор | Администратор |
|---|:---:|:---:|:---:|
| Смотреть публичные/unlisted видео | ✅ | ✅ | ✅ |
| Смотреть приватное видео по allowlist | ✅ | ✅ | ✅ |
| Загружать видео, вести канал, плейлисты | ✅ | ✅ | ✅ |
| Лайки, дизлайки, комментарии, подписки | ✅ | ✅ | ✅ |
| Жаловаться на видео | ✅ | ✅ | ✅ |
| Видеть скрытые видео и очередь жалоб | ❌ | ✅ | ✅ |
| Скрывать/восстанавливать видео | ❌ | ✅ | ✅ |
| Управлять ролями и блокировками | ❌ | ❌ | ✅ |
| Видеть статистику сервиса | ❌ | ❌ | ✅ |

Владелец всегда видит свои видео (включая приватные и скрытые) и управляет
доступом к ним.

---

## Экраны

- **Главная** — лента публичных опубликованных видео с превью, сортировкой
  «Новые / Популярные» и переключателем вида.
- **Просмотр видео** — HTML5-плеер с Range-стримингом и переключателем качества
  (оригинал / 1080p / 720p / 480p, если версии созданы при загрузке),
  лайк/дизлайк, подписка, комментарии и ответы, похожие видео, добавление в
  плейлист, жалоба, редактирование/удаление своего видео, управление доступом к
  приватному видео.
- **Канал** — информация об авторе, его видео и плейлисты, подписка/отписка.
- **Поиск** — поиск по названию видео.
- **Загрузка** — файл, прогресс загрузки, название, описание, видимость и
  простой редактор: обрезка начала/конца, поворот и отражение, формат кадра,
  фильтры, скорость, отключение звука и громкость, а также дополнительные
  качества 1080p/720p/480p. Превью можно выбрать кадром из видео, загрузить
  файлом или оставить автоматическим. Превью в браузере приближённое, финальные
  правки применяет ffmpeg на сервере.
- **Вход и регистрация** — JWT в httpOnly cookie, быстрый выбор демо-аккаунта.
- **Подписки** — свежие видео каналов, на которые подписан пользователь.
- **История** — просмотренные видео, удаление отдельных записей и всей истории.
- **Плейлисты** — создание, редактирование, добавление/удаление и сортировка видео.
- **Модерация** — очередь жалоб, скрытие/восстановление видео, фильтры по статусу.
- **Админ-панель** — статистика, поиск пользователей, смена роли, блокировка.

---

## Приватные видео: как это работает

Модель видимости видео:

- `public` — видно всем в ленте, поиске и на канале;
- `unlisted` — не попадает в ленту/поиск, но доступно по прямой ссылке;
- `private` — доступно только владельцу и пользователям из allowlist.

Дополнительно у видео есть статус `published` / `hidden`. Скрытое видео не видят
обычные зрители, но видят владелец, модераторы и администраторы.

**Сценарий выдачи доступа:**

1. Войдите как `creator` и откройте своё приватное видео.
2. Нажмите кнопку **«Доступ (N)»** рядом с действиями под плеером.
3. Введите username пользователя (например, `user`) и нажмите «Разрешить».
4. Пользователь сразу увидит видео по прямой ссылке `/watch/<id>`, его превью и
   поток. Остальные получат `403`.
5. Там же доступ можно отозвать.

Проверка доступа применяется одинаково к деталям видео, превью, потоку,
комментариям и добавлению в плейлист. Приватные ответы кэшируются с
`Cache-Control: private, no-store`.

---

## API и Swagger

- Все эндпоинты API начинаются с `/api`.
- Swagger: `/docs`, ReDoc: `/redoc`.
- Авторизация в браузере — httpOnly cookie `tube_access_token`.
- Для Swagger нажмите **Authorize** и войдите через OAuth2 password flow
  (`/api/auth/token`, поля `username` и `password`).
- Альтернативно можно передавать `Authorization: Bearer <token>`.

Основные группы:

| Префикс | Назначение |
|---|---|
| `/api/auth` | регистрация, вход, выход, профиль, OAuth2 token |
| `/api/feed`, `/api/search`, `/api/history` | лента, подписки, поиск, история |
| `/api/videos` | загрузка, метаданные, Range-поток, превью, реакции, доступ, жалобы |
| `/api/videos/{id}/comments` | комментарии и ответы |
| `/api/channels`, `/api/me/subscriptions` | каналы и подписки |
| `/api/playlists` | плейлисты и их содержимое |
| `/api/moderation` | жалобы, скрытие и восстановление видео |
| `/api/admin` | статистика, пользователи, роли, блокировки |
| `/api/health` | health-check |
| `/metrics` | метрики Prometheus (вне Swagger) |

### Range-стриминг

`GET /api/videos/{id}/stream` поддерживает заголовок `Range` и отвечает `206
Partial Content` с `Content-Range`, `Accept-Ranges: bytes` и `Content-Length`.
Это позволяет перематывать видео в браузере без полной загрузки файла.
Параметр `?quality=720p` (или `480p`, `1080p`) выдаёт соответствующую версию;
без параметра или с `quality=original` отдаётся оригинал.

### Загрузка

`POST /api/videos` принимает `multipart/form-data`:

- `file` — MP4, WebM, MOV или M4V;
- `title`, `description`, `visibility` (`public` / `unlisted` / `private`);
- `thumbnail` — необязательное изображение JPG/PNG/WebP;
- `thumbnail_timestamp` — необязательное время кадра в секундах относительно
  финального видео; приоритетнее загруженного `thumbnail`;
- правки редактора: `trim_start`, `trim_end`, `rotate` (0/90/180/270),
  `flip_horizontal`, `flip_vertical`, `crop_aspect` (`original` / `16:9` /
  `9:16` / `1:1` / `4:3`), `video_filter` (`none` / `grayscale` / `sepia` /
  `contrast` / `bright` / `vivid`), `speed` (0.5–2), `mute`, `volume` (0–2);
- `qualities` — необязательный список дополнительных версий через запятую:
  `1080p,720p,480p`. Версия создаётся, только если исходник выше по высоте;
  оригинал доступен всегда.

Если передана хотя бы одна правка, сервер перекодирует видео в MP4 (H.264 +
AAC) и заменяет загруженный файл. Кадр для превью извлекается уже из
финального видео. Без правок файл сохраняется как есть. Дополнительные
качества генерируются из финальной версии и доступны в плеере.

Лимит размера задаётся `MAX_UPLOAD_MB` (по умолчанию 1024 МБ). Длительность
определяется через `ffprobe`, превью — через `ffmpeg`.

---

## Настройки `.env`

| Переменная | По умолчанию | Описание |
|---|---|---|
| `APP_PORT` | `8000` | порт приложения на хосте |
| `JWT_SECRET` | `change-me-in-production` | секрет подписи JWT, замените в продакшене |
| `MAX_UPLOAD_MB` | `1024` | максимальный размер видеофайла |
| `SEED_DEMO` | `true` | создавать ли демо-данные при пустой БД |
| `PROMETHEUS_PORT` | `9090` | порт Prometheus на хосте |
| `GRAFANA_PORT` | `3000` | порт Grafana на хосте |
| `GRAFANA_ADMIN_USER` | `admin` | логин администратора Grafana |
| `GRAFANA_ADMIN_PASSWORD` | `admin` | пароль администратора Grafana |

Дополнительные переменные окружения приложения: `DATABASE_URL`, `MEDIA_DIR`,
`FRONTEND_DIST`, `COOKIE_SECURE`, `CORS_ORIGINS`, `MAX_THUMBNAIL_MB`.

---

## Структура проекта

```text
youtube-clone/
├── backend/
│   ├── requirements.txt
│   ├── requirements-dev.txt # pytest, httpx, pytest-cov
│   ├── pytest.ini
│   ├── tests/               # API, сервисы, метрики
│   └── app/
│       ├── main.py          # FastAPI, lifespan, SPA fallback, /metrics
│       ├── config.py        # настройки из окружения
│       ├── database.py      # SQLAlchemy engine/session (PostgreSQL и SQLite)
│       ├── models.py        # пользователи, видео, лайки, комментарии, жалобы…
│       ├── schemas.py       # Pydantic-схемы запросов/ответов
│       ├── security.py      # bcrypt + JWT
│       ├── deps.py          # текущий пользователь, проверки ролей
│       ├── permissions.py   # AccessPolicy: доступ к видео и плейлистам
│       ├── metrics.py       # AppMetrics, middleware и /metrics
│       ├── serializers.py   # сборка ответов API
│       ├── pagination.py
│       ├── routers/         # auth, feed, channels, videos, comments,
│       │                    # playlists, moderation, admin
│       └── services/
│           ├── media.py     # MediaService: ffmpeg, файлы, превью
│           ├── editor.py    # VideoEditor: правки и кадры для превью
│           ├── streaming.py # VideoStreamer: Range-стриминг и обложки
│           └── seed.py      # DemoSeeder: демо-пользователи и видео
├── frontend/
│   ├── src/
│   │   ├── api.js           # ApiClient: fetch, XHR-загрузка с прогрессом
│   │   ├── auth.jsx         # контекст авторизации
│   │   ├── App.jsx          # маршруты и guard-компоненты
│   │   ├── components/      # layout, карточки, комментарии, модалки…
│   │   ├── pages/           # все экраны приложения
│   │   └── styles.css       # тёмная тема YouTube: Roboto, плоские цвета
│   └── vite.config.js
├── monitoring/
│   ├── prometheus/
│   │   └── prometheus.yml   # scrape-конфигурация приложения
│   └── grafana/
│       ├── provisioning/    # datasource и провайдер дашбордов
│       └── dashboards/
│           └── tubeclone.json
├── Dockerfile               # multi-stage: Vite build + Python runtime + test
├── docker-compose.yml       # app, PostgreSQL, Prometheus, Grafana, tests
├── run.sh                   # запуск одной командой
└── .env.example
```

### ООП-структура

Ключевая логика вынесена в небольшие классы с одной ответственностью:

- `MediaService` — проверка форматов, сохранение файлов, ffprobe/ffmpeg, превью;
- `VideoEditor` — обрезка, поворот/отражение, кадрирование, фильтры, скорость,
  звук и извлечение кадра для превью;
- `AccessPolicy` — единые правила доступа к видео, плейлистам и подпискам;
- `VideoStreamer` — HTTP Range, заголовки кеширования и выдача обложек;
- `DemoSeeder` — создание согласованных демо-данных;
- `ApiClient` — HTTP-клиент фронтенда, JSON-запросы и XHR-загрузка.

Роутеры FastAPI остаются тонкими: валидируют запрос, вызывают нужный сервис
и возвращают схему ответа.

---

## Локальная разработка (без Docker для приложения)

Понадобятся Python 3.12+, Node.js 20+ и PostgreSQL 16 (или Docker для БД).

```bash
# 1. PostgreSQL в отдельном контейнере на порту 5433
docker run -d --name tube-postgres \
  -e POSTGRES_DB=tube -e POSTGRES_USER=tube -e POSTGRES_PASSWORD=tube \
  -p 5433:5432 postgres:16-alpine

# 2. Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

export DATABASE_URL=postgresql+psycopg://tube:tube@localhost:5433/tube
export MEDIA_DIR="$PWD/media"
export FRONTEND_DIST="$PWD/frontend/dist"
export SEED_DEMO=true

uvicorn app.main:app --app-dir backend --reload --port 8000
```

```bash
# 3. Frontend (второй терминал)
cd frontend
npm install
npm run dev
```

Vite поднимает dev-сервер на `http://localhost:5173` и проксирует `/api` на
`http://localhost:8000`. Если backend запущен на другом порту, поправьте
`frontend/vite.config.js`.

Сборка production-фронтенда:

```bash
cd frontend
npm run build   # результат в frontend/dist
```

---

## Хранение данных

- **PostgreSQL** — пользователи, видео, комментарии, лайки, подписки, жалобы,
  история, плейлисты.
- **Docker-том `tubeclone_media`** — файлы видео (`/data/media/videos`) и превью
  (`/data/media/thumbnails`).
- **Docker-том `tubeclone_pgdata`** — данные PostgreSQL.

Удалить всё и начать заново: `./run.sh reset`.

---

## Проверка работоспособности

```bash
# Укажите фактический порт из .env (по умолчанию 8000, в этом окружении 8010)
PORT=8010

curl http://localhost:$PORT/api/health
# {"status":"ok","service":"TubeClone"}
```

Проверка потока с Range:

```bash
curl -i -H 'Range: bytes=0-99' http://localhost:$PORT/api/videos/1/stream
# HTTP/1.1 206 Partial Content
# Content-Range: bytes 0-99/<размер>
```

Проверка приватного видео без входа:

```bash
curl -i http://localhost:$PORT/api/videos/3
# HTTP/1.1 403 Forbidden
```

---

## Возможные проблемы

- **`Bind for 0.0.0.0:8000 failed: port is already allocated`** — порт занят.
  Измените `APP_PORT` в `.env` (например, на `8010`) и выполните
  `docker compose up -d`.
- **Долгий первый запуск** — собираются frontend и backend-образ, а также
  генерируются демо-видео через ffmpeg (обычно 30–60 секунд).
- **Демо-данные не появились** — проверьте `SEED_DEMO=true` в `.env` и логи:
  `./run.sh logs`. Сид выполняется только для пустой базы.
- **Видео не проигрывается** — убедитесь, что браузер поддерживает кодек
  загруженного файла (рекомендуется MP4/H.264 + AAC).
