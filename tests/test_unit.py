"""Pruebas unitarias: regla de descuento, configuración de la base de datos y restricciones del modelo."""
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import database
import main
import models


@pytest.mark.parametrize(
    "price, expected",
    [
        (50.0, 50.0),
        (100.0, 100.0),  # el límite no tiene descuento
        (100.01, 90.01),
        (150.0, 135.0),
        (999.99, 899.99),
    ],
)
def test_apply_discount(price, expected):
    assert main.apply_discount(price) == expected


def test_get_database_url_requires_env(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        database.get_database_url()


def test_get_database_url_reads_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://u:p@db:3306/x")
    assert database.get_database_url() == "mysql+pymysql://u:p@db:3306/x"


def test_get_db_yields_session_and_closes_it():
    gen = database.get_db()
    session = next(gen)
    assert isinstance(session, Session)

    closed = []
    session.close = lambda: closed.append(True)
    gen.close()
    assert closed == [True]


def test_stock_cannot_be_negative(db):
    db.add(models.Product(name="Roto", price=1.0, stock=-1))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
