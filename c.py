from .core import *
from .logger import app_logger, color_text

import json

class Config():
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

        self.DEFINES : list[str] = []
        '''
            Defines used in this project and all its children
        '''

        self.SOURCES : list[str] = []
        '''
            List of source files
        '''

        self.VSCODE_CPPTOOLS_CONFIG : bool = False
        '''
            Generate C/C++ Tools for Visual Studio Code config (c_cpp_properties.json)
        '''

        if init:
            self.__dict__.update(init)

    def set_paths_absolute(self):
        cwd = caller_cwd()
        for key in self.__dict__.keys():
            if key in ['LIB_DIRS','INCLUDE_DIRS','SOURCES']:
                lst = self.__dict__[key]
                for i in range(len(lst)):
                    if not os.path.isabs(lst[i]):
                        lst[i] = os.path.join(cwd,lst[i])


def get_c_build_config_str(config:dict[str,]) -> str:
    '''
        Config string need to sign config of built files
        If any flag, that influences on the result file was changed then need to rebuild all targets
    '''
    return str([config[key] for key in ['AR','COMPILER','CFLAGS','DEFINES','LINK_FLAGS'] if key in config])

def vscode_make_cpp_properties(rule:Rule,cfg:'Config'):
    '''
        For visual studio code, С/С++ extension.
    '''
    vscode_file_path = f'{rule.cwd}/.vscode/c_cpp_properties.json'
    if os.path.exists(vscode_file_path):
        import inspect
        build_py_filename = inspect.stack()[2].filename
        if os.path.getmtime(build_py_filename) <= os.path.getmtime(vscode_file_path):
            return

    config = {
        'name':os.path.basename(rule.target),
        'includePath':cfg.INCLUDE_DIRS,
        'defines':cfg.DEFINES
    }

    main_config = {
        'configurations':[config],
        "version": 4
    }

    with open(vscode_file_path, 'w+') as f:
        json.dump(main_config, f, indent=4)

def build_object(rule:Rule) -> int:
    app_logger.info(f"{color_text(94,'Building')}: {os.path.relpath(rule.target)}")

    os.makedirs(os.path.dirname(rule.target),exist_ok=True)

    cfg = Config(rule.config)

    cmd = \
        [cfg.COMPILER,'-MT','','-MMD','-MP','-MF',''] \
        + cfg.CFLAGS \
        + [f"-D{x}" for x in cfg.DEFINES] \
        + [f"-I{x}" for x in cfg.INCLUDE_DIRS] \
        + ['-c','-o','','']

    path_wo_ext     = os.path.splitext(rule.target)[0]
    cmd[2]     = rule.prerequisites[0]
    cmd[6]     = f"{path_wo_ext}.d"
    cmd[-2]    = rule.target
    cmd[-1]    = rule.prerequisites[0]
    # mapyr special flags
    cmd.insert(7, f'-D__MAPYR__FILENAME__="{os.path.basename(rule.prerequisites[0])}"')
    return sh(cmd).returncode

def link_executable(rule:Rule) -> int:
    app_logger.info(f"{color_text(32,'Linking executable')}: {os.path.relpath(rule.target)}")

    os.makedirs(os.path.dirname(rule.target),exist_ok=True)

    cfg = Config(rule.config)

    cmd = [cfg.COMPILER] \
    + cfg.LINK_FLAGS \
    + [f"-L{x}" for x in cfg.LIB_DIRS] \
    + rule.prerequisites \
    + ['-o',rule.target] \
    + [f"-l{x}" for x in cfg.LIBS]

    if cfg.VSCODE_CPPTOOLS_CONFIG:
        vscode_make_cpp_properties(rule, cfg)

    with open(os.path.join(rule.cwd,'config_tag'),'w+') as f:
        f.write(get_c_build_config_str(cfg.__dict__))

    return sh(cmd).returncode

def link_static(rule:Rule) -> int:
    app_logger.info(f"{color_text(33,'Linking static')}: {os.path.relpath(rule.target)}")

    os.makedirs(os.path.dirname(rule.target),exist_ok=True)

    cfg = Config(rule.config)

    cmd = [cfg.AR] \
    + [''.join(cfg.AR_FLAGS)] \
    + [rule.target] \
    + rule.prerequisites

    if cfg.VSCODE_CPPTOOLS_CONFIG:
        vscode_make_cpp_properties(rule, cfg)

    with open(os.path.join(rule.cwd,'config_tag'),'w+') as f:
        f.write(get_c_build_config_str(cfg.__dict__))

    return sh(cmd).returncode

def clean(_rule:Rule) -> int:
    def _clean(rule:Rule, parent_rule:Rule) -> bool:
        if rule.target.endswith('.o'):
            silentremove(rule.target)

    recursive_run(_rule.target,_clean)
    return 0

def check_build(rule:Rule) -> int:
    '''
        If already built objects config not match current config
        we must delete old objects and build new
    '''
    from .core import RULES
    cfg = Config(rule.config)

    cfg_path = os.path.join(rule.cwd,'config_tag')
    if os.path.exists(cfg_path):
        with open(cfg_path, 'r') as f:
            if f.read() != get_c_build_config_str(cfg.__dict__):
                clean(rule)
    return 0

def add_rules_from_d_file(path : str, rules:list[Rule]):
    if not os.path.isabs(path):
        path = os.path.join(caller_cwd(),path)
    if not os.path.isfile(path):
        return

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
        rule = find_rule(target,rules)
        if rule:
            rule.prerequisites.extend(prerequisites)
        else:
            rules.append(Rule(target,prerequisites))

def gen_vscode_config(rule:Rule):
    '''
        Default vs code configs
    '''
    if os.path.exists('.vscode'):
        app_logger.error('directory .vscode already exists')
        exit()
    os.makedirs('.vscode')
    launch = {"version":"0.2.0","configurations":[{"name":"app","type":"cppdbg","request":"launch","program":"main","args":[],"stopAtEntry":False,"cwd":"${workspaceFolder}","environment":[],"externalConsole":False,"MIMode":"gdb","preLaunchTask":"build","setupCommands":[{"text":"-enable-pretty-printing","ignoreFailures":True},{"text":"-gdb-set disassembly-flavor intel","ignoreFailures":True}]}]}
    tasks = {"version":"2.0.0","tasks":[{"label":"build","type":"shell","command":"./build.py","group":{"isDefault":True,"kind":"build"},"presentation":{"clear":True}},{"label":"clean","type":"shell","command":"./build.py clean","presentation":{"reveal":"never"}}]}
    with open('.vscode/launch.json','w+') as flaunch, open('.vscode/tasks.json','w+') as ftasks:
        json.dump(launch, flaunch, indent=4)
        json.dump(tasks, ftasks, indent=4)

def pkg_config_search(packages:list[str],config:Config):
    '''
        Load libs data from pkg-config
    '''

    out = sh(["pkg-config","--cflags","--libs"]+packages,True)
    if out.stderr:
        app_logger.error(f'pkg_config_search :{out.stderr}')
        return
    out = out.stdout.replace('\n','')
    spl = out.split(' ')

    config.INCLUDE_DIRS.extend([x[2:] for x in spl if x.startswith('-I')])
    config.LIB_DIRS.extend([x[2:] for x in spl if x.startswith('-L')])
    config.LIBS.extend([x[2:] for x in spl if x.startswith('-l')])


def create_standard_rules_macro(target_file:str, config:Config = None, upstream_config:Config = None) -> list[Rule]:
    rules = []
    cwd = caller_cwd()
    sources = find_files(['src'],['.c','.cc','.cpp'],cwd)
    objects = [os.path.join(cwd,'obj',os.path.relpath(os.path.splitext(x)[0],cwd).replace('../','updir/'))+'.o' for x in sources]
    deps = [f'{os.path.splitext(x)[0]}.d' for x in objects]

    rules = [
        Rule('build',[target_file],phony=True, cwd=cwd),
    ]
    if target_file.endswith('.a'):
        if not upstream_config:
            upstream_config = Config()
        upstream_config.LIBS.append(os.path.basename(target_file)[3:-2])
        upstream_config.LIB_DIRS.append(os.path.join(cwd, os.path.dirname(target_file)))

        rules.append(Rule(target_file,objects,exec=link_static,upstream_config=upstream_config.__dict__, cwd=cwd))
    if os.path.splitext(target_file)[1] in ['.so','.dll']:
        raise NotImplementedError('The shared library rules maker not implemented yet')

    for i in range(len(sources)):
        rules.append(Rule(objects[i],[sources[i]],exec=build_object,config=dict(config) if config else dict(), cwd=cwd))
        rules.append(Rule(sources[i], cwd=cwd))
        add_rules_from_d_file(deps[i],rules)

    return rules
