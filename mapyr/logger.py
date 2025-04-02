import logging
import os

# Color text Win/Lin
if os.name == 'nt':
    def color_text(color,text):
        return f"[{color}m{text}[0m"
else:
    def color_text(color, text):
        return f"\033[{color}m{text}\033[0m"

class ConsoleFormatter(logging.Formatter):
    def __init__(self):
        super().__init__('[%(levelname)s]: %(message)s')

    def format(self, record: logging.LogRecord) -> str:
        if record.levelno >= logging.ERROR:
            record.msg = color_text(91,record.msg)
        if record.levelno == logging.WARNING:
            record.msg = color_text(31,record.msg)
        return super().format(record)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(ConsoleFormatter())

logger = logging.getLogger('mapyr')
logger.propagate = False
logger.setLevel(logging.DEBUG)
logger.addHandler(console_handler)
