#!/usr/bin/python3

def config() -> dict[str,"mapyr.ProjectConfig"]:
    main = mapyr.ProjectConfig()
    main.OUT_FILE  = "bin/liblib1.a"

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
    mapyr.process(config)