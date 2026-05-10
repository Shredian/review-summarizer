from uuid import UUID

from src.domain.models.user import User
from src.infrastructure.db.repositories.user_repository import UserRepository
from src.utils.logger import logger


class UserApplication:
    """CRUD и списки пользователей (авторов отзывов)."""

    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def create(self, user: User) -> UUID:
        logger.info(f"Создание пользователя: {user.display_name}")
        user_id = await self.user_repository.create(user)
        logger.info(f"Пользователь создан с ID: {user_id}")
        return user_id

    async def get(self, user_id: UUID) -> User:
        return await self.user_repository.get(user_id)

    async def get_optional(self, user_id: UUID) -> User | None:
        return await self.user_repository.get_optional(user_id)

    async def list(self, limit: int = 100, offset: int = 0) -> list[User]:
        return await self.user_repository.list(limit=limit, offset=offset)

    async def update(
        self,
        user_id: UUID,
        display_name: str | None = None,
        profile_url: str | None = None,
    ) -> User:
        user = await self.user_repository.get(user_id)
        user.update(display_name=display_name, profile_url=profile_url)
        await self.user_repository.update(user)
        logger.info(f"Пользователь {user_id} обновлён")
        return user

    async def delete(self, user_id: UUID) -> None:
        await self.user_repository.delete(user_id)
        logger.info(f"Пользователь {user_id} удалён")

    async def count(self) -> int:
        return await self.user_repository.count()
