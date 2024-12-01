#!/usr/bin/python3

import mapyr
'''
try:
    import mapyr
except:
    import requests, os
    os.makedirs(f'{os.path.dirname(__file__)}/mapyr',exist_ok=True)
    with open(f'{os.path.dirname(__file__)}/mapyr/__init__.py','+w') as f:
        f.write(requests.get('https://raw.githubusercontent.com/AIG-Livny/mapyr/master/__init__.py').text)
    import mapyr
'''

def get_config() -> mapyr.Config:
    cfg = mapyr.Config()
    cfg.MAX_THREADS_NUM = 1
    return cfg

def get_project(name:str) -> "mapyr.Project|None":
    return mapyr.create_c_project('bin/liblib1.a',export_config={'INCLUDE_DIRS' : ['src']})


if __name__ == "__main__":
    mapyr.process(get_project,get_config)