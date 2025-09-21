import importlib.util
import os
import pexpect
import shutil
import importlib
import inspect
import hashlib
from mapyr.logs import logger


# Color text Win/Lin
if os.name == 'nt':
    def color_text(color,text):
        return f"[{color}m{text}[0m"
else:
    def color_text(color, text):
        return f"\033[{color}m{text}\033[0m"

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

class CompletedProcess:
    def __init__(self,cmd,exitstatus,output):
        self.cmd = cmd
        self.returncode = exitstatus
        self.output = output

def sh(cmd: str | list[str], shell=False, cwd=None) -> CompletedProcess:
    logger.debug(cmd)

    program : str = cmd
    args : list[str] = []
    if type(cmd) is list:
        program = cmd[0]
        args = cmd[1:]
    else:
        program = cmd

    if shell:
       program = f"sh -c '{program} {' '.join(args)}'"
       args = []

    child = pexpect.spawn(program,args,encoding='UTF-8',codec_errors='replace', cwd=cwd)
    output = child.read()
    child.close(force=False)
    logger.debug(output)
    print(output,end="")
    return CompletedProcess(cmd,child.exitstatus,output)

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

def stable_hash(value:str) -> int:
    hasher = hashlib.sha256()
    hasher.update(value.encode('utf-8'))
    return int.from_bytes(hasher.digest(), byteorder='big')
