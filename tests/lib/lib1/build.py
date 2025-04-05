#!/usr/bin/env python

from mapyr import *

def get_config() -> 'ToolConfig':
    cfg = ToolConfig()
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

if __name__ == "__main__":
    process(get_project, get_config)