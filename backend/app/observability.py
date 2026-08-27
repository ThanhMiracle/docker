import json
import logging
import sys


def configure_logging():
    handler = logging.StreamHandler(sys.stdout)

    class JsonFormatter(logging.Formatter):
        def format(self, record):
            return json.dumps({
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            })

    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
