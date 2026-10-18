# Структура репозитория проекта

```test
SergeyTristan/
├── README.md
├── docker-compose.yml
├── .env.example
├── Makefile
├── pyproject.toml
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── deps.py
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── issuers.py
│   │   │   ├── events.py
│   │   │   ├── calendar.py
│   │   │   ├── watchlist.py
│   │   │   ├── notifications.py
│   │   │   └── admin.py
│   │   ├── models/          # SQLAlchemy
│   │   ├── schemas/         # Pydantic
│   │   ├── services/        # бизнес-логика
│   │   ├── ws/              # WebSocket
│   │   └── utils/
│   ├── ingestion/
│   │   ├── collectors/
│   │   │   ├── moex_iss.py
│   │   │   ├── edisclosure.py
│   │   │   └── base.py
│   │   ├── parsers/
│   │   │   ├── moex_dividends.py
│   │   │   ├── edisclosure_events.py
│   │   │   └── base.py
│   │   ├── normalizer.py
│   │   ├── loader.py
│   │   └── dedup.py
│   ├── tasks/
│   │   ├── celery_app.py
│   │   ├── ingest.py
│   │   ├── notify.py
│   │   └── reconcile.py
│   ├── migrations/          # Alembic
│   └── tests/
│       ├── fixtures/        # сохранённые HTML/JSON
│       ├── test_parsers.py
│       ├── test_normalizer.py
│       └── test_api.py
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── package.json
├── infra/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
└── docs/
    ├── architecture.md
    ├── data-model.md
    └── sources.md
```