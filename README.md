# Mapyr v.0.7.1

Mapyr - is a small not-installable in OS build system written in Python3 and inherits the Makefile rule system, extending and complementing it.

Why Mapyr needed:
 - Extend the capabilities of Makefile
 - Replace the Makefile language with Python language
 - For exchanging configurations system between different projects

# Usage
Create file `build.py` in the project root directory. Put this mandatory text into it:
```python
#!/usr/bin/python3

def get_rules(variant:str) -> list['Rule']:
    return []
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
    process(get_rules,get_config if 'get_config' in dir() else None)
```
This code will download this repository if it not exists or has errors

- Function `get_rules` have to return list of possible rules.

- `Rule` has target, prerequisites, configurations and executing function.

- `Target : str` is path to file that we expect after executing this rule, or just name.

- `Prerequisites : list[str]` is targets or names that must be done before this rule.

- `Config : dict` any configuration values packed into dictionary. Configurations can be passed to other rules. See below.

- `Exec : function(rule:Rule)` if function that rule must execute to achive target, accept caller rule as argument

- If `target` is name (not path to file) then rule must be marked `phony`.

- We can call any rule from shell: `build.py myrule`. Calling `build.py` without arguments will run `build` target as default.


Example of a C static library project `get_rules` function:

```python
def get_rules() -> list['Rule']:

    # We are going to send this config
    # to all who will include this project
    # so they must have INCLUDE_DIR, LIB_DIR and LIB
    # pointing to this library
    config = c.Config()
    config.LIB_DIRS = ['bin']
    config.LIBS = ['lib1']
    config.INCLUDE_DIRS = ['src']

    # Make paths absolute to avoid mistakes
    config.set_paths_absolute()

    rules = []
    # Phony target build as entry point
    rules.append(Rule('build',['bin/liblib1.a'],phony=True))

    # Main target request 'lib1.o' before exec link
    # and send config in upstream configs,
    # those who get this rule as prerequisite
    rules.append(Rule('bin/liblib1.a',['obj/src/lib1.o'],exec=c.link_static,upstream_config=config.__dict__))

    rules.append(Rule('obj/src/lib1.o',['src/lib1.c'],exec=c.build_object,config=config.__dict__))
    rules.append(Rule('src/lib1.c'))

    # Reading the .d file if he exists.
    # It appends 'src/lib1.h' and other .h
    c.add_rules_from_d_file('obj/src/lib1.d',rules)

    return rules
```
This is custom rules implementation. But it can done simplier by `create_standard_rules_macro` funcion from module `c.py`:
```python
def get_rules() -> list['Rule']:

    config = c.Config()
    config.INCLUDE_DIRS = ['src']
    config.set_paths_absolute()

    rules = c.create_standard_rules_macro('bin/liblib1.a',upstream_config=config)

    return rules
```

Module `c.py` is addon for C language.

# Config exchange rules
Diagram:
```
Root             ChildRoot        GrandChildRoot
Downstream ↧→→→→ Downstream ↧→→→→ Downstream ↧→→→→ ...
           ↓                ↓                ↓
    Config←↤         Config←↤         Config←↤     ...
           ↑                ↑                ↑
Upstream ←←↥←←←← Upstream ←←↥←←←← Upstream ←←↥←←←← ...
```

Downstream config applying for current rule and children
Upstream config applying for current rule and parents
Config applying only for current rule