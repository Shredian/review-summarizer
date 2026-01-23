"""Исключения репозиториев."""


class RepositoryError(Exception):
    """Базовое исключение репозитория."""
    pass


class NotFound(RepositoryError):
    """Сущность не найдена."""
    pass


class AlreadyExists(RepositoryError):
    """Сущность уже существует."""
    pass
