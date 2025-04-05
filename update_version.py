#!/bin/env python

import os
import re

os.chdir(os.path.realpath(os.path.dirname(__file__)))

with open('VERSION','r') as f:
    ver = f.read()

with open('README.md','r') as f:
    readme_content = f.read()
with open('README.md','w+') as f:
    f.write(re.sub(r"Mapyr v\..*", f"Mapyr v.{ver}", readme_content))

with open('src/mapyr/core.py','r') as f:
    core_content = f.read()
with open('src/mapyr/core.py','w+') as f:
    f.write(re.sub(r"VERSION = '.*'", f"VERSION = '{ver}'", core_content))

with open('pyproject.toml','r') as f:
    pyproject_content = f.read()
with open('pyproject.toml','w+') as f:
    f.write(re.sub(r'version = ".*"', f'version = "{ver}"', pyproject_content))
