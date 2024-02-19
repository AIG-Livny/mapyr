import os
import subprocess
import concurrent.futures

class Exceptions:
    class CustomException(Exception):
        def __init__(self): super().__init__(self.__doc__)
    
    class CircularDetected(CustomException):
        "Circular dependency detected!"
    class OutFileEmpty(CustomException):
        "Variable: OUT_FILE empty!"

def find_files_recursive(dirs:list[str], exts:list[str]) -> list[str]:
    result = []
    for dir in dirs:
        for folder, _, files in os.walk(dir):
            for file in files:
                filepath = f"{folder}/{file}"
                if os.path.splitext(file)[1] in exts:
                    result.append(os.path.abspath(filepath))
    return result

def find_files(dirs:list[str], exts:list[str]) -> list[str]:
    result = []
    for dir in dirs:
        for file in os.listdir(dir):
            filepath = f'{dir}/{file}'
            if os.path.isfile(filepath):
                if os.path.splitext(file)[1] in exts:
                    result.append(os.path.abspath(filepath))
    return result

class Target:
    def __init__(self, path:str, preqs : set[str]) -> None:
        self.path : str =  os.path.abspath(path)
        self.prerequisites : set[str] = {os.path.abspath(p) for p in preqs}
    
    def __repr__(self) -> str:
        return f'{self.path}:{self.prerequisites}'

class TargetManager:
    def __init__(self) -> None:
        self.targets : list[Target] = []

    def add(self, t:Target):
        found = self.find(t.path)
        if found is not None:
            found.prerequisites = t.prerequisites
            #found.prerequisites.update(t.prerequisites)
        else:
            self.targets.append(t)

    def find(self, rule: str) -> Target:
        rule = os.path.abspath(rule)

        # at first search exact rule
        for t in self.targets:
            if rule == t.path:
                return t        
        return None
    
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
            preq : set[str] = set()
            for prq in prerequisites:
                if prq != '':
                    preq.add(os.path.abspath(prq))
            
            self.add(Target(path,preq))


    def need_build(self, path) -> bool:
        '''
            Returns True if this target need to build
        '''
        def _need_build(_path:str):
            if not os.path.exists(_path):
                return True

            target = self.find(_path)
            if not target:
                return False

            target_time = os.path.getmtime(target.path)

            for prq in target.prerequisites:
                # start recursive
                if _need_build(prq):
                    return True

                if os.path.exists(prq):
                    prq_time = os.path.getmtime(prq)
                    if prq_time > target_time:
                        return True
                else:
                    return True
            return False
        return _need_build(path)

    def get_build_layers(self) -> list[list[Target]]:
        '''
            Returns targets that need to compile
            separated by layers of dependency/
            Each layer has independent objects, 
            that can be compiled in parallel
        '''
        local_targets : list[Target] = []
        for target in self.targets:
            local_targets.append(Target(target.path,target.prerequisites.copy()))
        
        def remove_local_prereqs(t:Target):
            for target in local_targets:
                if t.path in target.prerequisites:
                    target.prerequisites.remove(t.path)
            

        # remove not buildable
        torem = []
        for target in local_targets:
        
            try:
                if not self.need_build(target.path):
                    remove_local_prereqs(target)
                    torem.append(target)

            except Exceptions.CircularDetected as e:
                print(f'{target.path}: {e} : will be passed')
                continue
        
        for t in torem:
            local_targets.remove(t)

        def get_lower_nodes() -> list[Target]:
            # Empty prerequisits and those who have preqs not found in targets
            lower_nodes : list[Target] = []    
            for target in local_targets:
                if not target.prerequisites:
                    lower_nodes.append(target)
                    continue
                else:
                    for prq in target.prerequisites:
                        if not self.find(prq):
                            lower_nodes.append(target)
                            break

            # Remove from prerequisites upper nodes
            for node in lower_nodes:
                remove_local_prereqs(node)
                local_targets.remove(node)

            return lower_nodes
        
        # form list of compile layers
        result : list[list[Target]] = []

        layer = get_lower_nodes()
        while(len(layer) > 0):
            result.append(layer)
            layer = get_lower_nodes()
        return result

class Project:
    def __init__(self) -> None:
        self.target_man = TargetManager()
        self.OUT_FILE               : str = ""
        self.COMPILER               : str = "clang"
        self.OBJ_PATH               : str = "obj"
        self.AR                     : str = "ar"
        self.SRC_EXTS               : set[str] = {".cpp",".c"}
        self.SRC_DIRS               : set[str] = {"src"}
        self.SRC_RECURSIVE_DIRS     : set[str] = set()
        self.INCLUDE_DIRS           : set[str] = self.SRC_DIRS
        self.EXPORT_INCLUDE_DIRS    : set[str] = self.INCLUDE_DIRS
        self.LOCAL_COMPILER         : set[str] = self.COMPILER
        self.AR_FLAGS               : set[str] = {"r","c","s"}
        self.CFLAGS                 : set[str] = {"-O3"}
        self.SUBPROJECTS            : set[str] = set()
        self.SUBPROJECTS_LIBS       : set[str] = set()
        self.LIB_DIRS               : set[str] = set()
        self.LIBS                   : set[str] = set()
        self.INCLUDE_FLAGS          : set[str] = set()
        self.LIB_DIRS_FLAGS         : set[str] = set()
        self.LIBS_FLAGS             : set[str] = set()

        self.MAX_THREADS_NUM        : int = 1

# Color text Win/Lin
if os.name == 'nt':
    def color_text(color,text):
        return f"[{color}m{text}[0m"
else:
    def color_text(color, text):
        return f"\033[{color}m{text}\033[0m"

def sh(cmd: list[str]) -> int:
    #print(cmd)
    return subprocess.Popen(cmd).wait()

def build_c(source:str, obj:str, p:Project) -> int:
    print(f"{color_text(94,'Building')}: {os.path.relpath(obj)}")    
    os.makedirs(os.path.dirname(obj),exist_ok=True)
    basename = os.path.splitext(obj)[0]
    depflags = ['-MT',obj,'-MMD','-MP','-MF',f"{basename}.d"]
    cmd = [p.COMPILER]+depflags
    cmd += list(p.CFLAGS)
    cmd += list(p.INCLUDE_FLAGS) +['-c','-o',obj,source]
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

def link(cmd:list[str], out:str):
    os.makedirs(os.path.dirname(out),exist_ok=True)
    old_size = 0
    if os.path.exists(out):
        old_size=os.stat(out).st_size

    code = sh(cmd)
    
    if code == 0:
        new_size=os.stat(out).st_size
        print(f'{out} size {new_size} [{diff(old_size,new_size)}]')

    return code

def link_exe(out:str, objects:set[str], p:Project) -> int:
    print(f"{color_text(32,'Linking executable')}: {os.path.relpath(out)}")
    cmd = [p.COMPILER]+list(p.LIB_DIRS_FLAGS)+list(objects)+['-o',out]+list(p.LIBS)
    return link(cmd,out)

def build_target(t:Target, p:Project) -> int:
    for prq in t.prerequisites:
        match(os.path.splitext(prq)[1]):
            case '.c': return build_c(prq, t.path, p)
    
    target = p.target_man.find(t.path)
    match(os.path.splitext(target.path)[1]):
        case '' | '.exe': return link_exe(target.path,target.prerequisites,p)

    print(f"{color_text(91,'Not found builder for')}: {os.path.relpath(t.path)}")
    return 1

def process(p:Project):
    if not p.OUT_FILE:
        raise Exceptions.OutFileEmpty()

    # default sources targets 
    sources = set(find_files(p.SRC_DIRS, p.SRC_EXTS))
    objects = []
    deps = []
    for src in sources:
        path = p.OBJ_PATH + "/" + os.path.relpath(src).replace('../','updir/')
        spl = os.path.splitext(path)
        obj = f"{spl[0]}.o"
        dep = f"{spl[0]}.d"
        objects.append(obj)
        deps.append(dep)
        p.target_man.add(Target(obj,{src}))

    # default out file target
    p.target_man.add(Target(p.OUT_FILE,set(objects)))

    # load targets from .d files if they present
    for d in deps:
        p.target_man.get_from_d_file(d)

    layers = p.target_man.get_build_layers()
    if not layers:
        print('Nothing to build')
        return
    
    # prepare flags
    p.INCLUDE_FLAGS     = {f"-I{x}" for x in p.INCLUDE_DIRS}
    p.LIB_DIRS_FLAGS    = {f"-L{x}" for x in p.LIB_DIRS}
    p.LIBS_FLAGS        = {f"-l{x}" for x in p.LIBS}

    for layer in layers:
        layer : list[Target]

        error = False
        with concurrent.futures.ProcessPoolExecutor(max_workers=p.MAX_THREADS_NUM) as executor:
            builders = [executor.submit(build_target,t,p) for t in layer]
            for builder in builders:
                if builder.result() != 0:
                    error = True
                    break
            if error:
                break
    if not error:
        print(color_text(32,'Done'))

if __name__== "__main__":
    p = Project()
    p.OUT_FILE = "test"
    process(p)
    #p = Project()
    #p.target_man.add(Target("bin/test",{"lib/lib1.a","lib/lib2.a","obj/main.o","obj/second.o"}))
    #p.target_man.add(Target("obj/main.o",{"src/main.c","include/inc1.h","include/inc2.h"}))
    #p.target_man.add(Target("obj/second.o",{"src/second.c","include/inc1.h","include/inc2.h"}))
    #p.target_man.add(Target("include/inc1.h",{}))
    #p.target_man.add(Target("include/inc2.h",{}))
    #p.target_man.add(Target("lib/lib1.a",{"lib/src1.o"}))
    #p.target_man.add(Target("lib/src1.o",{"lib/src1.c"}))
    #p.target_man.add(Target("lib/lib2.a",{"lib/src2.o"}))
    #p.target_man.add(Target("lib/src2.o",{"lib/src2.c"}))

    #p.target_man.add(Target(re.compile(".*\.c$"),{}))
    #gg = p.target_man.check_prerequisites_have_targets()
    #targ = p.target_man.get_build_layers()
    #pass