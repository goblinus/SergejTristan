"""Базовый класс декларативных ORM-моделей."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Базовый класс всех моделей; metadata — источник для миграций и тестов."""
