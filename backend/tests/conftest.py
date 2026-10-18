from __future__ import annotations
import os
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database import Base, get_db
from app.main import app
from app.models import User, UserRole
from app.auth import hash_password, create_access_token
from app.llm.adapters.mock_adapter import MockLLMAdapter

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def student_user(db_session: Session) -> User:
    user = User(
        email="test_student@mirai.dev",
        hashed_password=hash_password("password123"),
        role=UserRole.STUDENT,
        full_name="Alice Student",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session: Session) -> User:
    user = User(
        email="test_admin@mirai.dev",
        hashed_password=hash_password("adminpass123"),
        role=UserRole.ADMIN,
        full_name="Bob Admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def student_auth_headers(student_user: User) -> dict:
    token = create_access_token(
        data={"sub": str(student_user.id), "role": student_user.role, "email": student_user.email}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(admin_user: User) -> dict:
    token = create_access_token(
        data={"sub": str(admin_user.id), "role": admin_user.role, "email": admin_user.email}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_llm_adapter() -> MockLLMAdapter:
    return MockLLMAdapter(model="mock-unit-test")
