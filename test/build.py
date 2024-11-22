#!/usr/bin/python3

import copy

def tool_config() -> "mapyr.ToolConfig":
    tc = mapyr.ToolConfig()
    tc.MINIMUM_REQUIRED_VERSION = '0.5.2'
    return tc

def config() -> dict[str,"mapyr.ProjectConfig"]:
    import lib.lib1.build

    main = mapyr.ProjectConfig()
    main.OUT_FILE  = "bin/test"
    main.CFLAGS = ['-g','-O0']
    main.SUBPROJECTS = [
        lib.lib1.build.config()['main']
    ]

    return {
        'main':main,
    }

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
    mapyr.process(config, tool_config)