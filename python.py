from mapyr.core import *
import mapyr.logger

def run(rule:Rule) -> int:
    app_logger.info(f"{color_text(35,'Script running')}: {os.path.relpath(rule.prerequisites[0])}")

    path = os.path.dirname(rule.target)
    if not os.path.exists(path):
        os.makedirs(path,exist_ok=True)

    return get_module(rule.prerequisites[0]).run(rule)
