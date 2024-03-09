import abc

import fire

from ..utils import create_request, create_db_session


class BaseScript(abc.ABC):
    db_session = None

    def setup(self, config: str):
        self.request = create_request(config)
        self.db_session = create_db_session(self.request)
        self.settings = self.request.registry.settings

    def teardown(self):
        self.db_session.close()

    @abc.abstractmethod
    def run(self, *, config: str):
        self.setup(config)

        # PLACERHOLDER: do stuff here

        self.db_session.close()

    @classmethod
    def cli(cls):
        fire.Fire(cls().run)
