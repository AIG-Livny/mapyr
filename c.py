from .core import *
from .logger import app_logger, color_text

import json

class Config(ConfigBase):
    def __init__(self) -> None:
        super().__init__()

        self.SRC_DIRS : list[str] = ['src']
        '''
            Paths to sources
        '''

        self.OBJ_PATH : str = 'obj'
        '''
            Path where to store object files
        '''

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

    def get_build_string(self) -> str:
        '''
            Config string need to sign config of built files
            If any flag, that influences on the result file was changed then need to rebuild all targets
        '''
        lst = [
            self.AR,
            self.COMPILER,
            self.CFLAGS,
            self.DEFINES,
            self.LINK_FLAGS,
        ]
        return str(lst)

    def get_abs_val(self, val:str|list[str]):
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

    def make_abs(self):
        '''
            Make absolute paths
        '''
        for k in self.__dict__.keys():
            if k not in ['TARGET_PATH','SRC_DIRS','OBJ_PATH','INCLUDE_DIRS','LIB_DIRS','SOURCES']:
                continue
            self.__dict__[k] = self.get_abs_val(self.__dict__[k])

    def extend(self, other:'Config'):
        self.INCLUDE_DIRS.extend(other.get_abs_val(other.INCLUDE_DIRS))

class Project(ProjectBase):
    def __init__(self,
            name:str,
            target:str,
            private_config:Config = None,
            protected_config:Config = None,
            public_config:Config = None,
            subprojects:list['ProjectBase'] = None
        ):
        super().__init__(name, target, private_config, protected_config, public_config, subprojects)

        self.private_config     : Config
        self.protected_config   : Config
        self.public_config      : Config

        self.delete_objects_if_config_different()

    def delete_objects_if_config_different(self):
        '''
            If already built objects config not match current config
            we must delete old objects and build new
        '''
        if os.path.isabs(self.private_config.OBJ_PATH):
            ap = self.private_config.OBJ_PATH
        else:
            ap = os.path.join(self.private_config.CWD, self.private_config.OBJ_PATH)

        cfg_path = os.path.join(ap,'config_tag')
        if os.path.exists(cfg_path):
            with open(cfg_path, 'r') as f:
                if f.read() != self.private_config.get_build_string():
                    silentremove(ap)
        return 0

    def build(self, rule:Rule):
        # Before build, make all configs absolute path
        def _set_absolute_config_paths(project:ProjectBase, parent_project:ProjectBase):
            if type(project) is Project:
                project.private_config.make_abs()

        self.project_recursive_run(_set_absolute_config_paths)

        return super().build(rule)

def vscode_make_cpp_properties(rule:Rule,cfg:'Config'):
    '''
        For visual studio code, С/С++ extension.
    '''
    vscode_file_path = f'{rule._cwd}/.vscode/c_cpp_properties.json'
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

    cfg : Config = rule.parent.private_config

    cmd = \
        [cfg.COMPILER,'-MT','','-MMD','-MP','-MF',''] \
        + cfg.CFLAGS \
        + [f"-D{x}" for x in cfg.DEFINES] \
        + [f"-I{x}" for x in cfg.INCLUDE_DIRS] \
        + ['-c','-o','','']

    path_wo_ext     = os.path.splitext(rule.target)[0]
    cmd[2]     = rule.prerequisites[0].target
    cmd[6]     = f"{path_wo_ext}.d"
    cmd[-2]    = rule.target
    cmd[-1]    = rule.prerequisites[0].target
    # mapyr special flags
    cmd.insert(7, f'-D__MAPYR__FILENAME__="{os.path.basename(rule.prerequisites[0].target)}"')
    return sh(cmd).returncode

def link_executable(rule:Rule) -> int:
    app_logger.info(f"{color_text(32,'Linking executable')}: {os.path.relpath(rule.target)}")

    os.makedirs(os.path.dirname(rule.target),exist_ok=True)

    cfg : Config = rule.parent.private_config

    cmd = [cfg.COMPILER] \
    + cfg.LINK_FLAGS \
    + [f"-L{x}" for x in cfg.LIB_DIRS] \
    + [x.target for x in rule.prerequisites] \
    + ['-o',rule.target] \
    + [f"-l{x}" for x in cfg.LIBS]

    if cfg.VSCODE_CPPTOOLS_CONFIG:
        vscode_make_cpp_properties(rule, cfg)

    with open(os.path.join(cfg.CWD, cfg.OBJ_PATH,'config_tag'),'w+') as f:
        f.write(cfg.get_build_string())

    return sh(cmd).returncode

def link_static(rule:Rule) -> int:
    app_logger.info(f"{color_text(33,'Linking static')}: {os.path.relpath(rule.target)}")

    os.makedirs(os.path.dirname(rule.target),exist_ok=True)

    cfg : Config = rule.parent.private_config

    cmd = [cfg.AR] \
    + [''.join(cfg.AR_FLAGS)] \
    + [rule.target] \
    + [x.target for x in rule.prerequisites]

    if cfg.VSCODE_CPPTOOLS_CONFIG:
        vscode_make_cpp_properties(rule, cfg)

    with open(os.path.join(cfg.CWD,cfg.OBJ_PATH,'config_tag'),'w+') as f:
        f.write(cfg.get_build_string())

    return sh(cmd).returncode

def add_rules_from_d_file(path:str,project:ProjectBase):
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
        rule = project.find_rule(target)
        if not rule:
            rule = Rule(target,project)

        for prq in prerequisites:
            prq_rule = project.find_rule(prq)
            if not prq_rule:
                prq_rule = Rule(prq,project)
                project.rules.append(prq_rule)
            rule.prerequisites.append(prq_rule)


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


def add_default_rules(project:ProjectBase) -> None:
    '''
        Auto create rules for C project
    '''
    cfg : Config = project.private_config
    target_path = cfg.parent.target if os.path.isabs(cfg.parent.target) else os.path.join(cfg.CWD,cfg.parent.target)
    cfg.SOURCES = cfg.get_abs_val(cfg.SOURCES) + find_files(cfg.SRC_DIRS,['.c','.cc','.cpp'],cfg.CWD)
    objects = [os.path.join(cfg.CWD,'obj',os.path.relpath(os.path.splitext(x)[0],cfg.CWD).replace('../','updir/'))+'.o' for x in cfg.SOURCES]
    deps = [f'{os.path.splitext(x)[0]}.d' for x in objects]

    ext = os.path.splitext(target_path)[1]
    object_rules = []

    for i in range(len(cfg.SOURCES)):
        src_rule = Rule(cfg.SOURCES[i], cfg.parent)
        project.rules.append(src_rule)

        object_rule = Rule(objects[i], cfg.parent, [src_rule], build_object,False)
        object_rules.append(object_rule)

        project.rules.append(object_rule)
        add_rules_from_d_file(deps[i],project)

    match ext:
        case '.a':
            if not project.public_config:
                project.public_config = cfg
            project.main_rule = Rule(cfg.parent.target, cfg.parent, object_rules, link_static, False)
            project.rules.append(project.main_rule)

            pub_cfg : Config = project.public_config
            pub_cfg.LIBS.append(os.path.basename(target_path)[3:-2])
            pub_cfg.LIB_DIRS.append(os.path.dirname(target_path))

        case '.so','.dll':
            raise NotImplementedError('The shared library rules maker not implemented yet')

        case '.exe'|'':
            project.main_rule = Rule(cfg.parent.target, cfg.parent, object_rules, link_executable, False)
            project.rules.append(project.main_rule)
            for sp in project.subprojects:
                project.main_rule.prerequisites.append(sp.main_rule)
                project.private_config.extend(sp.public_config)

    rule_build = Rule('build',project,[project.main_rule],phony=True)
    project.rules.append(rule_build)
