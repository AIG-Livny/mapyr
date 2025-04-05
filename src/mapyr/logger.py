import logging
import mapyr.utils as utils

class ConsoleFormatter(logging.Formatter):
    def __init__(self):
        super().__init__('[%(levelname)s]: %(message)s')

    def format(self, record: logging.LogRecord) -> str:
        if record.levelno >= logging.ERROR:
            record.msg = utils.color_text(91,record.msg)
        if record.levelno == logging.WARNING:
            record.msg = utils.color_text(31,record.msg)
        return super().format(record)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(ConsoleFormatter())

logger = logging.getLogger('mapyr')
logger.propagate = False
logger.setLevel(logging.DEBUG)
logger.addHandler(console_handler)
