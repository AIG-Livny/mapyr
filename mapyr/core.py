import sys
import os
import shutil
import subprocess
import concurrent.futures
import importlib.util
import inspect
import traceback
import copy

from .logger import app_logger,console_handler,color_text

VERSION = '0.8.0'

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

#----------------------EXCEPTIONS----------------------

class Exceptions:
    class CustomException(Exception):
        def __init__(self, add=None): super().__init__(f'{self.__doc__}{f" {add}" if add else ""}')
    class CircularDetected(CustomException):
        "Circular dependency detected!"
    class RuleNotFound(CustomException):
        "Rule not found for:"
    class PrerequisiteNotFound(CustomException):
        "Prerequisite not found!"
    class SameRulesInTreeDetected(CustomException):
        "Same rules in rule tree detected"
    class AtLeastOneConfig(CustomException):
        "At least one config must be present"

#----------------------END EXCEPTIONS------------------

#----------------------UTILS---------------------------

def find_files(dirs:list[str], exts:list[str], recursive=False, cwd = None) -> list[str]:
    '''
        Search files with extensions listed in `exts`
        in directories listed in `dirs`
    '''
    result = []
    if cwd is None:
        cwd = caller_cwd()
    def _check(dir, files):
        for file in files:
            filepath = f'{dir}/{file}'
            if os.path.isfile(filepath):
                if os.path.splitext(file)[1] in exts:
                    result.append(os.path.abspath(filepath))

    for dir in dirs:
        if not os.path.isabs(dir):
            dir = os.path.join(cwd,dir)
        if not os.path.exists(dir):
            continue

        if recursive:
            for root, subdirs, files in os.walk(dir):
                _check(root, files)
        else:
            _check(dir,os.listdir(dir))

    return result

def sh(cmd:list[str] | str, output_capture : bool = False) -> subprocess.CompletedProcess:
    '''
        Run command in shell
    '''
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE if output_capture else None,
        stderr=subprocess.PIPE if output_capture else None,
        encoding='utf-8',
        shell=False if type(cmd) is list else True
    )
    app_logger.debug(f'{result}')
    return result

def silentremove(filename:str):
    '''
        Remove file/directory or ignore error if not found
    '''
    try:
        os.remove(filename)
    except FileNotFoundError:
        pass
    except IsADirectoryError:
        shutil.rmtree(filename,ignore_errors=True)

def get_size(path:str) -> int:
    '''
        Get file size in bytes
    '''
    if os.path.exists(path):
        return os.stat(path).st_size
    return -1

def diff(old:int, new:int) -> str:
    '''
        Get difference btw two numbers in string format with color and sign
    '''
    diff = new - old
    summstr = '0'
    if diff > 0:
        summstr = color_text(31,f'+{diff}')
    if diff < 0:
        summstr = color_text(32,f'{diff}')
    return summstr

def unify_list(l:list):
    '''
        Make list elements unique
    '''
    result = []
    for v in l:
        if v not in result:
            result.append(v)
    return result

def get_module(path:str):
    '''
        Load module by path
    '''
    if not os.path.isabs(path):
        path = os.path.join(caller_cwd(),path)
    spec = importlib.util.spec_from_file_location("mapyr_buildpy", path)

    if spec is None:
        raise ModuleNotFoundError(path)
    foo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(foo)
    return foo

def caller_cwd() -> str:
    '''
        Path to caller script directory
    '''
    for frame in inspect.stack():
        path = frame[1]
        if not path.startswith(os.path.dirname(__file__)):
            return os.path.dirname(os.path.abspath(path))
    raise RuntimeError('frame not found')

#----------------------END UTILS-----------------------

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

        self._build_layer :int = 0
        '''
            On what step of building process this rule will be
            0 - means "do not build"
            This member fills by set_build_layers function
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
        self.CWD = caller_cwd()
        '''
            By default: path where config was created
        '''
        self.parent : ProjectBase = None

    def extend(self,other:'ConfigBase'):
        '''
            Must be implemented in children
        '''
        raise NotImplementedError()

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

    def rule_recursive_run(self, start_rule:Rule, function):
        '''
            Depth-first recursion for rules
            function(rule:Rule, parent_rule:Rule) -> bool
            function return true if need stop
        '''

        stack : list[Rule] = []

        def _run(rule:Rule, parent_rule:Rule = None):
            if not rule:
                return

            if rule in stack:
               raise Exceptions.CircularDetected(rule.target)

            stack.append(rule)
            for prq_rule in rule.prerequisites:
               if _run(prq_rule, rule) == True:
                   return True

            if function(rule, parent_rule) == True:
               return True

            stack.pop()

        _run(start_rule)

    def project_recursive_run(self, function):
        '''
            Depth-first recursion for projects
            function(project:ProjectBase, parent_project:ProjectBase) -> bool
            function return true if need stop
        '''

        stack : list[ProjectBase] = []

        def _run(project:ProjectBase, parent_project:ProjectBase = None):
            if not project:
                return

            if project in stack:
               raise Exceptions.CircularDetected()

            stack.append(project)
            for sp in project.subprojects:
               if _run(sp, project) == True:
                   return True

            if function(project, parent_project) == True:
               return True

            stack.pop()

        _run(self)

    def set_build_layers(self, start_rule:Rule) -> int:
        build_layers : dict[Rule,int] = dict()

        def _will_build(rule:Rule, parent_rule:Rule) -> bool:
            if build_layers[rule] == 0:
                build_layers[rule] = 1

            # If we will build then parent must built too
            if parent_rule:
                if build_layers.setdefault(parent_rule, build_layers[rule] + 1) <= build_layers[rule]:
                    build_layers[parent_rule] = build_layers[rule] + 1
                parent_rule._build_layer = build_layers[parent_rule]
            rule._build_layer = build_layers[rule]
            return False

        def _set_build_layers(rule:Rule, parent_rule:Rule) -> bool:
            build_layers.setdefault(rule,rule._build_layer)
            if build_layers[rule] > 0:
                return _will_build(rule,parent_rule)

            if rule.phony:
                return _will_build(rule,parent_rule)

            # Rule-file skip
            if not rule.prerequisites:
                return False

            # Target doesn't exists
            if not os.path.exists(rule.target):
                return _will_build(rule,parent_rule)

            for prq in rule.prerequisites:
                # Prerequisite not builded yet
                # He will set our build level as parent rule
                if not os.path.exists(prq.target):
                    break
                out_date = os.path.getmtime(rule.target)
                src_date = os.path.getmtime(prq.target)
                if src_date > out_date:
                    return _will_build(rule,parent_rule)
            return False

        self.rule_recursive_run(start_rule,_set_build_layers)
        return max(build_layers.values())

    def get_rules_layer(self, layer_num:int, start_rule:Rule) -> list[Rule]:
        result = []
        def _run(rule:Rule, parent_rule:Rule):
            if rule._build_layer == layer_num:
                result.append(rule)
        self.rule_recursive_run(start_rule, _run)

        return result

    #
    # TODO: if error somewhere in middle of the branch then we can not keep building parents
    #       but we can still build parents for other branches. Now we break if error on the layer
    #
    def build(self, _rule:Rule):
        layers_num = self.set_build_layers(_rule)

        cc = os.cpu_count()
        threads_num = cc if CONFIG.MAX_THREADS_NUM > cc else CONFIG.MAX_THREADS_NUM
        error : bool = False
        any_builds = False
        for layer_num in range(1,layers_num+1):

            layer : list[Rule] = self.get_rules_layer(layer_num, _rule)
            for rule in layer:
                # Not buildable targets (simple file) will never be updated
                # So we "update" them artifically to avoid endless rebuilds
                if rule.prerequisites and not rule.exec and not rule.phony:
                    os.utime(rule.target)

            layer_exec : list[Rule] = [x for x in layer if x.exec]

            if not layer_exec:
                continue

            any_builds = True
            problem_rule : Rule = None

            with concurrent.futures.ProcessPoolExecutor(max_workers=threads_num) as executor:
                builders = [executor.submit(x.exec,x) for x in layer_exec]
                for i in range(len(builders)):
                    if builders[i].result() != 0:
                        error = True
                        problem_rule=layer_exec[i]
                        break
                if error:
                    break
        if error:
            app_logger.error(f'{os.path.relpath(problem_rule.target, caller_cwd()) }: Error. Stopped.')
            return False

        if not any_builds:
            app_logger.info('Nothing to build')
            return True

        app_logger.info(color_text(32,'Done'))
        return True

#----------------------END PROJECT---------------------

def process(get_project_fnc, get_config_fnc=None):
    global CONFIG
    global console_handler

    if get_config_fnc:
        CONFIG = get_config_fnc()

    console_handler.setLevel(CONFIG.VERBOSITY)

    if CONFIG.MINIMUM_REQUIRED_VERSION > VERSION:
        app_logger.warning(f"Required version {CONFIG.MINIMUM_REQUIRED_VERSION} is higher than running {VERSION}!")

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
        app_logger.error(traceback.format_exc())
