"""
Создание первого пользователя-администратора.
Запуск: python create_user.py admin@monitix.ru mypassword
"""
import asyncio
import sys
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings
from app.db.models import User
import uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_user(email: str, password: str, org_id: str):
    engine = create_async_engine(settings.database_url)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        user = User(
            id=uuid.uuid4(),
            org_id=uuid.UUID(org_id),
            email=email,
            hashed_password=pwd_context.hash(password),
            role="admin",
            full_name="Администратор",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        print(f"Пользователь создан: {email}")

    await engine.dispose()


if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "admin@monitix.ru"
    password = sys.argv[2] if len(sys.argv) > 2 else "admin123"
    org_id = "00000000-0000-0000-0000-000000000001"
    asyncio.run(create_user(email, password, org_id))