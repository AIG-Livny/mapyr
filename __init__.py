import sys
import os
import shutil
import subprocess
import concurrent.futures
import logging
import json
import copy

VERSION = '0.4.4'

#----------------------PROJECT CONFIG------------------

class ProjectConfig:
    '''
        This config used for any project. Controls project build process
    '''

    def __init__(self) -> None:
        self.OUT_FILE : str = ""
        '''
            Name of out file. Name and extension defines type of file:
                - executable: without extension or `.exe`
                - static library:	`lib%.a`
                - dynamic library:	`%.dll` or `%.so`
        '''

        self.GROUPS : list[str] = ['DEBUG']
        '''
            A project can belong to several groups. Default group is DEBUG
            When build.py started without arguments, it runs build DEBUG group
        '''

        self.COMPILER : str = "clang"
        '''
            Compiler, global variable, come from main project
        '''

        self.OBJ_PATH : str = "obj"
        '''
            Path where store object files
        '''

        self.AR : str = "ar"
        '''
            Archiver
        '''

        self.SRC_EXTS : list[str] = [".cpp",".c"]
        '''
            Source extensions for search
        '''

        self.SRC_DIRS : list[str] = ["src"]
        '''
            Source directories for NOT recursive search
        '''

        self.SRC_RECURSIVE_DIRS : list[str] = []
        '''
            Source directories for recursive search
        '''

        self.INCLUDE_DIRS : list[str] = []
        '''
            Private include directories
        '''

        self.EXPORT_INCLUDE_DIRS : list[str] = []
        '''
            Include directories that also will be sended to parent project
            and parent will include them while his building process
        '''

        self.AR_FLAGS : list[str] = ["r","c","s"]
        '''
            Archiver flags
        '''

        self.CFLAGS : list[str] = ["-O3"]
        '''
            Compile flags
        '''

        self.LINK_EXE_FLAGS : list[str] = []
        '''
            Flags used while executable linking
        '''

        self.SUBPROJECTS : list[str] = []
        '''
            Paths to directories contains build.py
            If subproject is library, it will
            auto-included as library in the project.
        '''

        self.LIB_DIRS : list[str] = []
        '''
            Directories where looking for libraries
        '''

        self.LIBS : list[str] = []
        '''
            List of libraries
        '''

        self.INCLUDE_FLAGS : list[str] = []
        '''
            Flags that will passed to compiler in the include part of command.
            This is automatic variable, but you can add any flag if it needed
        '''

        self.LIB_DIRS_FLAGS : list[str] = []
        '''
            Flags that will passed to linker in library directories part of command.
            This is automatic variable, but you can add any flag it if needed
        '''

        self.LIBS_FLAGS : list[str] = []
        '''
            Flags that will passed to linker in library part of command.
            This is automatic variable, but you can add any flag it if needed
        '''

        self.PKG_SEARCH : list[str] = []
        '''
            If `pkg-config` installed in system then this libraries
            will be auto included in project
        '''

        self.SOURCES : list[str] = []
        '''
            Particular source files.
            This is automatic variable, but you can add any flag if needed
        '''

        self.EXCLUDE_SOURCES : list[str] = []
        '''
            Sometimes need to exclude a specific source file from auto search
            Add path to source in relative or absolute format
        '''

        self.PRIVATE_DEFINES : list[str] = []
        '''
            Private defines, that will be used only in this project
        '''

        self.DEFINES : list[str] = []
        '''
            Defines used in this project and all its children
        '''

        self.EXPORT_DEFINES : list[str] = []
        '''
            Defines that used in the project and also
            will be passed to parent project
        '''

        self.MAX_THREADS_NUM : int = 10
        '''
            Build threads limit
        '''

        self.VSCODE_CPPTOOLS_CONFIG : bool = False
        '''
            Generate C/C++ Tools for Visual Studio Code config (c_cpp_properties.json)
        '''

        self.OVERRIDE_CFLAGS : bool = False
        '''
            Override CFLAGS in children projects
        '''

    def copy(self) -> "ProjectConfig":
        return copy.copy(self)

#----------------------END PROJECT CONFIG--------------

#----------------------TOOL CONFIG---------------------

class ToolConfig:
    '''
        This config used while sertain build.py running. Config controls MAPYR features
    '''

    def __init__(self) -> None:
        self.MINIMUM_REQUIRED_VERSION : str = VERSION
        '''
            Minimum required version for this config file (build.py)
        '''

        self.VERBOSITY : str = "INFO"
        '''
            Verbosity level for console output. Value can be any from logging module: ['CRITICAL','FATAL','ERROR','WARN','WARNING','INFO','DEBUG','NOTSET']
        '''

#----------------------END TOOL CONFIG-----------------

#----------------------EXCEPTIONS----------------------
class Exceptions:
    class CustomException(Exception):
        def __init__(self): super().__init__(self.__doc__)

    class CircularDetected(CustomException):
        "Circular dependency detected!"
    class OutFileEmpty(CustomException):
        "Variable: OUT_FILE empty!"
#----------------------END EXCEPTIONS------------------

#----------------------LOGGING-------------------------
app_logger : logging.Logger = None

def setup_logger(config: ToolConfig):
    global app_logger
    file_formatter = logging.Formatter('%(asctime)-15s|PID:%(process)-11s|%(levelname)-8s|%(filename)s:%(lineno)s| %(message)s')
    console_formatter = logging.Formatter('[%(levelname)s]: %(message)s')

    file_path = f"{os.path.dirname(os.path.realpath(__file__))}/debug.log"
    file_handler = logging.FileHandler(file_path,'w',encoding='utf8')
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(config.VERBOSITY)
    console_handler.setFormatter(console_formatter)

    rootlog = logging.getLogger()
    rootlog.addHandler(file_handler)

    app_logger = logging.getLogger('main')
    app_logger.propagate = False
    app_logger.setLevel(logging.DEBUG)
    app_logger.addHandler(file_handler)
    app_logger.addHandler(console_handler)

#----------------------LOGGING-------------------------

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

def sh(cmd: list[str]) -> int:
    '''
        Run shell command and ignore answer, but code
    '''
    return subprocess.Popen(cmd).wait()

def sh_capture(cmd: list[str]) -> str:
    '''
        Run shell command and get stdin or stderr
    '''
    run = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout,stderr = run.communicate()
    run.wait()
    if len(stderr) > 0:
        return stderr.decode()
    return stdout.decode()

def silentremove(filename):
    '''
        Remove file or ignore error if not found
    '''
    try:
        os.remove(filename)
    except FileNotFoundError:
        pass

def get_size(path:str) -> int:
    '''
        Get file size in bytes
    '''
    if os.path.exists(path):
        return os.stat(path).st_size
    return -1

def diff(old:int, new:int) -> str:
    '''
        Get difference btw two numbers in string format with test color and sign
    '''
    diff = new - old
    summstr = '0'
    if diff > 0:
        summstr = color_text(31,f'+{diff}')
    if diff < 0:
        summstr = color_text(32,f'{diff}')
    return summstr

def unique_list(l:list):
    result = []
    for v in l:
        if v not in result:
            result.append(v)
    return result

#----------------------END UTILS-----------------------

#----------------------COMMAND-------------------------
class Command:
    '''
        Command unit contains comand line + console message format
    '''

    mfLinkStatic = f"{color_text(33,'Linking static')}: {{}}"
    mfLinkExe    = f"{color_text(32,'Linking executable')}: {{}}"
    mfBuild      = f"{color_text(94,'Building')}: {{}}"

    def __init__(self, parent_target:"Target", cmd:list[str], message_format:str) -> None:
        self.parent_target = parent_target
        self.cmd = cmd
        self.message_format = message_format

    def run(self, ) -> int:
        name = os.path.relpath(self.parent_target.path)
        app_logger.info(self.message_format.format(name))
        app_logger.debug(f'{name} run: {self.cmd}')
        return sh(self.cmd)

#----------------------END COMMAND---------------------

#----------------------TARGET--------------------------
class Target:
    '''
        Target file.
        `path` - target path with file name.
        `prerequisites` - all other files that must be builded before.
        `parent` - project to which this target belongs.
        `need_build` - if target have to be built.
    '''
    def __init__(self, path:str, prerequisites : list["Target"], parent:"Project", need_build:bool=False) -> None:
        self.path           : str           =  os.path.abspath(path)
        self.prerequisites  : list[Target]  = prerequisites
        self.parent         : Project       = parent
        self.need_build     : bool          = need_build

    def get_cmd(self) -> Command:
        '''
            Return command to build this target
        '''
        p = self.parent
        def _cmd_link_exe() -> Command:
            p.config.LIB_DIRS_FLAGS.extend([f"-L{x}" for x in p.config.LIB_DIRS])
            p.config.LIBS_FLAGS.extend([f"-l{x}" for x in p.config.LIBS])
            p.config.LIB_DIRS_FLAGS = unique_list(p.config.LIB_DIRS_FLAGS)
            p.config.LIBS_FLAGS = unique_list(p.config.LIBS_FLAGS)

            obj = [x.path for x in self.prerequisites if x.path.endswith('.o')]
            cmd = [p.config.COMPILER]+p.config.LINK_EXE_FLAGS+p.config.LIB_DIRS_FLAGS+obj+['-o',self.path]+p.config.LIBS_FLAGS
            return Command(self, cmd, Command.mfLinkExe)

        def _cmd_link_static() -> Command:
            obj = [x.path for x in self.prerequisites if x.path.endswith('.o')]
            cmd = [p.config.AR]+[''.join(p.config.AR_FLAGS)]+[self.path]+obj
            return Command(self, cmd, Command.mfLinkStatic)

        def _cmd_build_c(source:str) -> Command:
            # mapyr special flags
            p.config.CFLAGS.append(f'-D__MAPYR__FILENAME__="{os.path.basename(source)}"')

            # flags
            p.config.CFLAGS.extend([f"-D{x}" for x in p.config.PRIVATE_DEFINES])
            p.config.CFLAGS.extend([f"-D{x}" for x in p.config.DEFINES])
            p.config.INCLUDE_FLAGS.extend([f"-I{x}" for x in p.config.INCLUDE_DIRS])
            p.config.CFLAGS = unique_list(p.config.CFLAGS)
            p.config.INCLUDE_FLAGS = unique_list(p.config.INCLUDE_FLAGS)

            basename = os.path.splitext(self.path)[0]
            depflags = ['-MT',self.path,'-MMD','-MP','-MF',f"{basename}.d"]
            cmd = [p.config.COMPILER]+depflags + p.config.CFLAGS
            cmd += p.config.INCLUDE_FLAGS +['-c','-o',self.path,source]
            return Command(self, cmd, Command.mfBuild)

        ext_trg = os.path.splitext(self.path)[1]
        match(ext_trg):
            case '' | '.exe': return _cmd_link_exe()
            case '.a': return _cmd_link_static()
            case '.o':
                for prq in self.prerequisites:
                    ext_prq = os.path.splitext(prq.path)[1]
                    match(ext_prq):
                        case '.c' | '.cc' | '.cpp': return _cmd_build_c(prq.path)

        app_logger.error(f"{color_text(91,'Not found cmd builder for')}: {os.path.relpath(self.path)}")
        exit()

    def build(self) -> int:
        '''
            Build target. If it is main target and PRINT_SIZE env present,
            so it can print file size difference
        '''
        if os.getenv('PRINT_SIZE'):
            if self.parent.main_target is self:
                old_size = 0
                if os.path.exists(self.path):
                    old_size=os.stat(self.path).st_size

                code = self.get_cmd().run()

                if code == 0:
                    new_size=os.stat(self.path).st_size
                    app_logger.info(f'{os.path.relpath(self.path)} size {new_size} {f"[{diff(old_size,new_size)}]" if old_size else ""}')

                return code
        return self.get_cmd().run()

    def __repr__(self) -> str:
        return f'{self.path}:{self.prerequisites}'

#----------------------END TARGET----------------------

#----------------------TARGET CONTAINER----------------
class TargetContainer:
    def __init__(self) -> None:
        self.targets : list[Target] = []

    def find_target(self, path: str) -> Target:
        '''
            Find target by out file
        '''
        path = os.path.abspath(path)

        for t in self.targets:
            if path == t.path:
                return t
        return None

    def add(self, t:Target) -> Target:
        '''
            Add target or extend prerequisites if target already exists
        '''
        found = self.find_target(t.path)
        if found:
            for prq in t.prerequisites:
                if prq not in found.prerequisites:
                    self.add(prq)
                    found.prerequisites.append(prq)
            return found
        else:
            self.targets.append(t)
            return t

    def add_from_container(self, cnt:"TargetContainer"):
        '''
            Add targets from other container
        '''
        for t in cnt.targets:
            self.add(t)

#----------------------END TARGET CONTAINER------------

#----------------------PROJECT-------------------------

class Project:
    '''
        Project contain all data needed to build the project
        `targets` - its own targets
        `targets_recursive` - own targets and all children recursive targets
        `config` - configuration
        `cwd` - working directory of project
    '''
    def __init__(self, config:ProjectConfig) -> None:
        self.targets            = TargetContainer()
        self.targets_recursive  = TargetContainer()
        self.config             : ProjectConfig = config
        self.main_target        : Target = Target(self.config.OUT_FILE,[],self)
        self.subprojects        : list[Project] = []
        self.cwd                : str = os.getcwd()

    def get_targets_from_d_file(self, path : str):
        '''
            Get targets from .d file - is usual format of dependency files
            for c/cpp compilers
        '''

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

            prerequisites = spl[1].split(' ')
            path = os.path.abspath(spl[0])
            preq : list[Target] = []
            for prq in prerequisites:
                if prq:
                    prq_target = self.targets.add(Target(os.path.abspath(prq),[],self))
                    preq.append(prq_target)

            self.targets.add(Target(path,preq,self))

    def find_targets_contains_prerequisite(self,target:Target) -> list[Target]:
        '''
            Find all targets that contain `path` in them prerequisites that need build
        '''
        result=[]
        for trg in self.targets_recursive.targets:
            if trg.need_build:
                continue
            if target in trg.prerequisites:
                result.append(trg)
        return result

    def check_if_need_build(self, group:str='DEBUG'):
        '''
            Check and set `need_build` variable
        '''

        def _need_build(target:Target) -> bool:
            '''
                If target file not exists or prerequisites files newer than target
            '''
            if not os.path.exists(target.path):
                return True
            target_time = os.path.getmtime(target.path)

            for prq in target.prerequisites:
                if not group in prq.parent.config.GROUPS:
                    continue
                if os.path.exists(prq.path):
                    prq_time = os.path.getmtime(prq.path)
                    if prq_time > target_time:
                        return True
                else:
                    return True
            return False

        def _set_parents_need_build(target : Target):
            '''
                Set all parents `need_build` recursive
            '''
            parents = self.find_targets_contains_prerequisite(target)
            for par in parents:
                par.need_build = True
                _set_parents_need_build(par)

        # check if children rebuilds, so parents need rebuild too
        for target in self.targets_recursive.targets:
            if not target.need_build and _need_build(target):
                target.need_build = True
                _set_parents_need_build(target)

    def get_build_layers(self, group:str='DEBUG') -> list[list[Target]]:
        '''
            Return list of layers. Layer is bunch of targets that can be built parralel
        '''
        self.load_targets_recursive(group)
        self.check_if_need_build(group)

        # remove targets that not need to build
        torem = []
        for target in self.targets_recursive.targets:
            if not target.need_build:
                torem.append(target)
        for target in torem:
            self.targets_recursive.targets.remove(target)

        def _pop_layer() -> list[Target]:
            '''
                Return targets that can be built right now.
                If all prerequisites not need to build then we can build this target.
                So, these targets we can build parallel -> in one layer
            '''
            layer : set[Target] = set()
            for target in self.targets_recursive.targets:
                for prq in target.prerequisites:
                    if prq.need_build:
                        break
                else:
                    layer.add(target)

            return list(layer)

        result : list[list[Target]] = []

        layer = _pop_layer()
        while(len(layer) > 0):
            for target in layer:
                self.targets_recursive.targets.remove(target)
                target.need_build = False
            result.append(layer)
            layer = _pop_layer()
        return result

    def load(self):
        '''
            Load project variables, init subproject's configs
        '''
        self.main_target = None
        self.targets.targets = []
        self.targets_recursive.targets = []
        self.load_subprojects()

        if not self.config.OUT_FILE:
            raise Exceptions.OutFileEmpty()

        # Setup default variables in config
        if not self.config.INCLUDE_DIRS:
            self.config.INCLUDE_DIRS = self.config.SRC_DIRS
        if not self.config.EXPORT_INCLUDE_DIRS:
            self.config.EXPORT_INCLUDE_DIRS = self.config.INCLUDE_DIRS

        # Add exporting defines to defines
        self.config.DEFINES.extend(self.config.EXPORT_DEFINES)

        # Set absolute paths
        def _set_abs(l:list[str]):
            for i in range(len(l)):
                l[i] = os.path.abspath(l[i])

        _set_abs(self.config.INCLUDE_DIRS)
        _set_abs(self.config.EXPORT_INCLUDE_DIRS)

        # Looking for sources, exclude specified source files
        self.config.SOURCES += find_files(self.config.SRC_DIRS, self.config.SRC_EXTS)
        self.config.SOURCES += find_files(self.config.SRC_RECURSIVE_DIRS, self.config.SRC_EXTS, recursive=True)
        self.config.EXCLUDE_SOURCES = [os.path.abspath(x) for x in self.config.EXCLUDE_SOURCES]
        self.config.SOURCES = [x for x in self.config.SOURCES if x not in self.config.EXCLUDE_SOURCES]
        self.config.LIB_DIRS = [os.path.abspath(x) for x in self.config.LIB_DIRS]

        '''
            Create targets from sources.
            All object files must be in OBJ directory
            if source path is relative and contain `../`
            so it will be replaces by 'updir/' this allow stay in OBJ folder
        '''
        object_targets = []
        deps = []
        for src in self.config.SOURCES:
            path = self.config.OBJ_PATH + "/" + os.path.relpath(src).replace('../','updir/')
            spl = os.path.splitext(path)
            obj = f"{spl[0]}.o"
            dep = f"{spl[0]}.d"
            deps.append(dep)
            src_target = self.targets.add(Target(src,[],self))
            obj_target = self.targets.add(Target(obj,[src_target],self))
            object_targets.append(obj_target)

        # Main target
        self.main_target = self.targets.add(Target(self.config.OUT_FILE,object_targets,self))

        # Load targets from .d files if they present
        for d in deps:
            self.get_targets_from_d_file(d)

        '''
            Load data from subprojects
            chdir is for right abspath work
        '''
        for sp in self.subprojects:
            os.chdir(sp.cwd)
            sp_path = os.path.abspath(sp.config.OUT_FILE)
            self.main_target.prerequisites.append(sp.main_target)
            fname = os.path.basename(sp.config.OUT_FILE)

            # Pass export defines up
            self.config.EXPORT_DEFINES.extend(sp.config.EXPORT_DEFINES)

            # Accept exported defines
            self.config.PRIVATE_DEFINES.extend(sp.config.EXPORT_DEFINES)

            # Pass defines to children
            sp.config.DEFINES.extend(self.config.DEFINES)

            # Override CFLAGS if set in main target
            if self.main_target.parent.config.OVERRIDE_CFLAGS:
                sp.config.CFLAGS = self.main_target.parent.config.CFLAGS

            self.config.LIBS.extend(sp.config.LIBS)
            self.config.LIB_DIRS.extend(sp.config.LIB_DIRS)

            self.config.PKG_SEARCH.extend(sp.config.PKG_SEARCH)

            # Libraries
            if fname.startswith('lib') and fname.endswith('.a'):
                lib = fname[3:-2]
                self.config.LIBS.insert(0,lib)
                self.config.LIB_DIRS.append(os.path.dirname(sp_path))
                spe = [os.path.abspath(x) for x in sp.config.EXPORT_INCLUDE_DIRS]
                self.config.INCLUDE_DIRS.extend(spe)
            os.chdir(self.cwd)

        # Load libs data from pkg-config
        unique_list(self.config.PKG_SEARCH)
        if self.config.PKG_SEARCH:
            out = sh_capture(["pkg-config","--cflags","--libs"]+list(self.config.PKG_SEARCH))
            if not out.startswith('-'):
                if "command not found" in out:
                    app_logger.error(color_text(31,f"Project {self.cwd}: PKG_SEARCH present, but pkg-config not found"))
                if "No package" in out:
                    app_logger.error(color_text(31,f"Project {self.cwd}: {out}"))
            else:
                out = out.replace('\n','')
                spl = out.split(' ')
                self.config.INCLUDE_FLAGS.extend([x for x in spl if x.startswith('-I')])
                self.config.LIB_DIRS_FLAGS.extend([x for x in spl if x.startswith('-L')])
                self.config.LIBS_FLAGS.extend([x for x in spl if x.startswith('-l')])

    def load_targets_recursive(self, group:str='DEBUG'):
        '''
            Load all subproject targets recursive
        '''
        def _get_targets(p:Project) -> TargetContainer:
            result = TargetContainer()
            for prj in p.subprojects:
                targs = _get_targets(prj)
                for t in targs.targets:
                    if group in t.parent.config.GROUPS:
                        result.add(t)

            if group in p.config.GROUPS:
                result.add_from_container(p.targets)
            return result

        self.targets_recursive.add_from_container(_get_targets(self))

    def load_subprojects(self):
        '''
            We are loading the subproject data by executing `config` function
            inside `build.py`
        '''
        self.subprojects = []

        for sp in self.config.SUBPROJECTS:
            sp_abs = os.path.abspath(sp)
            self.tmp_config = None
            try:
                orig_dir = os.getcwd()
                os.chdir(sp_abs)

                with open(sp_abs+"/"+"build.py") as f:
                    exec(f.read()+'\nself.tmp_config = config()',
                        {
                            '__file__':f'{sp_abs}/build.py',
                            'mapyr':sys.modules[__name__],
                        },
                        {
                            'self':self,
                        })
                if self.tmp_config is None:
                    RuntimeError('config load failed!')

                subprojects = [Project(x) for x in self.tmp_config]
                for p in subprojects:
                    p.load()
                os.chdir(orig_dir)
                self.subprojects.extend(subprojects)

            except Exception as e:
                app_logger.error(color_text(31,f"Subproject {sp}: {e}"))
                continue

    def build(self, group:str='DEBUG') -> bool:
        '''
            Build project
        '''
        self.load()
        layers = self.get_build_layers(group)

        if not layers:
            app_logger.info('Nothing to build')
            return True

        for layer in layers:
            layer : list[Target]

            # create directories
            for t in layer:
                os.makedirs(os.path.dirname(t.path),exist_ok=True)

            error = False
            problem_task = None
            with concurrent.futures.ProcessPoolExecutor(max_workers=self.config.MAX_THREADS_NUM) as executor:
                builders = [executor.submit(t.build) for t in layer]
                for i in range(len(builders)):
                    if builders[i].result() != 0:
                        error = True
                        problem_task=layer[i]
                        break
                if error:
                    break
        if not error:
            app_logger.info(color_text(32,'Done'))
            return True
        else:
            name = os.path.relpath(problem_task.path)
            app_logger.error(color_text(91,f'{name}: Error. Stopped.'))
            return False

    def clean(self, group:str='DEBUG'):
        self.load_subprojects()
        for sp in self.subprojects:
            os.chdir(sp.cwd)
            sp.clean(group)
            os.chdir(self.cwd)

        if not group in self.config.GROUPS:
            return

        shutil.rmtree(self.config.OBJ_PATH,True)
        dirs = os.path.dirname(self.config.OUT_FILE)
        silentremove(self.config.OUT_FILE)
        if dirs:
            shutil.rmtree(dirs,True)

    def run(self):
        self.build()
        sh(self.config.OUT_FILE)

    def __repr__(self) -> str:
        return self.config.OUT_FILE

#----------------------END PROJECT---------------------

def build(pc:list[ProjectConfig],group):
    vscode_config_need = False
    projects : list[Project] = []
    for p in pc:
        if group not in p.GROUPS:
            continue
        prj = Project(p)
        projects.append(prj)
        prj.build(group)
        if p.VSCODE_CPPTOOLS_CONFIG:
            vscode_config_need = True

    # VSCode c_cpp_properties generating
    if vscode_config_need == False:
        return

    vscode_file_path = '.vscode/c_cpp_properties.json'
    if os.path.exists(vscode_file_path):
        import inspect
        build_py_filename = inspect.stack()[2].filename
        if os.path.getmtime(build_py_filename) <= os.path.getmtime(vscode_file_path):
            return

    configs = []
    for p in projects:
        if p.config.VSCODE_CPPTOOLS_CONFIG:
            config = {
                'name':p.config.OUT_FILE,
                'includePath':p.config.INCLUDE_DIRS,
                'defines':p.config.PRIVATE_DEFINES + p.config.DEFINES
            }
            configs.append(config)

    if configs:
        main_config = {
            'configurations':configs,
            "version": 4
        }

        with open('.vscode/c_cpp_properties.json', 'w+') as f:
            json.dump(main_config, f, indent=4)

def process():
    '''
        Runs Mapyr.
        Complicated algorythm for not inflate footer block in build.py
        and save it untouched from version to version.
        Loads parent build.py as python code, add injection code and
        run it again to fetch configs
   '''

    fetch = '''
vars.config = config()
if 'tool_config' in dir():
    vars.tool_config = tool_config()
'''

    parent_file = os.path.realpath(sys.argv[0])
    class _vars:
        config : list[ProjectConfig] = []
        tool_config : ToolConfig = ToolConfig()
    vars = _vars()
    try:
        with open(parent_file) as f:
            exec(f.read()+fetch,
                {
                    '__file__':parent_file,
                    'mapyr':sys.modules[__name__],
                },
                {
                    'vars':vars
                })
        if not vars.config:
            RuntimeError('config load failed!')

    except Exception as e:
        setup_logger(vars.tool_config)
        app_logger.error(color_text(31,f"{e}"))
        return

    setup_logger(vars.tool_config)
    if vars.tool_config.MINIMUM_REQUIRED_VERSION > VERSION:
        app_logger.warning(color_text(31,f"Required version {vars.tool_config.MINIMUM_REQUIRED_VERSION} is higher than running {VERSION}!"))

    os.chdir(os.path.dirname(parent_file))
    group = 'DEBUG'
    cmd = 'build'
    if len(sys.argv)>1:
        cmd = sys.argv[1]
        if len(sys.argv) > 2:
            group = sys.argv[2]

    match(cmd):
        case 'name':    print(vars.config[0].OUT_FILE)
        case 'run':     Project(vars.config[0]).run()
        case 'build':   build(vars.config,group)

        case 'clean':
            for p in vars.config:
                Project(p).clean(group)

