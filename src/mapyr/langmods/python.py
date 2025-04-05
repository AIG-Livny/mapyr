from mapyr.core import *
import mapyr.logger

def run(rule:Rule) -> int:
    target_path = rule.prerequisites[0].target

    logger.info(f"{color_text(35,'Script running')}: {target_path}")

    if not os.path.isabs(target_path):
        target_path = os.path.join(rule.parent.private_config.CWD, target_path)

    path = os.path.dirname(target_path)
    if not os.path.exists(path):
        os.makedirs(path,exist_ok=True)

    return get_module(target_path).run(rule)
