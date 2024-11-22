# Mapyr v.0.5.2

Mapyr - is python build system GCC/clang oriented. Focused on project relationships in dependency tree.

There is relate project for GNU Make `Mapr` https://github.com/AIG-Livny/mapr.git

# Quick start
Create `src/main.c` and `build.py` with content:
```py
#!/usr/bin/python3

def config() -> dict[str,"mapyr.ProjectConfig"]:
    result = []
    p = mapyr.ProjectConfig()

    p.OUT_FILE = "bin/test"

    return {
        'main':p
    }

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
    mapyr.process(config)

```
# Commands
- `build [project]` - build project. Default project 'main'
- `clean [project]` - clean projects in group
- `outfile [project]` - print output file path of project
- `run [project]` - execute output file of project
- `help` - print help
- `gcvscode` - generate init config for vscode

# Variables list

## macro in C code

- `__MAPYR__FILENAME__` - filename of current source file

## ProjectConfig
Almost all variables is optional, except `OUT_FILE`. In brackets default value if exists.

[//]: <start_of_project_config_list>

- `CWD` - (str:caller_cwd()) - A start path of project.By default - directory of caller script

- `OUT_FILE` - (str:"") - Name of out file. Name and extension defines type of file:    - executable: without extension or `.exe`    - static library:	`lib%.a`    - dynamic library:	`%.dll` or `%.so`

- `COMPILER` - (str:"clang") - Compiler, global variable, come from main project

- `SRC_EXTS` - (list[str]:[".cpp",".c"]) - Source extensions for search

- `SRC_DIRS` - (list[str]:["src"]) - Source directories for NOT recursive search

- `SRC_RECURSIVE_DIRS` - (list[str]:[]) - Source directories for recursive search

- `INCLUDE_DIRS` - (list[str]:[]) - Private include directories

- `EXPORT_INCLUDE_DIRS` - (list[str]:[]) - Include directories that also will be sended to parent projectand parent will include them while his building process

- `AR` - (str:"ar") - Archiver

- `AR_FLAGS` - (list[str]:["r","c","s"]) - Archiver flags

- `CFLAGS` - (list[str]:["-O3"]) - Compile flags

- `LINK_EXE_FLAGS` - (list[str]:[]) - Flags used while executable linking

- `SUBPROJECTS` - (list[ProjectConfig]:[]) - List of projects that must be builded before and used within this project

- `LIB_DIRS` - (list[str]:[]) - Directories where looking for libraries

- `LIBS` - (list[str]:[]) - List of libraries

- `INCLUDE_FLAGS` - (list[str]:[]) - Flags that will passed to compiler in the include part of command.This is automatic variable, but you can add any flag if it needed

- `LIB_DIRS_FLAGS` - (list[str]:[]) - Flags that will passed to linker in library directories part of command.This is automatic variable, but you can add any flag it if needed

- `LIBS_FLAGS` - (list[str]:[]) - Flags that will passed to linker in library part of command.This is automatic variable, but you can add any flag it if needed

- `PKG_SEARCH` - (list[str]:[]) - If `pkg-config` installed in system then this librarieswill be auto included in project

- `SOURCES` - (list[str]:[]) - Particular source files.This is automatic variable, but you can add any flag if needed

- `EXCLUDE_SOURCES` - (list[str]:[]) - Sometimes need to exclude a specific source file from auto searchAdd path to source in relative or absolute format

- `PRIVATE_DEFINES` - (list[str]:[]) - Private defines, that will be used only in this project

- `DEFINES` - (list[str]:[]) - Defines used in this project and all its children

- `EXPORT_DEFINES` - (list[str]:[]) - Defines that used in the project and alsowill be passed to parent project

- `MAX_THREADS_NUM` - (int:10) - Build threads limit

- `VSCODE_CPPTOOLS_CONFIG` - (bool:False) - Generate C/C++ Tools for Visual Studio Code config (c_cpp_properties.json)

- `OVERRIDE_CFLAGS` - (bool:False) - Override CFLAGS in children projects

[//]: <end_of_project_config_list>

## ToolConfig

[//]: <start_of_tool_config_list>

- `MINIMUM_REQUIRED_VERSION` - (str:VERSION) - Minimum required version for this config file (build.py)

- `VERBOSITY` - (str:"INFO") - Verbosity level for console output. Value can be any from logging module: ['CRITICAL','FATAL','ERROR','WARN','WARNING','INFO','DEBUG','NOTSET']

- `PRINT_SIZE` - (bool:False) - Print output file size

[//]: <end_of_tool_config_list>

# Third-party libraries
Any third-party library can be placed into subdirectory, it doesn't change original files and thus replaces its build system.
```
___mapyr
___lib
   |___somelib
       |___somelib  (original lib folder)
       |
       |___bin
       |   |___binary of lib, builded by mapr
       |
       |___build.py
```
or even:
```
___mapyr
___lib
   |___third-party
   |   |___somelib  (original lib folder)
   |
   |___somelib
       |___bin
       |   |___binary of lib, builded by mapr
       |
       |___build.py
```

# Mapyr example

```py
#!/usr/bin/python3

import lib.any_other_lib.build

def tool_config() -> "mapyr.ToolConfig":
    tc = mapyr.ToolConfig()
    tc.MINIMUM_REQUIRED_VERSION = '0.4.4'
    tc.VERBOSITY = 'DEBUG'
    return tc

def config() -> dict[str,"mapyr.ProjectConfig"]:
    p = mapyr.ProjectConfig()

    p.OUT_FILE = "bin/cloed"

    p.CFLAGS  = ["-g","-O0"]
    p.LIBS = ['m']
    p.SUBPROJECTS = [
        lib.any_other_lib.build.config()['main'],
        ]

    p.PKG_SEARCH = [
        "freetype2",
        "glew",
        "glfw3",
        "fontconfig",
    ]

    p.SUBPROJECTS = [
        lib.any_other_lib.build.config()['main']
    ]

    return {
        'main':p
    }


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
    mapyr.process(config, tool_config)

```