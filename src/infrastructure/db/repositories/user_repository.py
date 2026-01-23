from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from src.domain.models.user import User
from src.infrastructure.db.models.user import UserDB
from src.infrastructure.db.repositories.exceptions import NotFound


class UserRepository:
    """Репозиторий для работы с пользователями (авторами отзывов) в БД."""

    def __init__(self, session_factory: sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def create(self, user: User) -> UUID:
        """Создает пользователя в БД."""
        async with self.session_factory() as session:
            user_db = user.to_sql_model()
            session.add(user_db)
            await session.commit()
            return user_db.id

    async def get(self, user_id: UUID) -> User:
        """Возвращает пользователя по ID."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(UserDB).where(UserDB.id == user_id)
            )
            user_db = result.scalar_one_or_none()
            if not user_db:
                raise NotFound(f"Пользователь с ID {user_id} не найден")
            return User.from_sql_model(user_db)

    async def get_optional(self, user_id: UUID) -> Optional[User]:
        """Возвращает пользователя по ID или None, если не найден."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(UserDB).where(UserDB.id == user_id)
            )
            user_db = result.scalar_one_or_none()
            if not user_db:
                return None
            return User.from_sql_model(user_db)

    async def list(self, limit: int = 100, offset: int = 0) -> List[User]:
        """Возвращает список пользователей с пагинацией."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(UserDB)
                .order_by(UserDB.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            users_db = result.scalars().all()
            return [User.from_sql_model(u) for u in users_db]

    async def update(self, user: User) -> None:
        """Обновляет пользователя в БД."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(UserDB).where(UserDB.id == user.id)
            )
            user_db = result.scalar_one_or_none()
            if not user_db:
                raise NotFound(f"Пользователь с ID {user.id} не найден")
            
            user_db.display_name = user.display_name
            user_db.profile_url = user.profile_url
            await session.commit()

    async def delete(self, user_id: UUID) -> None:
        """Удаляет пользователя из БД."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(UserDB).where(UserDB.id == user_id)
            )
            user_db = result.scalar_one_or_none()
            if not user_db:
                raise NotFound(f"Пользователь с ID {user_id} не найден")
            
            await session.delete(user_db)
            await session.commit()

    async def get_by_display_name(self, display_name: str) -> Optional[User]:
        """Возвращает пользователя по display_name или None, если не найден."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(UserDB).where(UserDB.display_name == display_name)
            )
            user_db = result.scalar_one_or_none()
            if not user_db:
                return None
            return User.from_sql_model(user_db)

    async def count(self) -> int:
        """Возвращает общее количество пользователей."""
        async with self.session_factory() as session:
            result = await session.execute(select(func.count(UserDB.id)))
            return result.scalar_one()
