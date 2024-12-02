#!/usr/bin/python3

import lib.lib1.build

def get_config() -> 'mapyr.Config':
    cfg = mapyr.Config()
    cfg.MAX_THREADS_NUM = 1
    return cfg

def get_project(name:str) -> 'mapyr.Project|None':
    match(name):
        case 'main':
            m = mapyr.create_c_project('main','bin/main', subprojects=[lib.lib1.build.get_project('main')],
                                       private_config={'SOURCES':['src/script_artefact.c'],'CFLAGS':['-O2']},
                                       config={'CFLAGS':['-g']})
            m.RULES.append(mapyr.Rule(m,mapyr.Regex(r'.*\.py')))
            m.RULES.append(mapyr.RulePython(m,mapyr.abspath_project(m,'src/script_artefact.c'),mapyr.abspath_project(m,'script.py')))
            return m

    return None

#-----------FOOTER-----------
# https://github.com/AIG-Livny/mapyr.git
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

if __name__ == "__main__":
    mapyr.process(get_project,get_config)