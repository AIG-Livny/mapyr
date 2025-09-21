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

def enable_log_file(path:str):
    fh = logging.FileHandler(path,"w+")
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(thread)s [%(levelname)s] %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)