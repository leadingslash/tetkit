import os
from typing import Callable
from unittest import mock

import pytest
import transaction
from alembic.command import upgrade
from alembic.config import Config
from pyramid import testing
from pyramid.paster import get_appsettings
from pyramid.request import apply_request_extensions
from sqlalchemy import engine_from_config
from webtest import TestApp

PYTEST_CONFIG_FILE = os.getenv("PYTEST_CONFIG_FILE", "config/test.ini")


@pytest.fixture(scope="session")
def settings(request):
    return get_appsettings(PYTEST_CONFIG_FILE, name="main")


@pytest.fixture(scope="session")
def pyramid_app_factory(settings, connection):
    # patch setup_sqlalchemy so we can pass the same test `connection` to
    # session_factory.bind() instead creating new engine
    def _models_includeme(config):
        config.include("tet.sqlalchemy.simple")
        config.setup_sqlalchemy(engine=connection)

    def _app(factory_function: Callable):
        # dramatiq_broker_entrypoint()
        with mock.patch("tetkit.db.includeme", _models_includeme):
            app = factory_function(settings)
            testing.setUp(registry=app.registry)

        return app

    yield _app

    testing.tearDown()


@pytest.fixture(scope="session")
def app(pyramid_app):
    return TestApp(pyramid_app)


@pytest.fixture(scope="function")
def pyramid_request(app):
    _request = testing.DummyRequest()
    apply_request_extensions(_request)

    return _request


@pytest.fixture(scope="session")
def connection(settings):
    """
    Setup a SQLAlchemy engine and return a connection so we can use the same
    connection for both `db_session` fixture and the app, thus allowing
    to `rollback` after using `transaction.commit`
    """
    engine = engine_from_config(settings, "sqlalchemy.")
    connection = engine.connect()

    return connection


@pytest.fixture(scope="session")
def db_factory(connection, request):
    """
    TODO:
    * consider using hook pytest_sessionstart
    https://docs.pytest.org/en/latest/reference.html#initialization-hooks
    * add option to reuse DB so we don't always need to drop

    NOTE:
    * alembic upgrade is better than metadata.create_all() since we test
        migration process
    * metadata.drop_all() doesn't remove the alembic table so we need to drop
        schema manually
    """

    def _db(
        *,
        pre_migration_hook=None,
        post_migration_hook=None,
        teardown_hook=None,
    ):
        # transaction.begin()
        db_url = str(connection.engine.url)
        # metadata.create_all(connection.engine)

        if pre_migration_hook:
            pre_migration_hook(connection)
        else:
            connection.execute("CREATE SCHEMA IF NOT EXISTS public;")

        print(">>> Upgrade DB to head")
        alembic_config = Config(PYTEST_CONFIG_FILE)
        alembic_config.set_main_option("sqlalchemy.url", db_url)
        upgrade(alembic_config, "head")

        # NOTE: we can feed some default content here
        # transaction.commit()
        if post_migration_hook:
            post_migration_hook(connection)

        def teardown():
            print("\n>>> Drop DB")
            if connection.in_transaction():
                transaction.abort()
            # metadata.drop_all(engine)

            if teardown_hook:
                teardown_hook(connection)
            else:
                connection.execute("DROP SCHEMA public CASCADE;CREATE SCHEMA public;")

        # we use addfinalizer() here instead of yield fixture so in case there is
        # exception, our teardown can still run correctly
        request.addfinalizer(teardown)

    return _db


@pytest.fixture(scope="function")
def db_session(connection, pyramid_app, request):
    """
    Return a dbsession object and setup a transaction savepoint, which will
    be rolled back after the test
    """
    tx = connection.begin()
    session_factory = pyramid_app.registry.get("tet.sqlalchemy.simple.factories").get(
        ""
    )
    session = session_factory()
    session.tx = tx

    def teardown():
        session.close()
        tx.rollback()
        transaction.abort()

    request.addfinalizer(teardown)

    return session


@pytest.fixture(scope="function")
def route_url(pyramid_request):
    return pyramid_request.route_url
