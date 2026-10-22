---
name: install
description: Клонирование и локальный запуск «Дивидендного календаря»: backend на uv/FastAPI/SQLite с тестовой БД backend/divcal.db и frontend на Vue 3/Vite. Использовать, когда нужно поднять проект после клонирования или проверить, что он запускается.
allowed-tools: Bash, Read, Glob, Grep
---

# Локальный запуск «Дивидендного календаря»

Цель: поднять API на `http://127.0.0.1:8000` и интерфейс на `http://localhost:5173`, используя готовую тестовую БД `backend/divcal.db`. База уже содержит демо-данные; создавать новую или запускать сборщики данных не нужно.

## 0. Проверка окружения

Проверь наличие инструментов и версий:

```bash
git --version
uv --version          # требуется Python >= 3.11
node --version        # требуется >= 20
npm --version
```

Если репозитория ещё нет:

```bash
git clone git@github.com:goblinus/SergejTristan.git
# без настроенного SSH:
# git clone https://github.com/goblinus/SergejTristan.git
cd SergejTristan
```

Если `uv` или Node не установлены — не устанавливай их молча: сообщи пользователю и дай ссылки (<https://docs.astral.sh/uv/>, <https://nodejs.org/>).

Дальнейшие команды выполняются из корня репозитория.

## 1. Бэкенд

```bash
cd backend
```

1. Убедись, что тестовая БД на месте:

   ```bash
   test -f divcal.db && echo "db ok"
   ```

   Если файла нет — **остановись** и сообщи: `divcal.db` должна лежать в `backend/`. Не создавай пустую БД: без демо-данных интерфейс будет пустым (миграции создадут только схему).

2. Установи зависимости и проверь схему:

   ```bash
   uv sync
   uv run alembic current        # ожидается 001_initial (head)
   ```

   Если ревизия не определена или таблиц нет:

   ```bash
   uv run alembic upgrade head
   ```

   `upgrade head` идемпотентен и не удаляет данные.

3. Запусти API в фоне:

   ```bash
   uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

4. Проверь:

   ```bash
   curl -fsS http://127.0.0.1:8000/health
   curl -fsS http://127.0.0.1:8000/api/v1/watchlist
   ```

   Ожидается `{"status":"ok"}` и список из двух сторожков (`HNFG`, `SAGOP`). В справочнике — 510 тикеров.

## 2. Фронтенд

В отдельном терминале:

```bash
cd frontend
npm ci            # если node_modules отсутствует; package-lock.json в репозитории
npm run dev
```

Vite поднимается на `http://localhost:5173` и проксирует `/api` и `/static` на `127.0.0.1:8000`. Если порт 5173 занят, Vite выберет следующий — возьми фактический URL из вывода.

Проверка:

```bash
curl -fsS http://localhost:5173/ > /dev/null && echo "ui ok"
```

## 3. Что открыть

- Календарь: <http://localhost:5173/calendar> — собрания за текущий месяц; собрания демо-данных приходятся на ноябрь 2026, переключи месяц стрелкой «›».
- Сторожки: <http://localhost:5173/me> — `HNFG` и `SAGOP` с днями до события.
- Swagger API: <http://127.0.0.1:8000/docs>.

Демо-данные: 510 тикеров, 6 собраний (ноябрь 2026), 2 сторожка, логотипы у 6 тикеров. `DSI` отображается как `—`: сбор истории дивидендов ещё не реализован (см. таблицу «Что нужно доделать» в `backend/README.md`).

## 4. Остановка

Останови фоновые процессы, запущенные на шагах 1–2 (Ctrl+C в их терминалах либо заверши процессы по PID). Не оставляй uvicorn и Vite висеть после проверки, если пользователь не просил оставить их запущенными.

## Важно

- **Не запускай** `fetch_tickers_moex`, `fetch_meetings_disclosure`, `fetch_dividend_history_moex`: они ходят в сеть и перезапишут демо-данные.
- `sync_logos` безопасен и идемпотентен, но требует непустой `backend/assets/logos/`.
- Не коммить `divcal.db`, `node_modules/`, `.venv/`, `frontend/dist/`.

## Диагностика

| Симптом | Решение |
|---|---|
| `error: No solution found ... pil` | Устаревший `pyproject.toml`; выполни `git pull` (зависимость удалена) |
| `[Errno 10048]` / порт 8000 занят | Останови старый процесс: `netstat -ano \| findstr :8000`, затем `taskkill /PID <pid> /F` (Windows) или `kill <pid>` |
| Vite пишет «Port 5173 is in use» | Это нормально: используй порт из вывода (например, 5174) |
| `no such table` при запросе | `uv run alembic upgrade head` в `backend/` |
| `uv: command not found` | Установи uv: <https://docs.astral.sh/uv/> |
| `node: command not found` или version < 20 | Установи/обнови Node.js |
| Логотипы отдают 404 | `uv run python -m scripts.sync_logos` в `backend/` (нужны файлы в `assets/logos/`) |
| Порт 8000 нужен другой | Поменяй порт в команде uvicorn **и** `server.proxy.target` в `frontend/vite.config.ts` |

## Отчёт

Сообщи пользователю: версии `uv` и Node, URL API и UI, результат проверок `/health` и `/api/v1/watchlist`, список запущенных процессов и как их остановить. Если что-то не запустилось — укажи точную команду и текст ошибки, не маскируй сбой.
