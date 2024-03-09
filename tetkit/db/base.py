from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import ClauseElement
from tet.sqlalchemy.simple import declarative_base

from tetkit.utils import import_all

Base = declarative_base()


class BaseModel(Base):
    __abstract__ = True
    __table_args__ = {"extend_existing": True}

    id = Column(BigInteger, primary_key=True)
    created_at = Column(
        DateTime,
        nullable=True,
        default=datetime.utcnow,
    )
    updated_at = Column(
        DateTime,
        nullable=True,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    @classmethod
    def get_or_create(
        cls,
        *,
        db_session: Session,
        defaults: dict = None,
        **kwargs,
    ) -> tuple:
        """
        Inspried by Django's get_or_create()
        Note: db_session doesn't commit here so it should be used in
        a transaction manager

        Example:
        Try to fetch obj with prop1 = foo, if not exists then create obj with
        prop1 = foo and prop2 = bar

            obj, created = MyClass.get_or_create(
                prop1="foo",
                defaults={"prop2": "bar"},
            )
        """
        instance = db_session.query(cls).filter_by(**kwargs).one_or_none()
        if instance:
            return instance, False

        params = {k: v for k, v in kwargs.items() if not isinstance(v, ClauseElement)}
        params.update(defaults or {})
        instance = cls(**params)
        db_session.add(instance)
        db_session.flush()

        return instance, True


def _scan_models(path: str):
    if not path:
        raise ImportError("tetkit.db_models_path is blank")

    imported = import_all(path)
    if imported == 0:
        raise ImportError(f"No module can be found under {path}")
