import sys
import os
import shutil
import subprocess
import concurrent.futures

#----------------------EXCEPTIONS----------------------
class Exceptions:
    class CustomException(Exception):
        def __init__(self): super().__init__(self.__doc__)
    
    class CircularDetected(CustomException):
        "Circular dependency detected!"
    class OutFileEmpty(CustomException):
        "Variable: OUT_FILE empty!"
#----------------------END EXCEPTIONS------------------

#----------------------UTILS---------------------------
def find_files_recursive(dirs:list[str], exts:list[str]) -> list[str]:
    result = []
    for dir in dirs:
        if not os.path.exists(dir):
            continue
        for folder, _, files in os.walk(dir):
            for file in files:
                filepath = f"{folder}/{file}"
                if os.path.splitext(file)[1] in exts:
                    result.append(os.path.abspath(filepath))
    return result

def find_files(dirs:list[str], exts:list[str]) -> list[str]:
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
    return subprocess.Popen(cmd).wait()

def sh_capture(cmd: list[str]) -> str:
    run = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout,stderr = run.communicate()
    run.wait()
    if len(stderr) > 0:
        return stderr.decode()
    return stdout.decode()

def silentremove(filename):
    try:
        os.remove(filename)
    except FileNotFoundError:
        pass
    
#----------------------END UTILS-----------------------

#----------------------TARGET--------------------------
class Target:
    def __init__(self, path:str, preqs : list[str], parent:"Project", need_build:bool=False) -> None:
        self.path           : str           =  os.path.abspath(path)
        self.prerequisites  : list[str]     = [os.path.abspath(p) for p in preqs]
        self.parent         : Project       = parent
        self.need_build     : bool          = need_build
    
    def __repr__(self) -> str:
        return f'{self.path}:{self.prerequisites}'

class TargetManager:
    def __init__(self, parent:"Project") -> None:
        self.targets : list[Target] = []
        self.parent  : Project      = parent

    def add(self, t:Target):
        found = self.find(t.path)
        if found is not None:
            #found.prerequisites = t.prerequisites
            found.prerequisites.extend(t.prerequisites)
        else:
            self.targets.append(t)

    def find(self, path: str) -> Target:
        path = os.path.abspath(path)

        for t in self.targets:
            if path == t.path:
                return t        
        return None
    
    def find_contains_prerequisite(self,path:str) -> list[Target]:
        path = os.path.abspath(path)

        result=[]
        for target in self.targets:
            if path in target.prerequisites:
                result.append(target)
        return result

    def get_from_d_file(self, path : str):
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
            spl = line.split(':')
            if len(spl) < 2:
                continue

            prerequisites = spl[1].split(' ')
            path = os.path.abspath(spl[0])
            preq : list[str] = []
            for prq in prerequisites:
                if prq != '':
                    preq.append(os.path.abspath(prq))
            
            self.add(Target(path,preq,self.parent))

    def check_if_need_build(self):
        # reset all states
        for target in self.targets:
            target.need_build = False

        # at first check files
        def _need_build(target:Target) -> bool:
            if not os.path.exists(target.path):
                return True
            target_time = os.path.getmtime(target.path)

            for prq in target.prerequisites:
                if os.path.exists(prq):
                    prq_time = os.path.getmtime(prq)
                    if prq_time > target_time:
                        return True
                else:
                    return True
            return False        

        def _set_parents_need_build(path : str):
            parents = self.find_contains_prerequisite(path)
            for par in parents:
                par.need_build = True
                _set_parents_need_build(par.path)

        # next check if children rebuilds, so parents need rebuild too
        for target in self.targets:
            if _need_build(target):
                target.need_build = True
                _set_parents_need_build(target.path)

    def get_build_layers(self) -> list[list[Target]]:
        self.check_if_need_build()
        
        # Copying targets
        local_targets : list[Target] = []
        for target in self.targets:
            local_targets.append(Target(target.path,target.prerequisites.copy(),self.parent,target.need_build))

        def _prerequisites_in_targets(target:Target):
            for prq in target.prerequisites:
                for t in local_targets:
                    if t.path == prq:
                        return True
            return False

        def _remove(t:Target):
            for target in local_targets:
                if t.path in target.prerequisites:
                    target.prerequisites.remove(t.path)
            local_targets.remove(t)

        def _pop_layer():
            torem = []
            for target in local_targets:
                if not target.need_build:
                    torem.append(target)

            for t in torem:
                _remove(t)

            layer : set[Target] = set()
            for target in local_targets:
                if not _prerequisites_in_targets(target):
                    layer.add(target)
            
            for t in layer:
                _remove(t)

            return list(layer)
        
        # form list of compile layers
        result : list[list[Target]] = []

        layer = _pop_layer()
        while(len(layer) > 0):
            result.append(layer)
            layer = _pop_layer()
        return result

#----------------------END TARGET----------------------

#----------------------PROJECT--------------------------
class ProjectConfig:
    def __init__(self) -> None:
        self.OUT_FILE               : str = ""
        self.COMPILER               : str = "clang"
        self.OBJ_PATH               : str = "obj"
        self.AR                     : str = "ar"
        self.SRC_EXTS               : list[str] = [".cpp",".c"]
        self.SRC_DIRS               : list[str] = ["src"]
        self.SRC_RECURSIVE_DIRS     : list[str] = []
        self.INCLUDE_DIRS           : list[str] = []
        self.EXPORT_INCLUDE_DIRS    : list[str] = []
        self.AR_FLAGS               : list[str] = ["r","c","s"]
        self.CFLAGS                 : list[str] = ["-O3"]
        self.SUBPROJECTS            : list[str] = []
        self.LIB_DIRS               : list[str] = []
        self.LIBS                   : list[str] = []
        self.INCLUDE_FLAGS          : list[str] = []
        self.LIB_DIRS_FLAGS         : list[str] = []
        self.LIBS_FLAGS             : list[str] = []
        self.PKG_SEARCH             : list[str] = []
        self.SOURCES                : list[str] = []
        self.EXCLUDE_SOURCES        : list[str] = []
        self.EXPORT_DEFINITIONS     : list[str] = []
        self.DEFINITIONS            : list[str] = []

        self.MAX_THREADS_NUM        : int = 10

class Project:
    def __init__(self, config:ProjectConfig) -> None:
        self.target_man = TargetManager(self)
        self.config : ProjectConfig = config
        self.subprojects : list[Project] = []
        self.cwd : str = os.getcwd()

        self.reload_subprojects()
        self.prepare()

    def prepare(self):
        if not self.config.OUT_FILE:
            raise Exceptions.OutFileEmpty()

        # default vars in config
        if not self.config.INCLUDE_DIRS:
            self.config.INCLUDE_DIRS = self.config.SRC_DIRS
        if not self.config.EXPORT_INCLUDE_DIRS:
            self.config.EXPORT_INCLUDE_DIRS = self.config.INCLUDE_DIRS

        # default sources targets 
        self.config.SOURCES += find_files(self.config.SRC_DIRS, self.config.SRC_EXTS)
        self.config.EXCLUDE_SOURCES = [os.path.abspath(x) for x in self.config.EXCLUDE_SOURCES]
        self.config.SOURCES = [x for x in self.config.SOURCES if x not in self.config.EXCLUDE_SOURCES]
        objects = []
        deps = []
        for src in self.config.SOURCES:
            path = self.config.OBJ_PATH + "/" + os.path.relpath(src).replace('../','updir/')
            spl = os.path.splitext(path)
            obj = f"{spl[0]}.o"
            dep = f"{spl[0]}.d"
            objects.append(obj)
            deps.append(dep)
            self.target_man.add(Target(obj,{src},self))

        # default out file target
        main_target = Target(self.config.OUT_FILE,set(objects),self)
        self.target_man.add(main_target)

        # load targets from .d files if they present
        for d in deps:
            self.target_man.get_from_d_file(d)

        # subprojects
        for sp in self.subprojects:
            os.chdir(sp.cwd)
            sp_path = os.path.abspath(sp.config.OUT_FILE)
            main_target.prerequisites.append(sp_path)
            fname = os.path.basename(sp.config.OUT_FILE)
            self.config.DEFINITIONS.extend(sp.config.EXPORT_DEFINITIONS)
            self.config.LIBS.extend(sp.config.LIBS)
            self.config.LIB_DIRS.extend(sp.config.LIB_DIRS)
            if fname.startswith('lib') and fname.endswith('.a'):
                lib = fname[3:-2]
                self.config.LIBS.append(lib)
                self.config.LIB_DIRS.append(os.path.dirname(sp_path))
                spe = [os.path.abspath(x) for x in sp.config.EXPORT_INCLUDE_DIRS]
                self.config.INCLUDE_DIRS.extend(spe)
            os.chdir(self.cwd)

        # prepare flags
        self.config.INCLUDE_FLAGS     = [f"-I{x}" for x in self.config.INCLUDE_DIRS]
        self.config.LIB_DIRS_FLAGS    = [f"-L{x}" for x in self.config.LIB_DIRS]
        self.config.LIBS_FLAGS        = [f"-l{x}" for x in self.config.LIBS]
        self.config.CFLAGS.extend([f"-D{x}" for x in self.config.DEFINITIONS])

        # pkg-config
        if self.config.PKG_SEARCH:
            out = sh_capture(["pkg-config","--cflags","--libs"]+list(self.config.PKG_SEARCH))
            if not out.startswith('-'):
                if "command not found" in out:
                    print(color_text(31,f"Project {self.cwd}: PKG_SEARCH present, but pkg-config not found"))
                if "No package" in out:
                    print(color_text(31,f"Project {self.cwd}: {out}"))
            else:
                out = out.replace('\n','')
                spl = out.split(' ')
                self.config.INCLUDE_FLAGS.extend([x for x in spl if x.startswith('-I')])
                self.config.LIB_DIRS_FLAGS.extend([x for x in spl if x.startswith('-L')])
                self.config.LIBS_FLAGS.extend([x for x in spl if x.startswith('-l')])

    def reload_subprojects(self):
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
                np = Project(self.tmp_config)
                os.chdir(orig_dir)
                self.subprojects.append(np)
            
            except Exception as e:
                print(color_text(31,f"Subproject {sp}: {e}"))
                continue

    def get_build_layers(self) -> list[list[str]]:        
        # load all subproject targets recursive
        def get_targets(p:Project): 
            for prj in p.subprojects:
                targets = get_targets(prj)
                for target in targets:
                    if not p.target_man.find(target.path):
                        p.target_man.add(target)

            return p.target_man.targets
        
        get_targets(self)
        result = self.target_man.get_build_layers()
        return result

#----------------------END PROJECT---------------------
    
#----------------------BUILD PROCESS-------------------
# Color text Win/Lin
if os.name == 'nt':
    def color_text(color,text):
        return f"[{color}m{text}[0m"
else:
    def color_text(color, text):
        return f"\033[{color}m{text}\033[0m"

def sh(cmd: list[str]) -> int:
    return subprocess.Popen(cmd).wait()

def build_c(source:str, obj:str, p:Project) -> int:
    print(f"{color_text(94,'Building')}: {os.path.relpath(obj)}")    
    os.makedirs(os.path.dirname(obj),exist_ok=True)
    basename = os.path.splitext(obj)[0]
    depflags = ['-MT',obj,'-MMD','-MP','-MF',f"{basename}.d"]
    cmd = [p.config.COMPILER]+depflags + p.config.CFLAGS
    cmd += p.config.INCLUDE_FLAGS +['-c','-o',obj,source]
    return sh(cmd)

def get_size(path:str) -> int:
    if os.path.exists(path):
        return os.stat(path).st_size
    return -1

def diff(old:int, new:int) -> str:
    diff = new - old
    summstr = '0'
    if diff > 0:
        summstr = color_text(31,f'+{diff}')
    if diff < 0:
        summstr = color_text(32,f'{diff}')
    return summstr

def link(cmd:list[str], out:str, print_size=False):
    os.makedirs(os.path.dirname(out),exist_ok=True)
    old_size = 0
    if os.path.exists(out):
        old_size=os.stat(out).st_size

    code = sh(cmd)
    
    if code == 0:
        if print_size:
            new_size=os.stat(out).st_size
            print(f'{out} size {new_size} {f"[{diff(old_size,new_size)}]" if old_size else ""}')

    return code

def link_exe(out:str, objects:list[str], p:Project) -> int:
    print(f"{color_text(32,'Linking executable')}: {os.path.relpath(out)}")
    cmd = [p.config.COMPILER]+p.config.LIB_DIRS_FLAGS+objects+['-o',out]+p.config.LIBS_FLAGS
    return link(cmd,out)

def link_static(out:str, objects:list[str], p:Project) -> int:
    print(f"{color_text(33,'Linking static')}: {os.path.relpath(out)}")
    cmd = [p.config.AR]+[''.join(p.config.AR_FLAGS)]+[out]+objects
    return link(cmd,out)

def build_target(t:Target) -> int:
    for prq in t.prerequisites:
        match(os.path.splitext(prq)[1]):
            case '.c': return build_c(prq, t.path, t.parent)
    
    target = t.parent.target_man.find(t.path)
    match(os.path.splitext(target.path)[1]):
        case '' | '.exe': return link_exe(target.path,target.prerequisites,t.parent)
        case '.a': return link_static(target.path,target.prerequisites,t.parent)

    print(f"{color_text(91,'Not found builder for')}: {os.path.relpath(t.path)}")
    return 1

def build(p:Project):
    layers = p.get_build_layers()
    if not layers:
        print('Nothing to build')
        return
    
    for layer in layers:
        layer : list[Target]

        error = False
        with concurrent.futures.ProcessPoolExecutor(max_workers=p.config.MAX_THREADS_NUM) as executor:
            builders = [executor.submit(build_target,t) for t in layer]
            for builder in builders:
                if builder.result() != 0:
                    error = True
                    break
            if error:
                break
    if not error:
        print(color_text(32,'Done'))
    else:
        print(color_text(91,'Error. Stopped.'))
#----------------------END BUILD PROCESS---------------

def clean(p:Project):
    for sp in p.subprojects:
        os.chdir(sp.cwd)
        clean(sp)
        os.chdir(p.cwd)

    shutil.rmtree(p.config.OBJ_PATH,True)
    dirs = os.path.dirname(p.config.OUT_FILE)
    silentremove(p.config.OUT_FILE)
    if dirs:
        shutil.rmtree(dirs,True)

def process(pc:ProjectConfig):
    if len(sys.argv)>1:
        for arg in sys.argv:
            match(arg.lower()):
                case 'name':    print(pc.OUT_FILE)
                case 'run':     sh(pc.OUT_FILE)
                case 'build':   build(Project(pc))
                case 'clean':   clean(Project(pc))
    else:
        build(Project(pc))