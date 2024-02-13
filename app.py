import logging
import logging.config

from bs4 import BeautifulSoup
import requests
import time
import threading as thr

from flask import Flask, Blueprint
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
            level = "DEBUG"
            LOGGING = {
                'version': 1,
                'disable_existing_loggers': False,
                'handlers': {
                    'console': {
                        'level': level,
                        'class': 'logging.StreamHandler',
                    },
                },
                'loggers': {
                    '': {
                        'handlers': ['console'],
                        'level': level,
                        'propagate': True,
                    },
                    'anyconfig': {
                        'handlers': ['console'],
                        'level': "WARNING",
                        'propagate': True,
                    },
                    'pyms': {
                        'handlers': ['console'],
                        'level': "WARNING",
                        'propagate': True,
                    },
                    'root': {
                        'handlers': ['console'],
                        'level': level,
                        'propagate': True,
                    },
                }
            }

            logging.config.dictConfig(LOGGING)

    def create_app(self) -> Flask:
        app = super().create_app()
        app.register_blueprint(ss_blueprint)
        return app


ssscraper = SSScraperMicroservice()
app = ssscraper.create_app()
