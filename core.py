import sys
import os
import shutil
import subprocess
import concurrent.futures
import importlib.util
import inspect

from .logger import app_logger,console_handler,color_text

VERSION = '0.7.0'

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

#---------------------------CONFIG---------------------

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

def silentremove(filename):
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

def extend_config(dst:dict[str,]|None, src:dict[str,]|None) -> None:
    '''
        Extend config from other config values
    '''
    if type(dst) is not dict or type(src) is not dict:
        raise RuntimeError('Config type is not dictionary. Maybe forgot __dict__?')

    if src is None:
        return
    if dst is None:
        dst = src

    for key in src.keys():
        if key not in dst:
            dst[key] = src[key]
            continue

        if src[key] is dst[key]:
            continue

        if type(src[key]) != type(dst[key]):
            continue

        if type(dst[key]) is list:
            dst[key].extend(src[key])
            dst[key] = unify_list(dst[key])

#----------------------END UTILS-----------------------

#---------------------------RULE-----------------------

class Rule:
    def __init__(
            self,
            target              : str,
            prerequisites       : list[str]         = [],
            exec                : 'function'        = None,
            phony               : bool              = False,
            config              : dict              = dict(),
            downstream_config   : dict              = dict(),
            upstream_config     : dict              = dict(),
            before_build        : list['function']  = [],
            cwd                 : str               = None
        ) -> None:

        self.cwd : str = cwd if cwd else caller_cwd()
        '''
            Directory, where rule was created
        '''

        self.target : str = target if os.path.isabs(target) else os.path.join(self.cwd,target)
        '''
            Output file or phony name
        '''

        self.prerequisites : list[str] = [ x if os.path.isabs(x) else os.path.join(self.cwd,x) for x in prerequisites ]
        '''
            All targets needed be done before this rule
        '''

        self.exec : function = exec
        '''
            Execution function
        '''

        self.phony : bool = phony
        '''
            Phony target not expects output file, and will be executed every time when called
        '''

        self.config : dict = config
        '''
            Config only for this rule
        '''

        self.downstream_config : dict = downstream_config
        '''
            Config for this rule and children
        '''

        self.upstream_config : dict = upstream_config
        '''
            Config for this rule and parents
        '''

        self.before_build = before_build
        '''
            List of functions that will be executed after config exchanging
                and before setting build_layer.
            As exemple: can be used for checking validity build config
                of exists output files.
        '''

        self._build_layer :int = 0
        '''
            On what step of building process this rule will be
            0 - means "do not build"
            This member fills by set_build_layers function
        '''

    def __str__(self) -> str:
        return f'{os.path.relpath(self.target,self.cwd)}:{[os.path.relpath(x,self.cwd) for x in self.prerequisites]}'

    def __repr__(self) -> str:
        return self.__str__()


RULES : list[Rule] = []

def find_rule(path:str, rules : list[Rule] = None) -> Rule|None:
    '''
        Search by target path
    '''
    rules = RULES if rules is None else rules
    for rule in rules:
        if rule.target.endswith(path):
            return rule
    return None

def recursive_run(target:str, function):
    '''
        Depth-first recursion
        function(target:str, rule:Rule, parent_rule:Rule) -> bool
        function return true if need stop
    '''
    stack : list[Rule] = []

    def _run(_target:str, parent_rule:Rule = None):
        rule = find_rule(_target)

        if not rule:
            raise Exceptions.RuleNotFound(_target)

        if rule in stack:
            raise Exceptions.CircularDetected()

        stack.append(rule)
        for prq in rule.prerequisites:
            if _run(prq, rule) == True:
                return True

        if function(rule, parent_rule) == True:
            return True

        stack.pop()

    _run(target)

def exchange_configs(target:str) -> bool:
    '''
        Do config exchage.
        This function expect this is root rule, so all work will be among children

        Root             ChildRoot        GrandChildRoot
        Downstream ↧→→→→ Downstream ↧→→→→ Downstream ↧→→→→ ...
                   ↓                ↓                ↓
            Config←↤         Config←↤         Config←↤     ...
                   ↑                ↑                ↑
          Upstream ←←↥←←←←←Upstream ←←↥←←←← Upstream ←←↥←← ...
    '''

    def _exchange_configs(rule:Rule, parent_rule:Rule) -> bool:
        if parent_rule is None:
            return False

        # Config parent -> child
        extend_config(rule.downstream_config, parent_rule.downstream_config)

        # Config parent -> child private
        extend_config(rule.config, parent_rule.downstream_config)

        # Config parent private <- child export
        extend_config(parent_rule.config, rule.upstream_config)

        # Config parent <- child export
        extend_config(parent_rule.upstream_config, rule.upstream_config)

        # Self export -> private
        extend_config(rule.config, rule.upstream_config)
        return False

    recursive_run(target,_exchange_configs)

def set_build_layers(target:str) -> int:
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
            if not os.path.exists(prq):
                break
            out_date = os.path.getmtime(rule.target)
            src_date = os.path.getmtime(prq)
            if src_date > out_date:
                return _will_build(rule,parent_rule)
        return False

    recursive_run(target,_set_build_layers)
    return max(build_layers.values())

#
# TODO: if error somewhere in middle of the branch then we can not keep building parents
#       but we can still build parents for other branches. Now we break if error on the layer
#
def build(target):
    exchange_configs(target)

    # Before build functions runing
    for rule in [x for x in RULES if x.before_build]:
        for func in rule.before_build:
            func(rule)

    layers_num = set_build_layers(target)

    cc = os.cpu_count()
    threads_num = cc if CONFIG.MAX_THREADS_NUM > cc else CONFIG.MAX_THREADS_NUM
    error : bool = False
    any_builds = False
    for layer_num in range(1,layers_num+1):

        layer : list[Rule] = [x for x in RULES if x._build_layer == layer_num]
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

def help():
    cwd = caller_cwd()
    print('\n'.join([ os.path.relpath(x.target,cwd) for x in RULES if x.phony ]))
#---------------------------END RULE-------------------

def process(get_rules_fnc, get_config_fnc=None):
    global RULES
    global CONFIG
    global console_handler

    if get_config_fnc:
        CONFIG = get_config_fnc()

    console_handler.setLevel(CONFIG.VERBOSITY)

    if CONFIG.MINIMUM_REQUIRED_VERSION > VERSION:
        app_logger.warning(f"Required version {CONFIG.MINIMUM_REQUIRED_VERSION} is higher than running {VERSION}!")

    if len(sys.argv) < 2:
        sys.argv.append('build')

    try:
        RULES = get_rules_fnc()

        if 'help' in sys.argv:
            help()
            exit()

        # Unify rules
        been : dict[str,Rule] = dict()
        for rule in RULES:
            if been.setdefault(rule.target,rule) is not rule:
                been[rule.target].extend(rule)
        RULES = list(been.values())

        for i in range(1,len(sys.argv)):
            sys.argv[i] = sys.argv[i] if os.path.isabs(sys.argv[i]) else os.path.join(caller_cwd(),sys.argv[i])
            build(sys.argv[i])

    except Exception as e:
        app_logger.error(e)
