#!/usr/bin/env python

def get_config() -> 'ToolConfig':
    cfg = ToolConfig()
    cfg.MAX_THREADS_NUM = 1
    return cfg

# `Name` can be passed out of parent projects or command line
# it can be build config or whatever you want
def get_project(name:str) -> 'c.Project':
    import lib.lib1.build

    # Create config and inject artificial dependency on generated file
    config = c.Config()
    config.SOURCES = ['src/script_artefact.c']

    # Create project and make default rules
    project = c.Project('release','bin/main',config,subprojects=[lib.lib1.build.get_project()])
    c.add_default_rules(project)

    # Add dependency of the script_artefact.c on python script
    script = Rule('script.py',project)
    src_rule = project.find_rule('script_artefact.c')
    src_rule.prerequisites.append(script)

    # Add method what we have to run to make the target
    src_rule.exec = python.run

    return project

#-----------FOOTER-----------
# Disable footer in tests
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
    process(get_project,get_config)