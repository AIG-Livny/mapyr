import logging
import os

app_logger : logging.Logger = None

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
            record.msg = color_text(91,record.message)
        if record.levelno == logging.WARNING:
            record.msg = color_text(31,record.message)
        return super().format(record)

file_formatter = logging.Formatter('%(asctime)-15s|PID:%(process)-11s|%(levelname)-8s|%(filename)s:%(lineno)s| %(message)s')

file_path = f"{os.path.dirname(os.path.realpath(__file__))}/debug.log"
file_handler = logging.FileHandler(file_path,'w',encoding='utf8')
file_handler.setFormatter(file_formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(ConsoleFormatter())

rootlog = logging.getLogger()
rootlog.addHandler(file_handler)

app_logger = logging.getLogger('main')
app_logger.propagate = False
app_logger.setLevel(logging.DEBUG)
app_logger.addHandler(file_handler)
app_logger.addHandler(console_handler)
