import sys
import os
import shutil
import subprocess
import concurrent.futures
import logging

VERSION = '0.4'

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
file_formatter = logging.Formatter('%(asctime)-15s|PID:%(process)-11s|%(levelname)-8s|%(filename)s:%(lineno)s| %(message)s')
console_formatter = logging.Formatter('[%(levelname)s]: %(message)s')

file_path = f"{os.path.dirname(os.path.realpath(__file__))}/debug.log"
file_handler = logging.FileHandler(file_path,'w',encoding='utf8')
file_handler.setFormatter(file_formatter)

console_handler = logging.StreamHandler()
verb = os.getenv('VERBOSITY')
if verb and verb.isdigit():
    console_handler.setLevel(int(verb))
else:
    console_handler.setLevel(logging.INFO)
console_handler.setFormatter(console_formatter)

rootlog = logging.getLogger()
rootlog.addHandler(file_handler)

app_logger = logging.getLogger('main')
app_logger.propagate = False
app_logger.setLevel(logging.DEBUG)
app_logger.addHandler(file_handler)
app_logger.addHandler(console_handler)

# Color text Win/Lin
if os.name == 'nt':
    def color_text(color,text):
        return f"[{color}m{text}[0m"
else:
    def color_text(color, text):
        return f"\033[{color}m{text}\033[0m"

#----------------------LOGGING-------------------------

#----------------------UTILS---------------------------
def find_files(dirs:list[str], exts:list[str]) -> list[str]:
    '''
        Search files with extensions listed in `exts` 
        in directories listed in `dirs` not recursive
    '''
    result = []
    for dir in dirs:
        if not os.path.exists(dir):
            continue
        for file in os.listdir(dir):
            filepath = f'{dir}/{file}'
            if os.path.isfile(filepath):
                if os.path.splitext(file)[1] in exts:
                    result.append(os.path.abspath(filepath))
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
            obj = [x.path for x in self.prerequisites if x.path.endswith('.o')]
            cmd = [p.config.COMPILER]+p.config.LIB_DIRS_FLAGS+obj+['-o',self.path]+p.config.LIBS_FLAGS
            return Command(self, cmd, Command.mfLinkExe)

        def _cmd_link_static() -> Command:
            obj = [x.path for x in self.prerequisites if x.path.endswith('.o')]
            cmd = [p.config.AR]+[''.join(p.config.AR_FLAGS)]+[self.path]+obj
            return Command(self, cmd, Command.mfLinkStatic)
        
        def _cmd_build_c(source) -> Command:
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
                    app_logger.info(f'{self.path} size {new_size} {f"[{diff(old_size,new_size)}]" if old_size else ""}')

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
class ProjectConfig:
    def __init__(self) -> None:
        self.OUT_FILE : str = ""
        '''
            Path and name of output file. 
            This defines build type: exe, static, shared or other... 
        '''
        
        self.GROUPS : list[str] = ['DEBUG']
        '''
            A project can belong to several groups. Default group is DEBUG
            When Mapyrfile started without arguments, it runs build DEBUG group
        '''

        self.COMPILER : str = "clang"
        '''
            Compiler command 
        '''

        self.OBJ_PATH               : str = "obj"
        '''
            Path where object files will be
        '''

        self.AR                     : str = "ar"
        '''
            Archiver command
        '''

        self.SRC_EXTS               : list[str] = [".cpp",".c"]
        '''
            Source extensions for search them in `SRC_DIRS`
        '''

        self.SRC_DIRS               : list[str] = ["src"]
        '''
            Source directories for NOT recursive search
        '''

        self.SRC_RECURSIVE_DIRS     : list[str] = []
        '''
            Source directories for recursive search
        '''
        
        self.INCLUDE_DIRS           : list[str] = []
        '''
            Private include directories
        '''
        
        self.EXPORT_INCLUDE_DIRS    : list[str] = []
        '''
            Include directories that also will be sended to parent project
            and parent will include them while his building process 
        '''
        
        self.AR_FLAGS               : list[str] = ["r","c","s"]
        '''
            Archiver flags 
        '''

        self.CFLAGS                 : list[str] = ["-O3"]
        '''
            Compile flags
        '''

        self.SUBPROJECTS            : list[str] = []
        '''
            Paths to directories contains Mapyrfile.
            If subproject is library, it will automatic included as library in the project.
        '''
        
        self.LIB_DIRS               : list[str] = []
        '''
            Directories where looking for libraries
        '''

        self.LIBS                   : list[str] = []
        '''
            List of libraries
        '''
        
        self.INCLUDE_FLAGS          : list[str] = []
        '''
            Flags that will passed to compiler in include part of command.
            This is automatic variable, but you can add any flag if needed
        '''
        
        self.LIB_DIRS_FLAGS         : list[str] = []
        '''
            Flags that will passed to linker in library directories part of command.
            This is automatic variable, but you can add any flag if needed
        '''
       
        self.LIBS_FLAGS             : list[str] = []
        '''
            Flags that will passed to linker in library part of command.
            This is automatic variable, but you can add any flag if needed
        '''

        self.PKG_SEARCH             : list[str] = []
        '''
            If `pkg-config` installed in system, so this libraries will be auto included in project 
        '''

        self.SOURCES                : list[str] = []
        '''
            Particular source files. 
            This is automatic variable, but you can add any flag if needed
        '''

        self.EXCLUDE_SOURCES        : list[str] = []
        '''
            Sometimes need to exclude specific source file from auto search
            Add path to source in relative or absolute format
        '''

        self.DEFINITIONS            : list[str] = []
        '''
            Private definitions, that will be used only in this project
        '''
        
        self.EXPORT_DEFINITIONS     : list[str] = []
        '''
            Definitions that used in the project and also will be passed to parent project
        '''
        
        self.MAX_THREADS_NUM        : int = 10
        '''
            Build threads limit
        '''

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
            if 'libgrid.a' in target.path:
                pass
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
                _set_parents_need_build(par.path)

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

        # Looking for sources, exclude specified source files
        self.config.SOURCES += find_files(self.config.SRC_DIRS, self.config.SRC_EXTS)
        self.config.EXCLUDE_SOURCES = [os.path.abspath(x) for x in self.config.EXCLUDE_SOURCES]
        self.config.SOURCES = [x for x in self.config.SOURCES if x not in self.config.EXCLUDE_SOURCES]
        
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
            self.config.DEFINITIONS.extend(sp.config.EXPORT_DEFINITIONS)
            self.config.LIBS.extend(sp.config.LIBS)
            self.config.LIB_DIRS.extend(sp.config.LIB_DIRS)
            
            # Libraries
            if fname.startswith('lib') and fname.endswith('.a'):
                lib = fname[3:-2]
                self.config.LIBS.insert(0,lib)
                self.config.LIB_DIRS.append(os.path.dirname(sp_path))
                spe = [os.path.abspath(x) for x in sp.config.EXPORT_INCLUDE_DIRS]
                self.config.INCLUDE_DIRS.extend(spe)
            os.chdir(self.cwd)

        # prepare flags
        self.config.INCLUDE_FLAGS     = unique_list([f"-I{x}" for x in self.config.INCLUDE_DIRS])
        self.config.LIB_DIRS_FLAGS    = unique_list([f"-L{x}" for x in self.config.LIB_DIRS])
        self.config.LIBS_FLAGS        = unique_list([f"-l{x}" for x in self.config.LIBS])
        self.config.CFLAGS.extend([f"-D{x}" for x in self.config.DEFINITIONS])
        self.config.CFLAGS = unique_list(self.config.CFLAGS)

        # Load libs data from pkg-config
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
                if not group in prj.config.GROUPS:
                    continue
                result.add_from_container(targs)
            
            if group in p.config.GROUPS:
                result.add_from_container(p.targets)
            return result
        
        self.targets_recursive.add_from_container(_get_targets(self))

    def load_subprojects(self):
        '''
            We are loading the subproject data by executing `config` function 
            inside `Mapyrfile`
        '''
        self.subprojects = []
        
        for sp in self.config.SUBPROJECTS:
            sp_abs = os.path.abspath(sp)
            self.tmp_config = None
            try:
                with open(sp_abs+"/"+"Mapyrfile") as f:
                    exec(f.read()+'\nself.tmp_config = config()',None,{'self':self})
                if self.tmp_config is None:
                    RuntimeError('config load failed!')
                
                orig_dir = os.getcwd()
                os.chdir(sp_abs)
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
    
def process(pc:list[ProjectConfig]):
    os.chdir(os.path.dirname(sys.argv[0]))
    group = 'DEBUG'
    cmd = 'build'
    if len(sys.argv)>1:
        cmd = sys.argv[1]
        if len(sys.argv) > 2:
            group = sys.argv[2]

    match(cmd):
        case 'name':    print(pc[0].OUT_FILE)
        case 'run':     Project(pc[0]).run()
        case 'build':
            for p in pc:
                Project(p).build(group)

        case 'clean': 
            for p in pc:
                Project(p).clean(group)