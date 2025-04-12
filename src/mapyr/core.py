import sys
import os
import concurrent.futures
import traceback
import copy
import mapyr.utils as utils
from mapyr.exceptions import Exceptions
from mapyr.logger import logger,console_handler

VERSION = '0.8.7'

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
            Execution function
        '''

        self.phony : bool = phony
        '''
            Phony target not expects output file, and will be executed every time when called
        '''

        self.parent : ProjectBase = parent
        '''
            Parent project
        '''

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

    def recursive_run(self, start_node, function, children_container_name) -> int:
        '''
            Deep first multithreaded recursive function run
            Any type of nodes support

            start_node : Rule | Project | ... - node as root of tree
            function : function(node : Rule | Project | ... ) - function will be executed for all nodes
            children_container_name : str - name of class member contains children nodes

            return : int - exitcode
        '''
        cc = os.cpu_count()
        threads_num = cc if CONFIG.MAX_THREADS_NUM > cc else CONFIG.MAX_THREADS_NUM

        visited = []
        stack = []

        def process_node(_node : Rule):
            if _node in stack:
                raise Exceptions.CircularDetected(_node)

            if _node in visited:
                return 0

            stack.append(_node)

            result = 0
            children = getattr(_node, children_container_name)
            if children:
                result = process_subtree(_node)

            result = max(result, function(_node))
            visited.append(_node)
            stack.pop()
            return result

        def process_subtree(_node):
            with concurrent.futures.ThreadPoolExecutor(max_workers=threads_num) as executor:
                children = getattr(_node, children_container_name)
                futures = [executor.submit(process_node, child) for child in children]
                max_return_code = 0
                for future in concurrent.futures.as_completed(futures):
                    return_code = future.result()
                    max_return_code = max(max_return_code, return_code)
                    if max_return_code != 0:
                        for f in futures:
                            f.cancel()
                        break
                return max_return_code

        return process_node(start_node)

    def rule_recursive_run(self, rule : Rule, function):
        return self.recursive_run(rule, function, 'prerequisites')

    def project_recursive_run(self, function):
        return self.recursive_run(self, function, 'subprojects')

    def build(self, rule : Rule):
        bulilded_rules = []
        def _build(_rule : Rule):

            if _rule.phony:
                if _rule.exec:
                    return _rule.exec(_rule)
                else:
                    return 0

            if not _rule.exec:
                return 0

            if not os.path.isabs(_rule.target):
                _rule.target = f'{_rule.parent.private_config.CWD}/{_rule.target}'

            # Target doesn't exists
            if not os.path.exists(_rule.target):
                bulilded_rules.append(_rule)
                return _rule.exec(_rule)

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
                    return _rule.exec(_rule)

            return 0
        try:
            self.rule_recursive_run(rule, _build)
            if bulilded_rules:
                logger.info(utils.color_text(32,'Done'))
            else:
                logger.info('Nothing to build')
        except Exception as e:
            logger.error(f'{e}')

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
        project.build(rule)
    except Exception as e:
        logger.error(traceback.format_exc())
