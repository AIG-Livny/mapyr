import sys
import os
import concurrent.futures
import traceback
import copy
import threading
import json
import mapyr.utils as utils
from mapyr.exceptions import Exceptions
from mapyr.logger import logger,console_handler

VERSION = '0.9.0'

#----------------------CONFIG--------------------------

class ToolConfig:
    '''
        This config used while sertain build.py running. Config controls MAPYR features
    '''

    def __init__(self) -> None:
        self.MAX_THREADS_NUM : int = 10
        '''
            Build threads limit
        '''

        self.MINIMUM_REQUIRED_VERSION : str = VERSION
        '''
            Minimum required version for this config file
        '''

        self.VERBOSITY : str = "INFO"
        '''
            Verbosity level for console output. Value can be any from logging module: ['CRITICAL','FATAL','ERROR','WARN','WARNING','INFO','DEBUG','NOTSET']
        '''

CONFIG : ToolConfig = ToolConfig()

#----------------------END CONFIG----------------------

#----------------------RULE----------------------------

class Rule:
    def __init__(
            self,
            target              : str,
            parent              : 'ProjectBase',
            prerequisites       : list['Rule']      = None,
            exec                : 'function'        = None,
            phony               : bool              = False,
        ) -> None:

        self.target : str = target
        '''
            Output file or phony name
        '''

        self.prerequisites : list[Rule] = prerequisites if prerequisites else []
        '''
            All rules that have to be done before this rule
        '''

        self.exec : function = exec
        '''
            Execution function: def my_exec_func(rule:Rule) -> CompileCommand | None
        '''

        self.phony : bool = phony
        '''
            Phony target not expects output file, and will be executed every time when called
        '''

        self.parent : ProjectBase = parent
        '''
            Parent project
        '''

        if not self.phony:
            if not os.path.isabs(self.target):
                self.target = f'{self.parent.private_config.CWD}/{self.target}'

    def __str__(self) -> str:
        return f'{self.target}:{self.prerequisites}'

    def __repr__(self) -> str:
        return self.__str__()

#----------------------END RULE------------------------

class ConfigBase:
    '''
        Base class of configs
    '''

    def __init__(self):
        self.CWD = utils.caller_cwd()
        '''
            By default: path where config was created
        '''

        self.dir_members = []
        '''
            List of member names that contains directory path
            By this static list will work `make_abs` function
        '''

        self.parent : ProjectBase = None

    def extend(self, other:'ConfigBase', members : list[str] = None):
        '''
            Must be implemented in children
            members : list of config member names, that will be extended
        '''
        raise NotImplementedError()

    def get_abs_val(self, val:str|list[str]):
        '''
            Make value-"directory path" absolute path
        '''
        if type(val) == str:
            if not os.path.isabs(val):
                val = os.path.join(self.CWD,val)
            return val
        elif type(val) == list:
            result = []
            for v in val:
                if not os.path.isabs(v):
                    v = os.path.join(self.CWD,v)
                result.append(v)
            return result
        else:
            raise ValueError()

    def make_abs(self) -> 'ConfigBase':
        '''
            Make absolute paths
        '''
        for k in self.__dict__.keys():
            if k not in self.dir_members:
                continue
            self.__dict__[k] = self.get_abs_val(self.__dict__[k])
        return self

class CompileCommand:
    def __init__(self):
        self.directory : str = None
        '''
            The working directory of the compilation
        '''

        self.file : str = None
        '''
            The main translation unit source processed by this compilation step.
        '''

        self.arguments : list[str] = None
        '''
            The compile command argv as list of strings.
        '''

        self.command : str = None
        '''
            The compile command as a single shell-escaped string.
            Either arguments or command is required.
            arguments is preferred,
        '''

        self.output : str = None
        '''
            The name of the output created by this compilation step.
        '''

        self._name : str = 'Unnamed'


    def get_dict(self):
        filtered = {k: v for k, v in self.__dict__.items() if v is not None and not k.startswith('_')}
        return filtered

    def __str__(self) -> str:
        return json.dumps(self.get_dict())

#----------------------PROJECT-------------------------

class ProjectBase():
    def __init__(self,
            name:str,
            target:str,
            private_config:ConfigBase = None,
            protected_config:ConfigBase = None,
            public_config:ConfigBase = None,
            subprojects:list['ProjectBase'] = None
        ):
        if not private_config and not protected_config and not public_config:
            raise Exceptions.AtLeastOneConfig()

        self.name = name
        self.target = target
        self.main_rule : Rule = None
        self.rules : list[Rule] = []
        self.subprojects : list['ProjectBase'] = subprojects if subprojects else []
        self.source_names_hash = 0

        self.private_config     : ConfigBase = None
        self.public_config      : ConfigBase = None
        self.protected_config   : ConfigBase = None

        if private_config:
            self.private_config = copy.deepcopy(private_config)
            self.private_config.parent = self

        if public_config:
            if self.private_config:
                self.private_config.extend(public_config)
            else:
                self.private_config = copy.deepcopy(public_config)
                self.private_config.parent = self
            self.public_config = copy.deepcopy(public_config)
            self.public_config.parent = self

        if protected_config:
            if self.private_config:
                self.private_config.extend(protected_config)
            else:
                self.private_config = copy.deepcopy(protected_config)
                self.private_config.parent = self
            self.protected_config = copy.deepcopy(protected_config)
            self.protected_config.parent = self

    def find_rule(self, target:str) -> Rule|None:
        '''
            Search by target path
        '''
        for rule in self.rules:
            if rule.target.endswith(target):
                return rule
        return None

    def recursive_run(self, start_node, function, children_container_name, stop_criteria = None):
        '''
            Deep first multithreaded recursive function run
            Any type of nodes support

            start_node : Rule | Project | ... - node as root of tree
            function : function(node : Rule | Project | ... ) - function will be executed for all nodes
            children_container_name : str - name of class member contains children nodes
            stop_criteria : function(return_value:Any) -> bool - if true, stops tree walking
        '''
        cc = os.cpu_count()
        threads_num = cc if CONFIG.MAX_THREADS_NUM > cc else CONFIG.MAX_THREADS_NUM

        visited = set()
        stack = []
        mutex_stack = threading.Lock()
        mutex_visited = threading.Lock()

        def process_node(_node : Rule):
            with mutex_visited:
                if _node in visited:
                    return
                visited.add(_node)

            children = getattr(_node, children_container_name)
            if children:
                with mutex_stack:
                    if _node in stack:
                        raise Exceptions.CircularDetected(_node)
                    stack.append(_node)

                process_subtree(_node)

                with mutex_stack:
                    stack.remove(_node)

            return function(_node)

        def process_subtree(_node):
            with concurrent.futures.ThreadPoolExecutor(max_workers=threads_num) as executor:
                children = getattr(_node, children_container_name)
                futures = [executor.submit(process_node, child) for child in children]
                for future in concurrent.futures.as_completed(futures):
                    if stop_criteria:
                        if stop_criteria(future.result()):
                            for f in futures:
                                f.cancel()
                            break

        process_node(start_node)

    def rule_recursive_run(self, rule : Rule, function, stop_criteria = None):
        return self.recursive_run(rule, function, 'prerequisites', stop_criteria)

    def project_recursive_run(self, function, stop_criteria = None):
        return self.recursive_run(self, function, 'subprojects', stop_criteria)

    def build(self, rule : Rule) -> int:
        bulilded_rules = []

        def _exec_rule(_rule : Rule) -> int:
            if _rule.exec:
                compile_command : CompileCommand = _rule.exec(_rule)
                if compile_command:
                    if compile_command._name:
                        logger.info(f"{compile_command._name}: {os.path.relpath(compile_command.output)}")

                    if compile_command.arguments:
                        return utils.sh(compile_command.arguments,cwd=compile_command.directory).returncode
                    elif compile_command.command:
                        return utils.sh(compile_command.command,cwd=compile_command.directory).returncode
                    else:
                        return 0
            return 0

        mutex_hash = threading.Lock()

        def _build(_rule : Rule) -> int:

            if _rule.phony:
                return _exec_rule(_rule)

            # Hash source names calculation
            hash_sum = 0
            for prq in _rule.prerequisites:
                hash_sum = utils.stable_hash(prq.target)
            hash_sum + utils.stable_hash(_rule.target)

            with mutex_hash:
                _rule.parent.source_names_hash += hash_sum

            if not os.path.isabs(_rule.target):
                _rule.target = f'{_rule.parent.private_config.CWD}/{_rule.target}'

            # Target doesn't exists
            if not os.path.exists(_rule.target):
                return _exec_rule(_rule)

            # Prerequisite is newer
            out_date = os.path.getmtime(_rule.target)
            for prq in _rule.prerequisites:
                if not os.path.isabs(prq.target):
                    prq.target = f'{prq.parent.private_config.CWD}/{prq.target}'

                if not os.path.exists(prq.target):
                    raise Exceptions.PrerequisiteNotFound(f': {os.path.relpath(prq.target,prq.parent.private_config.CWD)}')
                src_date = os.path.getmtime(prq.target)
                if src_date > out_date:
                    bulilded_rules.append(_rule)
                    if _rule.exec:
                        return _exec_rule(_rule)
                    else:
                        # Not buildable targets cannot be updated naturally
                        # so update them artificially to avoid endless rebuilds
                        os.utime(_rule.target)

            return 0

        code = 0
        def _stop_criteria(value) -> bool:
            nonlocal code
            if value != 0:
                code = value
                return True
            return False

        try:
            self.rule_recursive_run(rule, _build, _stop_criteria)
            if code != 0:
                logger.error('Error has occurred')
            else:
                if bulilded_rules:
                    logger.info(utils.color_text(32,'Done'))
                else:
                    logger.info('Nothing to build')
        except Exception as e:
            logger.error(f'{e}')

        return code

    def get_compile_commands(self) -> list[dict]:
        result = []

        mutex = threading.Lock()

        def _compile_commands(_rule : Rule):
            if _rule.phony:
                return

            if _rule.exec:
                compile_command : CompileCommand = _rule.exec(_rule)
                if compile_command:
                    if compile_command.command or compile_command.arguments:
                        with mutex:
                            result.append(compile_command.get_dict())

        self.rule_recursive_run(self.main_rule, _compile_commands)
        return result

#----------------------END PROJECT---------------------

def process(get_project_fnc, get_config_fnc=None):
    global CONFIG
    global console_handler

    if get_config_fnc:
        CONFIG = get_config_fnc()

    console_handler.setLevel(CONFIG.VERBOSITY)

    if CONFIG.MINIMUM_REQUIRED_VERSION > VERSION:
        logger.warning(f"Required version {CONFIG.MINIMUM_REQUIRED_VERSION} is higher than running {VERSION}!")

    project_name = 'main'
    target = 'build'

    match len(sys.argv):
        case 1:pass
        case 2:
            target = sys.argv[1]
        case 3|_:
            project_name = sys.argv[1]
            target = sys.argv[2]

    try:
        project : ProjectBase = get_project_fnc(project_name)
        rule = project.find_rule(target)
        if not rule:
            raise Exceptions.RuleNotFound(target)
        code = project.build(rule)
        exit(code)
    except Exception as e:
        logger.error(traceback.format_exc())
        exit(1)
