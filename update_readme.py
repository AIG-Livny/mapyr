import os
import re

lp = os.path.dirname(__file__)

with open(f'{lp}/__init__.py','r') as f:
    text = f.read()
    version = re.search(r"VERSION\s+=\s+'(.*)'",text).group(1)

with open(f'{lp}/README.md','r') as f:
    readme_content = f.read()

with open(f'{lp}/README.md','w+') as f:
    res = re.sub(r"^# Mapyr v.*", f'# Mapyr v.{version}', readme_content)
    f.write(res)