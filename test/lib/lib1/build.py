#!/usr/bin/env python

def get_config() -> 'core.ToolConfig':
    cfg = core.ToolConfig()
    cfg.MAX_THREADS_NUM = 1
    return cfg

def get_project(name:str = 'main') -> 'c.Project':
    config = c.Config()
    config.INCLUDE_DIRS = ['src']

    # Put config in `public_config` to show what values we want to expose to other projects
    # in `add_default_rules` of parent it be automatically added in parent private_config

    project = c.Project('main','bin/liblib1.a',public_config=config)
    c.add_default_rules(project)
    return project

#-----------FOOTER-----------
from mapyr import *
# Disable footer in tests
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
    core.process(get_project, get_config)