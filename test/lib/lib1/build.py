#!/usr/bin/python3

def get_config() -> 'ToolConfig':
    cfg = ToolConfig()
    cfg.MAX_THREADS_NUM = 1
    return cfg

def get_rules() -> list['Rule']:
    config = c.Config()
    config.INCLUDE_DIRS = ['src']
    config.set_paths_absolute()

    rules = c.create_standard_rules_macro('bin/liblib1.a',upstream_config=config)
    return rules

#-----------FOOTER-----------
# https://github.com/AIG-Livny/mapyr.git
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
    process(get_rules,get_config if 'get_config' in dir() else None)