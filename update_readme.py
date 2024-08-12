import os
import re

lp = os.path.dirname(__file__)

with open(f'{lp}/__init__.py','r') as f:
    text = f.read()
    content = re.search(r'^#-+PROJECT CONFIG-+(\n|.)*^#-+END PROJECT CONFIG',text,re.MULTILINE).group(0)
    version = re.search(r"VERSION\s+=\s+'(.*)'",text).group(1)

res = re.findall(r"^\s+self.(\w+)\s*:\s*([\w\[\]]+)\s*=\s*(.+)$\n\s+'''((?:.|\n)+?)'''",content, re.MULTILINE)

lines = ['[//]: <start_of_varlist>\n']
for m in res:
    descr = m[3].replace('\n            ','').strip()
    lines.append(f'- `{m[0]}` - ({m[1]}:{m[2]}) - {descr}\n')
lines.append('[//]: <end_of_varlist>\n')

with open(f'{lp}/README.md','r') as f:
    readme_content = f.read()

with open(f'{lp}/README.md','w+') as f:
    res = re.sub(r"^\[\/\/\]: <start_of_varlist>((?:.|\n)+)^\[\/\/\]: <end_of_varlist>",'\n'.join(lines),readme_content,flags=re.MULTILINE)
    res = re.sub(r"^# Mapyr v.*", f'# Mapyr v.{version}', res)
    f.write(res)