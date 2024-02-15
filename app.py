import json
import logging
import logging.config

from flask import Flask
from pyms.flask.app import Microservice

from controller.stay_controller import ss_blueprint

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SSScraperMicroservice(Microservice):
    def init_logger(self):
        if not self.application.config["DEBUG"]:
            super().init_logger()
        else:
            with open('./config/logging_config.json', 'r') as f:
                LOGGING = json.load(f)
                logging.config.dictConfig(LOGGING)


    def create_app(self) -> Flask:
        app = super().create_app()
        app.register_blueprint(ss_blueprint)
        return app


ssscraper = SSScraperMicroservice()
app = ssscraper.create_app()
