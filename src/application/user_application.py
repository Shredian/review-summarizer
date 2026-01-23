from typing import List, Optional
from uuid import UUID

from src.domain.models.user import User
from src.infrastructure.db.repositories.user_repository import UserRepository
from src.utils.logger import logger


class UserApplication:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def create(self, user: User) -> UUID:
        """Создание пользователя."""
        logger.info(f"Создание пользователя: {user.display_name}")
        user_id = await self.user_repository.create(user)
        logger.info(f"Пользователь создан с ID: {user_id}")
        return user_id

    async def get(self, user_id: UUID) -> User:
        """Получение пользователя по ID."""
        return await self.user_repository.get(user_id)

    async def get_optional(self, user_id: UUID) -> Optional[User]:
        """Получение пользователя по ID или None, если не найден."""
        return await self.user_repository.get_optional(user_id)

    async def list(self, limit: int = 100, offset: int = 0) -> List[User]:
        """Получение списка пользователей с пагинацией."""
        return await self.user_repository.list(limit=limit, offset=offset)

    async def update(
        self,
        user_id: UUID,
        display_name: Optional[str] = None,
        profile_url: Optional[str] = None,
    ) -> User:
        """Обновление пользователя."""
        user = await self.user_repository.get(user_id)
        user.update(display_name=display_name, profile_url=profile_url)
        await self.user_repository.update(user)
        logger.info(f"Пользователь {user_id} обновлён")
        return user

    async def delete(self, user_id: UUID) -> None:
        """Удаление пользователя."""
        await self.user_repository.delete(user_id)
        logger.info(f"Пользователь {user_id} удалён")

    async def count(self) -> int:
        """Получение общего количества пользователей."""
        return await self.user_repository.count()
