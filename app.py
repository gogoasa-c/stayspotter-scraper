import json
import logging
import logging.config
import py_eureka_client.eureka_client as eureka_client

from flask import Flask
from pyms.flask.app import Microservice

from controller.stay_controller import ss_blueprint

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

eureka_client.init(eureka_server="http://localhost:8761",
                   app_name="scraper",
                   instance_port=8090,
                   instance_host="127.0.0.1")


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
