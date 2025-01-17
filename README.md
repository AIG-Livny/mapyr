# Mapyr v.0.8.0

Mapyr - is a small build system written in Python3, uses python as build file (no new languages) and inherits the Makefile rule system, extending and complementing it.

Advantages of Mapyr:
 - Small size
 - Project system
 - Simple hierarchy
 - Modular addon system makes it easy to add new languages or
 - It can be used as is for any language. Language modules just for convenience.

# Usage
Mapyr starts with `build.py` file. This footer will clone the Mapyr repo if it no exists yet. The Mapyr repository is not expected to become part of your project, but `build.py`.

```python
#-----------FOOTER-----------
try:
    from mapyr import *
except:
    import shutil, subprocess, os
    path = f'{os.path.dirname(__file__)}/mapyr'
    shutil.rmtree(path,ignore_errors=True)
    if subprocess.run(['git','clone','https://github.com/AIG-Livny/mapyr.git',path]).returncode: exit()
    from mapyr import *

if __name__ == "__main__":
    process(get_project)
```

Next we need to add `get_project` function.
```python
def get_project(name:str) -> 'core.ProjectBase':
    cfg = core.ConfigBase()
    return core.ProjectBase('debug','target-file', cfg)
```
`name` can be used to identify projects. This example uses base classes, but for more convenient using there are addons like `c.py` and they must provide its own classes (example: `c.Project`,`c.Config` from `c.py`)

run:
```shell
python3 build.py
```

## Rule system
Rule system come directly from GNU Make:

`target` - file (or phony name) that must be exists or be built

`prerequisites` - list of rules that we have to build before this rule

`exec` - what we must do to get target.

If any from prerequisites newer than taraget then rebuid rule.

### Projects
`Project` needed to share configations between them. `Project` joins multiple rules of one unit, and keep private, protected and public configurations. They act like in C++, but are not as strict. You choose which configuration to take from the subproject. But nevertheless, they are separated in order to understand what the project wants to show us and what to leave for internal use.

`private` - only for this project

`protected` - for this and children

`public` - for anyone who want include us as subproject


### You can look at examples in the `test` directory