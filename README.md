# Mapyr v.0.6.0

Mapyr - is a one-file build system written in Python3 and inherits the Makefile rule system, extending and complementing it.

Why Mapyr needed:
 - Extend the capabilities of Makefile
 - Replace the Makefile language with Python language
 - Create a system for exchanging configurations between different projects

# Quick start
Create `src/main.c` and `build.py` with content:
```py
#!/usr/bin/python3

def get_project(name:str) -> 'mapyr.Project|None':
    return mapyr.create_c_project('main','bin/main')


#-----------FOOTER-----------
# https://github.com/AIG-Livny/mapyr.git
try:
    import mapyr
except:
    import requests, os
    os.makedirs(f'{os.path.dirname(__file__)}/mapyr',exist_ok=True)
    with open(f'{os.path.dirname(__file__)}/mapyr/__init__.py','+w') as f:
        f.write(requests.get('https://raw.githubusercontent.com/AIG-Livny/mapyr/master/__init__.py').text)
    import mapyr

if __name__ == "__main__":
    mapyr.process(get_project)
```
And run `./build.py`

# Arguments
By default arguments are "main build", so running `./build.py` will compile main target

If an one argument present then it will be accepted as target name for 'main' project. So running `./buld.py clean` will execute 'main clean'

If both or more arguments present: the first - project name, the second - target name. Other will be ignored

Default rules for all projects:
- `target` - print target of project
- `build` - run build process

Default arguments for C project:
- `clean` - clean project
- `gcvscode` - generate init config for vscode

# Features

### Config sharing:
There are 3 config types for each project:
- Private config - is using only for this project
- Config - for this project and its children
- Export config - for this project and its parents

While processing the project tree "Export config" and "Config" will be merged with "Private config" and go further. Take a look this diagram

 ```
 Root project------>------SubProject-------->-----SubSubProject----------...

 Config---\----->---------Config---\-------->-----Config----\------>-----...
          V                        V                        V
 Private config           Private config          Private config         ...
              ^                        ^                       ^
 Export config-\-----<----Export config-\----<----Export config-\----<---...
 ```

So, some a library with specific flags can transmit them up
And children can get the parent configs

### Flexible rule system:
Inherited from Makefile the rule system can be configured for any project and language.

There is default rule set for C language project as example. See the 'C' section in `__init__.py`

### Mapyr Config
Mapyr itself has config:

- `MAX_THREADS_NUM` [int = 10] - Build threads limit

- `MINIMUM_REQUIRED_VERSION` [str = VERSION] - Minimum required version for this config file

- `VERBOSITY` [str = "INFO"] - Verbosity level for console output. Value can be any from logging module: ['CRITICAL','FATAL','ERROR','WARN','WARNING','INFO','DEBUG','NOTSET']

Using example you can see in test folder
