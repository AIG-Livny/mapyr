#!/usr/bin/env python

def get_config() -> 'ToolConfig':
    cfg = ToolConfig()
    cfg.MAX_THREADS_NUM = 1
    return cfg

def get_rules(variant : str = '') -> list['Rule']:
    config = c.Config('bin/liblib1.a')
    config.INCLUDE_DIRS = ['src']
    config.make_abs()

    c.delete_objects_if_config_different(config)
    return c.get_default_rules(config)

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