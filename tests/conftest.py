import os

# Las pruebas nunca deben tocar la base de datos real: se fija antes de importar la app
os.environ["DATABASE_URL"] = "sqlite://"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import database  # noqa: E402
import main  # noqa: E402
import models  # noqa: E402

# Una sola conexión en memoria, compartida por la prueba y por las peticiones a la API
engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    """Sesión sobre una base de datos vacía que se borra al terminar cada prueba."""
    models.Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        models.Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    main.app.dependency_overrides[database.get_db] = override_get_db
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()


@pytest.fixture
def make_user(db):
    def _make(name="Ana", email="ana@example.com"):
        user = models.User(name=name, email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _make


@pytest.fixture
def make_product(db):
    def _make(name="Producto", price=50.0, stock=10):
        product = models.Product(name=name, price=price, stock=stock)
        db.add(product)
        db.commit()
        db.refresh(product)
        return product

    return _make


@pytest.fixture
def count_queries():
    """Cuenta las sentencias SQL que se ejecutan mientras dura la prueba."""
    counter = {"n": 0}

    def _count(*args, **kwargs):
        counter["n"] += 1

    event.listen(engine, "before_cursor_execute", _count)
    yield counter
    event.remove(engine, "before_cursor_execute", _count)
