#!/usr/bin/python3

def get_config() -> 'ToolConfig':
    cfg = ToolConfig()
    cfg.MAX_THREADS_NUM = 1
    return cfg

def get_rules() -> list['Rule']:
    import lib.lib1.build

    conf = c.Config()
    rules = lib.lib1.build.get_rules()
    rules.append(Rule('build',['bin/main'],phony=True))
    rules.append(Rule('bin/main',['obj/src/main.o','obj/src/script_artefact.o',find_rule('bin/liblib1.a',rules).target], config=conf.__dict__, exec=c.link_executable, before_build=[c.check_build]))
    rules.append(Rule('obj/src/main.o',['src/main.c'],exec=c.build_object,config=conf.__dict__))
    rules.append(Rule('obj/src/script_artefact.o',['src/script_artefact.c'],exec=c.build_object,config=conf.__dict__))
    rules.append(Rule('src/script_artefact.c',['script.py'],exec=python.run,config=conf.__dict__))
    rules.append(Rule('src/main.c'))
    rules.append(Rule('script.py'))

    c.add_rules_from_d_file('obj/src/main.d',rules)

    return rules

#-----------FOOTER-----------
from mapyr import *
'''
#-----------FOOTER-----------
try:
    from mapyr import *
except:
    import shutil, subprocess, os
    path = f'{os.path.dirname(__file__)}/mapyr'
    shutil.rmtree(path,ignore_errors=True)
    if subprocess.run(['git','clone','https://github.com/AIG-Livny/mapyr.git',path]).returncode: exit()
    from mapyr import *

'''
if __name__ == "__main__":
    process(get_rules,get_config if 'get_config' in dir() else None)