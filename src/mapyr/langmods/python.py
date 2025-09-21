from mapyr.core import *

def run(rule:Rule) -> CompileCommand:
    target_path = rule.prerequisites[0].target

    compile_command = CompileCommand()
    compile_command._name = utils.color_text(35,'Script running')
    compile_command.output = target_path

    if not os.path.isabs(target_path):
        target_path = os.path.join(rule.parent.private_config.CWD, target_path)

    path = os.path.dirname(target_path)
    if not os.path.exists(path):
        os.makedirs(path,exist_ok=True)

    utils.get_module(target_path).run(rule)

    return compile_command
