from sqlalchemy import select, update
from app.db.database import async_session
from app.db.models import User, DialogMessage, Lead

class UserRepository:
    async def get_or_create(self, tg_id: int) -> User:
        """Получает пользователя или создаёт нового"""
        async with async_session() as session:
            stmt = select(User).where(User.tg_id == tg_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                user = User(tg_id=tg_id)
                session.add(user)
                await session.commit()
                await session.refresh(user)

            return user

class DialogRepository:
    async def save_message(self, user_id: int, role: str, content: str):
        """Сохраняет сообщение в историю"""
        async with async_session() as session:
            message = DialogMessage(
                user_id=user_id,
                role=role,
                content=content
            )
            session.add(message)
            await session.commit()

    async def get_recent_messages(self, user_id: int, limit: int = 12) -> list[dict]:
        """Получает последние N сообщений пользователя"""
        async with async_session() as session:
            stmt = (
                select(DialogMessage)
                .where(DialogMessage.user_id == user_id)
                .order_by(DialogMessage.timestamp.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            messages = result.scalars().all()

            # Разворачиваем в хронологическом порядке
            return [
                {"role": msg.role, "content": msg.content}
                for msg in reversed(messages)
            ]

class LeadRepository:
    async def get_by_user_id(self, user_id: int) -> Lead | None:
        """Получает лид по ID пользователя"""
        async with async_session() as session:
            stmt = select(Lead).where(Lead.user_id == user_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def create(self, user_id: int, **kwargs) -> Lead:
        """Создаёт новый лид"""
        async with async_session() as session:
            lead = Lead(user_id=user_id, **kwargs)
            session.add(lead)
            await session.commit()
            await session.refresh(lead)
            return lead

    async def update(self, lead_id: int, **kwargs) -> Lead:
        """Обновляет лид"""
        async with async_session() as session:
            stmt = update(Lead).where(Lead.id == lead_id).values(**kwargs)
            await session.execute(stmt)
            await session.commit()

            stmt = select(Lead).where(Lead.id == lead_id)
            result = await session.execute(stmt)
            return result.scalar_one()
