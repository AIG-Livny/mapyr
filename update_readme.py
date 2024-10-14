import os
import re

lp = os.path.dirname(__file__)

with open(f'{lp}/__init__.py','r') as f:
    text = f.read()
    pc_content = re.search(r'^#-+PROJECT CONFIG-+(\n|.)*^#-+END PROJECT CONFIG',text,re.MULTILINE).group(0)
    tc_content = re.search(r'^#-+TOOL CONFIG-+(\n|.)*^#-+END TOOL CONFIG',text,re.MULTILINE).group(0)
    version = re.search(r"VERSION\s+=\s+'(.*)'",text).group(1)

methods_re = r"^\s+self.(\w+)\s*:\s*([\w\[\]]+)\s*=\s*(.+)$\n\s+'''((?:.|\n)+?)'''"

pc_res = re.findall(methods_re, pc_content, re.MULTILINE)
tc_res = re.findall(methods_re, tc_content, re.MULTILINE)

pc_lines = ['[//]: <start_of_project_config_list>\n']
for m in pc_res:
    descr = m[3].replace('\n            ','').strip()
    pc_lines.append(f'- `{m[0]}` - ({m[1]}:{m[2]}) - {descr}\n')
pc_lines.append('[//]: <end_of_project_config_list>')

tc_lines = ['[//]: <start_of_tool_config_list>\n']
for m in tc_res:
    descr = m[3].replace('\n            ','').strip()
    tc_lines.append(f'- `{m[0]}` - ({m[1]}:{m[2]}) - {descr}\n')
tc_lines.append('[//]: <end_of_tool_config_list>')

with open(f'{lp}/README.md','r') as f:
    readme_content = f.read()

with open(f'{lp}/README.md','w+') as f:
    res = re.sub(r"^\[\/\/\]: <start_of_project_config_list>((?:.|\n)+)^\[\/\/\]: <end_of_project_config_list>",'\n'.join(pc_lines),readme_content,flags=re.MULTILINE)
    res = re.sub(r"^\[\/\/\]: <start_of_tool_config_list>((?:.|\n)+)^\[\/\/\]: <end_of_tool_config_list>",'\n'.join(tc_lines),res,flags=re.MULTILINE)
    res = re.sub(r"^# Mapyr v.*", f'# Mapyr v.{version}', res)
    f.write(res)