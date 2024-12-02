import sys
import os
import shutil
import subprocess
import concurrent.futures
import logging
import json
import importlib.util
import inspect
import re

VERSION = '0.6.0'

#----------------------LOGGING-------------------------

app_logger : logging.Logger = None

class ConsoleFormatter(logging.Formatter):
    def __init__(self):
        super().__init__('[%(levelname)s]: %(message)s')

    def format(self, record: logging.LogRecord) -> str:
        if record.levelno >= logging.ERROR:
            record.msg = color_text(91,record.message)
        if record.levelno == logging.WARNING:
            record.msg = color_text(31,record.message)
        return super().format(record)

def setup_logger(config: 'Config'):
    global app_logger
    file_formatter = logging.Formatter('%(asctime)-15s|PID:%(process)-11s|%(levelname)-8s|%(filename)s:%(lineno)s| %(message)s')

    file_path = f"{os.path.dirname(os.path.realpath(__file__))}/debug.log"
    file_handler = logging.FileHandler(file_path,'w',encoding='utf8')
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(config.VERBOSITY)
    console_handler.setFormatter(ConsoleFormatter())

    rootlog = logging.getLogger()
    rootlog.addHandler(file_handler)

    app_logger = logging.getLogger('main')
    app_logger.propagate = False
    app_logger.setLevel(logging.DEBUG)
    app_logger.addHandler(file_handler)
    app_logger.addHandler(console_handler)

#----------------------LOGGING-------------------------

#----------------------CONFIG--------------------------

class Config:
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

config : Config = Config()

#---------------------------CONFIG---------------------

#----------------------EXCEPTIONS----------------------

class Exceptions:
    class CustomException(Exception):
        def __init__(self, add=None): super().__init__(f'{self.__doc__}{f" {add}" if add else ""}')
    class CircularDetected(CustomException):
        "Circular dependency detected!"
    class ProjectNotFound(CustomException):
        "Project not found"
    class RuleNotFound(CustomException):
        "Rule not found for:"
    class NotImplemented(CustomException):
        "Not implemented"
    class SameProjectDifferentConfig(CustomException):
        "Same project but with different config detected in subprojects:"

#----------------------END EXCEPTIONS------------------

#----------------------UTILS---------------------------
# Color text Win/Lin
if os.name == 'nt':
    def color_text(color,text):
        return f"[{color}m{text}[0m"
else:
    def color_text(color, text):
        return f"\033[{color}m{text}\033[0m"

def find_files(dirs:list[str], exts:list[str], recursive=False) -> list[str]:
    '''
        Search files with extensions listed in `exts`
        in directories listed in `dirs`
    '''
    result = []

    def _check(dir, files):
        for file in files:
            filepath = f'{dir}/{file}'
            if os.path.isfile(filepath):
                if os.path.splitext(file)[1] in exts:
                    result.append(os.path.abspath(filepath))

    for dir in dirs:
        if not os.path.exists(dir):
            continue

        if recursive:
            for root, subdirs, files in os.walk(dir):
                _check(root, files)
        else:
            _check(dir,os.listdir(dir))

    return result

def sh(cmd:list[str] | str) -> int:
    '''
        Run shell command and ignore answer, but code
    '''
    app_logger.debug(cmd)
    if type(cmd) == list:
        result = subprocess.run(cmd)
    else:
        result = subprocess.run(cmd,shell=True)
    return result.returncode

def sh_capture(cmd:list[str] | str) -> str:
    '''
        Run shell command and get stdin or stderr
    '''
    if type(cmd) == list:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
    else:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, encoding='utf-8')
    if len(result.stderr) > 0:
        return result.stderr
    return result.stdout

def silentremove(filename):
    '''
        Remove file or ignore error if not found
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

def unique_list(l:list):
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
        Load module by relative path
    '''
    orig_cwd = os.getcwd()
    os.chdir(caller_cwd())
    spec = importlib.util.spec_from_file_location("mapyr_buildpy", path)
    os.chdir(orig_cwd)

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
        if path != __file__:
            return os.path.dirname(os.path.abspath(path))
    raise RuntimeError('frame not found')

def extend_config(dst:dict[str,],src:dict[str,]):
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
            dst[key] = unique_list(dst[key])

def abspath_project(prj:'Project', path) -> str:
    '''
        Return absolute path relative project and not CWD
        It made to keep CWD as is
    '''
    return path if os.path.isabs(path) else os.path.abspath(f'{prj.CWD}/{path}')

def relpath_project(prj:'Project', path) -> str:
    return os.path.relpath(path,prj.CWD)

def make_cpp_properties(p:'Project',cfg:'CConfig'):
    vscode_file_path = f'{p.CWD}/.vscode/c_cpp_properties.json'
    if os.path.exists(vscode_file_path):
        import inspect
        build_py_filename = inspect.stack()[2].filename
        if os.path.getmtime(build_py_filename) <= os.path.getmtime(vscode_file_path):
            return

    config = {
        'name':p.TARGET,
        'includePath':cfg.INCLUDE_DIRS,
        'defines':cfg.DEFINES
    }

    main_config = {
        'configurations':[config],
        "version": 4
    }

    with open(vscode_file_path, 'w+') as f:
        json.dump(main_config, f, indent=4)

def gen_vscode_config():
    if os.path.exists('.vscode'):
        app_logger.error('directory .vscode already exists')
        exit()
    os.makedirs('.vscode')
    extensions = {"recommendations": ["augustocdias.tasks-shell-input"]}
    launch = {"version":"0.2.0","configurations":[{"name":"app","type":"cppdbg","request":"launch","program":"${workspaceFolder}/${input:GetName}","args":[],"stopAtEntry":False,"cwd":"${workspaceFolder}","environment":[],"externalConsole":False,"MIMode":"gdb","preLaunchTask":"build","setupCommands":[{"text":"-enable-pretty-printing","ignoreFailures":True},{"text":"-gdb-set disassembly-flavor intel","ignoreFailures":True}]},{"name":"mapyr","type":"debugpy","request":"launch","program":"build.py","console":"integratedTerminal"}],"inputs":[{"id":"GetName","type":"command","command":"shellCommand.execute","args":{"command":"./build.py outfile main","useFirstResult":True}}]}
    tasks = {"version":"2.0.0","tasks":[{"label":"build","type":"shell","command":"./build.py","group":{"isDefault":True,"kind":"build"},"presentation":{"clear":True}},{"label":"run","type":"shell","command":"./build.py run"},{"label":"clean","type":"shell","command":"./build.py clean","presentation":{"reveal":"never"}}]}
    with open('.vscode/extensions.json','w+') as fext, open('.vscode/launch.json','w+') as flaunch, open('.vscode/tasks.json','w+') as ftasks:
        json.dump(extensions, fext, indent=4)
        json.dump(launch, flaunch, indent=4)
        json.dump(tasks, ftasks, indent=4)

#----------------------END UTILS-----------------------

#---------------------------RULE-----------------------

class Regex:
    def __init__(self, regex:str) -> None:
        self.regex = regex

    def __str__(self) -> str:
        return self.regex

    def __repr__(self) -> str:
        return self.regex

class Rule:
    def __init__(self, parent:'Project', targets:str|Regex|list[str|Regex], prerequisites:str|list['str'] = [], phony=True) -> None:
        self.targets : list[str|Regex] = [targets] if type(targets) in [str,Regex] else list(targets)
        self.prerequisites : list[str] = [prerequisites] if type(prerequisites) is str else list(prerequisites)

        self.phony = phony
        self.parent : Project = parent
        self.build_layer :int = 0
        self.target_build_list : list[str] = []

    '''
    def execute(self, target:str) -> int:
    '''

    def __repr__(self) -> str:
        return f'{self.targets}:{self.prerequisites}'

#---------------------------END RULE-------------------

#---------------------------PROJECT--------------------

class Project:
    def __init__(self,name:str, target_path:str) -> None:
        self.CWD : str = caller_cwd()
        self.NAME = name
        self.TARGET : str = target_path if os.path.isabs(target_path) else f'{self.CWD}/{target_path}'

        '''
            A start path of project.
            By default - directory of caller script
        '''

        self.PRIVATE_CONFIG : dict[str,] = dict()
        self.CONFIG : dict[str,] = dict()
        self.EXPORT_CONFIG : dict[str,] = dict()

        self.RULES : list[Rule] = [RuleBuild(self),RulePrintTarget(self)]
        '''
        '''

        self.SUBPROJECTS : list[Project] = []
        self.ALL_RULES : list [Rule] = []
        self.BEFORE_RUN_BUILD_CALLBACK = None


    def get_rule(self, project:'Project', name:str, exclude_rule:Rule = None) -> Rule|None:
        rules = self.ALL_RULES if self.ALL_RULES else self.RULES

        # First, looking for exact match
        for rule in rules:
            if rule is exclude_rule:
                continue

            for target in rule.targets:
                if target == name:
                    return rule

        # Second, looking for regex rules
        for rule in rules:
            if rule is exclude_rule:
                continue
            for target in rule.targets:
                # Regex match only for owner project
                if project != rule.parent:
                    continue

                if type(target) is not Regex:
                    continue

                if re.match(target.regex, name):
                    return rule
        return None

    def build(self, target_path:str = None) -> bool:
        global config

        if target_path is None:
            target_path = self.TARGET

        projects_loaded : list[Project] = []
        projects_trace : list[Project] = []
        def _load_subprojects(p:Project):
            if p in projects_trace:
                raise Exceptions.CircularDetected()

            projects_trace.append(p)

            p.ALL_RULES.extend(p.RULES)

            for sp in p.SUBPROJECTS:
                for pl in projects_loaded:
                    if pl.TARGET == sp.TARGET:
                        if sp.NAME != pl.NAME:
                            raise Exceptions.SameProjectDifferentConfig(f'{sp.TARGET} and {pl.TARGET}. Projects trace: {projects_trace}')

                        # We found same project but from another branch of tree
                        # It can has a different config
                        extend_config(pl.PRIVATE_CONFIG, sp.PRIVATE_CONFIG)
                        continue

                _load_subprojects(sp)

                p.ALL_RULES.extend(sp.ALL_RULES)

                # Config master -> slave
                extend_config(sp.CONFIG, p.CONFIG)

                # Config master -> slave private
                extend_config(sp.PRIVATE_CONFIG, p.CONFIG)

                # Config master private <- slave export
                extend_config(p.PRIVATE_CONFIG, sp.EXPORT_CONFIG)

                # Config master <- slave export
                extend_config(p.EXPORT_CONFIG, sp.EXPORT_CONFIG)

            # Summary config
            extend_config(p.PRIVATE_CONFIG, p.EXPORT_CONFIG)
            projects_loaded.append(p)
            projects_trace.pop()

        _load_subprojects(self)

        if self.BEFORE_RUN_BUILD_CALLBACK:
            self.BEFORE_RUN_BUILD_CALLBACK(self)

        rules_in = []
        def _get_build_layer(p:Project, _target:str) -> int:
            rule = self.get_rule(p, _target, rules_in[-1] if rules_in else None)

            if not rule:
                raise Exceptions.RuleNotFound(_target)

            if not rule.prerequisites:
                return 0

            if rule in rules_in:
                raise Exceptions.CircularDetected()
            rules_in.append(rule)

            max_child_build_layer = 0
            need_build = False
            for prq in rule.prerequisites:
                prq_layer = _get_build_layer(rule.parent, prq)
                if prq_layer > max_child_build_layer:
                    max_child_build_layer = prq_layer

                # If children will builds then we will build too
                if max_child_build_layer:
                    need_build = True
                    continue

                if rule.phony:
                    continue

                if not os.path.exists(_target):
                    need_build = True
                    continue

                out_date = os.path.getmtime(_target)
                src_date = os.path.getmtime(prq)
                if src_date > out_date:
                    need_build = True

            if need_build:
                rule.build_layer = max_child_build_layer + 1
                if _target not in rule.target_build_list:
                    rule.target_build_list.append(_target)

            rules_in.pop()
            return rule.build_layer

        layers_num = _get_build_layer(self, target_path)

        if layers_num == 0:
            app_logger.info('Nothing to build')
            return True

        cc = os.cpu_count()
        threads_num = cc if config.MAX_THREADS_NUM > cc else config.MAX_THREADS_NUM
        error : bool = False
        for layer_num in range(1,layers_num+1):
            layer : list[Rule] = [x for x in self.ALL_RULES if x.build_layer == layer_num]

            problem_rule : Rule = None

            with concurrent.futures.ProcessPoolExecutor(max_workers=threads_num) as executor:
                builders = []
                for rule in layer:
                    if getattr(rule, "execute", None):
                        for target in rule.target_build_list:
                            builders.append(executor.submit(rule.execute, target))

                for i in range(len(builders)):
                    if builders[i].result() != 0:
                        error = True
                        problem_rule=layer[i]
                        break
                if error:
                    break
        if error:
            app_logger.error(f'{problem_rule.targets[0]}: Error. Stopped.')
            return False

        app_logger.info(color_text(32,'Done'))
        return True

    def __repr__(self) -> str:
        return f'{self.NAME}:{self.TARGET}'

#----------------------END PROJECT---------------------

#----------------------COMMON--------------------------

class RuleBuild(Rule):
    def __init__(self, parent: Project) -> None:
        super().__init__(parent, 'build', parent.TARGET, phony=True)

    def execute(self, target: str) -> int:
        self.parent.build()

class RulePrintTarget(Rule):
    def __init__(self, parent: Project) -> None:
        super().__init__(parent, 'target', parent.TARGET, phony=True)

    def execute(self, target: str) -> int:
        print(self.parent.TARGET)

#----------------------END COMMON----------------------

#----------------------C-------------------------------

class RuleGenerateVSCODE(Rule):
    def __init__(self, parent: Project) -> None:
        super().__init__(parent, 'gcvscode', parent.TARGET, phony=True)

    def execute(self, target: str) -> int:
        gen_vscode_config()

class RuleO(Rule):
    def execute(self, target:str) -> int:
        app_logger.info(f"{color_text(94,'Building')}: {os.path.relpath(self.prerequisites[0])}")

        if not os.path.exists(target):
            os.makedirs(os.path.dirname(target),exist_ok=True)

        cfg = CConfig(self.parent.PRIVATE_CONFIG)

        self.cmd = \
            [cfg.COMPILER,'-MT','','-MMD','-MP','-MF',''] \
            + cfg.CFLAGS \
            + [f"-D{x}" for x in cfg.DEFINES] \
            + [f"-I{x}" for x in cfg.INCLUDE_DIRS] \
            + ['-c','-o','','']

        path_wo_ext     = os.path.splitext(target)[0]
        self.cmd[2]     = self.prerequisites[0]
        self.cmd[6]     = f"{path_wo_ext}.d"
        self.cmd[-2]    = target
        self.cmd[-1]    = self.prerequisites[0]
        # mapyr special flags
        self.cmd.insert(7, f'-D__MAPYR__FILENAME__="{os.path.basename(self.prerequisites[0])}"')
        return sh(self.cmd)

class RuleExe(Rule):
    def execute(self, target:str) -> int:
        app_logger.info(f"{color_text(32,'Linking executable')}: {os.path.relpath(target)}")

        if not os.path.exists(target):
            os.makedirs(os.path.dirname(target),exist_ok=True)

        cfg = CConfig(self.parent.PRIVATE_CONFIG)

        self.cmd = [cfg.COMPILER] \
        + cfg.LINK_FLAGS \
        + [f"-L{x}" for x in cfg.LIB_DIRS] \
        + self.prerequisites \
        + ['-o',self.parent.TARGET] \
        + [f"-l{x}" for x in cfg.LIBS]

        if cfg.VSCODE_CPPTOOLS_CONFIG:
            make_cpp_properties(self.parent, cfg)

        with open(f"{self.parent.PRIVATE_CONFIG['OBJ_PATH']}/config_str",'w+') as f:
            f.write(get_c_build_config_str(self.parent.PRIVATE_CONFIG))

        return sh(self.cmd)

class RuleStatic(Rule):
    def execute(self, target:str) -> int:
        app_logger.info(f"{color_text(33,'Linking static')}: {os.path.relpath(target)}")

        if not os.path.exists(target):
            os.makedirs(os.path.dirname(target),exist_ok=True)

        cfg = CConfig(self.parent.CONFIG)

        self.cmd = [cfg.AR] \
        + [''.join(cfg.AR_FLAGS)] \
        + [target] \
        + self.prerequisites

        if cfg.VSCODE_CPPTOOLS_CONFIG:
            make_cpp_properties(self.parent, cfg)

        with open(f"{self.parent.PRIVATE_CONFIG['OBJ_PATH']}/config_str",'w+') as f:
            f.write(get_c_build_config_str(self.parent.PRIVATE_CONFIG))

        return sh(self.cmd)

class RuleCClean(Rule):
    def __init__(self, parent: Project) -> None:
        super().__init__(parent, 'clean')

    def execute(self, target: str) -> int:
        def _rm(p:Project):
            for sp in p.SUBPROJECTS:
                _rm(sp)

            silentremove(p.PRIVATE_CONFIG['OBJ_PATH'])
        _rm(self.parent)

class CConfig():
    def __init__(self, init:dict[str,] = None) -> None:
        self.INCLUDE_DIRS : list[str] = []
        '''
            Include directories for this project and children
        '''

        self.COMPILER : str = 'clang'
        '''
            Compiler exe name
        '''

        self.AR : str = 'ar'
        '''
            Archiver
        '''

        self.AR_FLAGS : list[str] = ['r','c','s']
        '''
            Archiver flags
        '''

        self.CFLAGS : list[str] = []
        '''
            Compile flags
        '''

        self.LINK_FLAGS : list[str] = []
        '''
            Flags used while linking
        '''

        self.LIB_DIRS : list[str] = []
        '''
            Directories where looking for libraries
        '''

        self.LIBS : list[str] = []
        '''
            List of libraries
        '''

        self.PKG_SEARCH : list[str] = []
        '''
            If `pkg-config` present in system this libraries
            will be auto included in project
        '''

        self.DEFINES : list[str] = []
        '''
            Defines used in this project and all its children
        '''

        self.SOURCES : list[str] = []
        '''
        '''

        self.OBJ_PATH : str = "obj"
        '''
        '''

        self.VSCODE_CPPTOOLS_CONFIG : bool = False
        '''
            Generate C/C++ Tools for Visual Studio Code config (c_cpp_properties.json)
        '''

        if init:
            self.__dict__.update(init)

def get_c_build_config_str(config:dict[str,]) -> str:
    '''
        Config string need to sign config of built files
        If any flag, that influences on the result file was changed then need to rebuild all targets
    '''
    return str([config[key] for key in ['AR','COMPILER','CFLAGS','DEFINES','LINK_FLAGS'] if key in config])

def set_c_config_paths_absolute(prj:Project, config:dict[str,]):
    for key in config.keys():
        if key in ['LIB_DIRS','INCLUDE_DIRS','SOURCES']:
            config[key] = [abspath_project(prj, x) for x in config[key]]
        if key == 'OBJ_PATH':
            config[key] = abspath_project(prj, config[key])

def get_rules_from_d_file(p:Project, path : str):
    result = []
    if not os.path.isfile(path):
        return result

    with open(path,'r') as f:
        content = f.read()

    # make list[str] = ["/dir/targtet:src1.c src2.c src3.c", ...]
    content = content.replace('\\\n','')
    content = content.replace('\n\n','\n')
    content = content.replace('   ',' ')
    content = content.split('\n')

    for line in content:
        if not line:
            continue
        spl = line.split(':')
        if len(spl) < 2:
            continue

        target = spl[0]
        prerequisites = [x for x in spl[1].strip().split(' ') if x != target] if spl[1] else []
        p.RULES.append(Rule(p,target,prerequisites))

def pkg_config_search(config:dict[str,]):
    # Load libs data from pkg-config
    if 'PKG_SEARCH' in config and config['PKG_SEARCH']:
        out = sh_capture(["pkg-config","--cflags","--libs"]+config['PKG_SEARCH'])
        if not out.startswith('-'):
            if "command not found" in out:
                raise RuntimeError("PKG_SEARCH present, but pkg-config not found")
            if "No package" in out:
                raise RuntimeError(out)
        else:
            out = out.replace('\n','')
            spl = out.split(' ')
            inc_dirs = [x[2:] for x in spl if x.startswith('-I')]
            lib_dirs = [x[2:] for x in spl if x.startswith('-L')]
            libs     = [x[2:] for x in spl if x.startswith('-l')]

            config['INCLUDE_DIRS']  = config['INCLUDE_DIRS'] + inc_dirs if 'INCLUDE_DIRS' in config else inc_dirs
            config['LIB_DIRS']      = config['LIB_DIRS'] + lib_dirs     if 'LIB_DIRS' in config else lib_dirs
            config['LIBS']          = config['LIBS'] + libs             if 'LIBS' in config else libs

def before_run_build_c(prj:Project):
    def rm_artifacts(p:Project):
        for sp in p.SUBPROJECTS:
            rm_artifacts(sp)

        cfg_path = f'{p.PRIVATE_CONFIG["OBJ_PATH"]}/config_str'
        rm = False
        if os.path.exists(cfg_path):
            with open(cfg_path, 'r') as f:
                if f.read() != get_c_build_config_str(p.PRIVATE_CONFIG):
                    rm = True
        if rm:
            silentremove(p.PRIVATE_CONFIG["OBJ_PATH"])

    rm_artifacts(prj)

def create_c_project(name:str,target_file:str, src_dirs = ['src'], src_extensions=['.c'], subprojects:list[Project]=[],
                     export_config:dict[str,]={}, config:dict[str,]={}, private_config:dict[str,]={}) -> Project:

    p = Project(name,target_file)
    p.BEFORE_RUN_BUILD_CALLBACK = before_run_build_c

    set_c_config_paths_absolute(p,export_config)
    set_c_config_paths_absolute(p,config)
    set_c_config_paths_absolute(p,private_config)

    try:
        pkg_config_search(export_config)
        pkg_config_search(config)
        pkg_config_search(private_config)
    except Exception as e:
        app_logger.error(f'Project {target_file}: {e}')
        exit()

    p.EXPORT_CONFIG = export_config
    p.PRIVATE_CONFIG = private_config
    p.CONFIG = config

    extend_config(p.PRIVATE_CONFIG, p.CONFIG)
    extend_config(p.PRIVATE_CONFIG, p.EXPORT_CONFIG)

    p.RULES.append(Rule(p,Regex(r'.*\.c')))
    p.RULES.append(Rule(p,Regex(r'.*\.h')))
    p.RULES.append(RuleCClean(p))
    p.RULES.append(RuleGenerateVSCODE(p))

    obj_path = private_config['OBJ_PATH'] if 'OBJ_PATH' in private_config else abspath_project(p,'obj')
    p.PRIVATE_CONFIG['OBJ_PATH'] = obj_path

    obj_path = abspath_project(p,obj_path)
    src_dirs = [abspath_project(p,x) for x in src_dirs]
    sources = find_files(src_dirs,src_extensions)
    if 'SOURCES' in private_config:
        sources.extend(private_config['SOURCES'])

    sources = unique_list(sources)

    objects = []
    for src in sources:
        artefact = f'{obj_path}/{os.path.splitext(relpath_project(p,src).replace("../","updir/"))[0]}'
        object = f'{artefact}.o'
        dep = f'{artefact}.d'
        p.RULES.append(RuleO(p,object,src,phony=False))
        objects.append(object)
        get_rules_from_d_file(p,dep)

    if p.TARGET.endswith('.a'):
        target_rule = RuleStatic(p, p.TARGET, objects,phony=False)
    else:
        target_rule = RuleExe(p, p.TARGET, objects,phony=False)

    p.RULES.append(target_rule)

    if subprojects:
        p.SUBPROJECTS.extend(subprojects)
        for sp in subprojects:
            target_rule.prerequisites.append(sp.TARGET)

    return p

#----------------------END C---------------------------

#----------------------PYTHON--------------------------

class RulePython(Rule):
    def __init__(self, parent: Project, targets: str | Regex | list[str | Regex], prerequisites: str | list[str] = []) -> None:
        super().__init__(parent, targets, prerequisites, phony=False)

    def execute(self, target:str) -> int:
        app_logger.info(f"{color_text(35,'Script running')}: {os.path.relpath(self.prerequisites[0])}")

        if not os.path.exists(target):
            os.makedirs(os.path.dirname(target),exist_ok=True)

        return sh(self.prerequisites[0])

#----------------------END PYTHON----------------------

def process(get_project_fnc, get_config_fnc=None):
    global config

    if get_config_fnc:
        config = get_config_fnc()

    setup_logger(config)
    if config.MINIMUM_REQUIRED_VERSION > VERSION:
        app_logger.warning(f"Required version {config.MINIMUM_REQUIRED_VERSION} is higher than running {VERSION}!")

    project = 'main'
    target = 'build'
    ln = len(sys.argv)
    ln = 3 if ln > 3 else ln

    match len(sys.argv):
        case 3:
            project = sys.argv[1]
            target = sys.argv[2]
        case 2:
            target = sys.argv[1]
        case 1:
            pass

    try:
        p : Project = get_project_fnc(project)
        if not p:
            raise Exceptions.ProjectNotFound()

        rule : Rule = p.get_rule(p,target)
        if not rule:
            raise Exceptions.RuleNotFound(target)

        rule.execute('')

    except Exception as e:
        app_logger.error(e)
