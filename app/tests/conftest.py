import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from fastapi_users.password import PasswordHelper
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import ObjectDeletedError
from sqlalchemy.pool import StaticPool

from app.application import fastapi_app
from app.db.db import get_session
from app.db.models.base import Base
from app.db.models.user import User


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite:///file:temp.db?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest_asyncio.fixture()
async def async_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///file:temp.db?mode=memory&cache=shared&uri=true",
        echo=False,
        future=True,
        poolclass=StaticPool,
    )
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session_maker() as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session, async_session: AsyncSession):
    async def get_session_override():
        yield async_session

    fastapi_app.dependency_overrides[get_session] = get_session_override

    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


@pytest.fixture()
def admin_user(session: Session):
    password_helper = PasswordHelper()
    password = "password1234"

    user = User(
        email="admin@email.com",
        hashed_password=password_helper.hash(password),
        name="Admin",
        surname="Admin",
        is_verified=True,
        is_superuser=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    yield user

    try:
        session.delete(user)
        session.commit()
    except ObjectDeletedError:
        pass


@pytest.fixture()
def verified_user(session: Session):
    password_helper = PasswordHelper()
    password = "password1234"

    user = User(
        email="johndoe@email.com",
        hashed_password=password_helper.hash(password),
        name="John",
        surname="Doe",
        is_verified=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    yield user

    try:
        session.delete(user)
        session.commit()
    except ObjectDeletedError:
        pass


@pytest.fixture()
def unverified_user(session: Session):
    password_helper = PasswordHelper()
    password = "password1234"

    user = User(
        email="alexmask@email.com",
        hashed_password=password_helper.hash(password),
        name="Alex",
        surname="Mask",
        is_verified=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    yield user

    try:
        session.delete(user)
        session.commit()
    except ObjectDeletedError:
        pass
