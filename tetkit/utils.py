import importlib
import os
import pkgutil
import random
import string

from pyramid.paster import bootstrap
from pyramid.request import Request
from sqlalchemy.orm import Session


def create_request(config_path: str) -> Request:
    if not config_path.endswith(
        (
            "development.ini",
            "production.ini",
            "test.ini",
            "ci.ini",
        )
    ):
        raise ValueError("Invalid config path")

    with bootstrap(config_path) as app:
        return app["request"]


def create_db_session(request: Request) -> Session:
    return request.find_service(Session)


def import_all(package_path: str) -> int:
    ospath = package_path.replace(".", os.sep)
    imported = 0
    for module_loader, name, ispkg in pkgutil.iter_modules([ospath]):
        importlib.import_module(f"{package_path}.{name}")
        imported += 1

    return imported


def get_random_string(length: int) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def camel_to_snake(string: str) -> str:
    return "".join(["_" + i.lower() if i.isupper() else i for i in string]).lstrip("_")
