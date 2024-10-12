# Mapyr v.0.4.3

Mapyr - is python build system GCC/clang oriented. 

For simple and complex projects with subprojects in it. 

There is relate project for GNU Make `Mapr` https://github.com/AIG-Livny/mapr.git

# Quick start
Create `src/main.c` and `build.py` with content:
```py
#!/usr/bin/python3
REQUIRED_VERSION = '0.4.2'

def config() -> list["mapyr.ProjectConfig"]:
    result = []
    p = mapyr.ProjectConfig()

    p.OUT_FILE = "bin/cloed"

    result.append(p)
    return result

#-----------FOOTER-----------
# https://github.com/AIG-Livny/mapyr.git
if __name__ == "__main__": 
    try:
        import mapyr
    except:
        import requests, os
        os.makedirs(f'{os.path.dirname(__file__)}/mapyr',exist_ok=True)
        with open(f'{os.path.dirname(__file__)}/mapyr/__init__.py','+w') as f:
            f.write(requests.get('https://raw.githubusercontent.com/AIG-Livny/mapyr/master/__init__.py').text)
        import mapyr
    mapyr.process(config(), REQUIRED_VERSION)
```
# Commands
- `build [group]` - build projects in group. Default group is 'DEBUG'
- `clean [group]` - clean projects in group
- `name` - print output file path of first project
- `run` - execute output file of first project

# Variables list

## of macro in C code 

- `__MAPYR__FILENAME__` - filename of current source file

## of ProjectConfig
Almost all variables is optional, except `OUT_FILE`. In brackets default value if exists.

[//]: <start_of_varlist>

- `OUT_FILE` - (str:"") - Name of out file. Name and extension defines type of file:    - executable: without extension or `.exe`    - static library:	`lib%.a`    - dynamic library:	`%.dll` or `%.so`

- `GROUPS` - (list[str]:['DEBUG']) - A project can belong to several groups. Default group is DEBUGWhen build.py started without arguments, it runs build DEBUG group

- `COMPILER` - (str:"clang") - Compiler, global variable, come from main project

- `OBJ_PATH` - (str:"obj") - Path where store object files

- `AR` - (str:"ar") - Archiver

- `SRC_EXTS` - (list[str]:[".cpp",".c"]) - Source extensions for search

- `SRC_DIRS` - (list[str]:["src"]) - Source directories for NOT recursive search

- `SRC_RECURSIVE_DIRS` - (list[str]:[]) - Source directories for recursive search

- `INCLUDE_DIRS` - (list[str]:[]) - Private include directories

- `EXPORT_INCLUDE_DIRS` - (list[str]:[]) - Include directories that also will be sended to parent projectand parent will include them while his building process

- `AR_FLAGS` - (list[str]:["r","c","s"]) - Archiver flags

- `CFLAGS` - (list[str]:["-O3"]) - Compile flags

- `LINK_EXE_FLAGS` - (list[str]:[]) - Flags used while executable linking

- `SUBPROJECTS` - (list[str]:[]) - Paths to directories contains build.pyIf subproject is library, it will auto-included as library in the project.

- `LIB_DIRS` - (list[str]:[]) - Directories where looking for libraries

- `LIBS` - (list[str]:[]) - List of libraries

- `INCLUDE_FLAGS` - (list[str]:[]) - Flags that will passed to compiler in the include part of command.This is automatic variable, but you can add any flag if it needed

- `LIB_DIRS_FLAGS` - (list[str]:[]) - Flags that will passed to linker in library directories part of command.This is automatic variable, but you can add any flag it if needed

- `LIBS_FLAGS` - (list[str]:[]) - Flags that will passed to linker in library part of command.This is automatic variable, but you can add any flag it if needed

- `PKG_SEARCH` - (list[str]:[]) - If `pkg-config` installed in system then this libraries will be auto included in project

- `SOURCES` - (list[str]:[]) - Particular source files. This is automatic variable, but you can add any flag if needed

- `EXCLUDE_SOURCES` - (list[str]:[]) - Sometimes need to exclude a specific source file from auto searchAdd path to source in relative or absolute format

- `PRIVATE_DEFINES` - (list[str]:[]) - Private defines, that will be used only in this project

- `DEFINES` - (list[str]:[]) - Defines used in this project and all its children

- `EXPORT_DEFINES` - (list[str]:[]) - Defines that used in the project and also will be passed to parent project

- `MAX_THREADS_NUM` - (int:10) - Build threads limit

- `VSCODE_CPPTOOLS_CONFIG` - (bool:False) - Generate C/C++ Tools for Visual Studio Code config (c_cpp_properties.json)

[//]: <end_of_varlist>


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
REQUIRED_VERSION = '0.4.2'

def config() -> list["mapyr.ProjectConfig"]:
    result = []
    p = mapyr.ProjectConfig()

    p.OUT_FILE = "bin/cloed"

    p.CFLAGS  = ["-g","-O0"]
    p.LIBS = ['m']
    p.SUBPROJECTS = [
        "lib/mathc",
        "lib/shaderutils",
        "lib/freetype-gl",
        ]

    p.PKG_SEARCH = [
        "freetype2",
        "glew",
        "glfw3",
        "fontconfig",
    ]

    result.append(p)
    return result

#-----------FOOTER-----------
# https://github.com/AIG-Livny/mapyr.git
if __name__ == "__main__": 
    try:
        import mapyr
    except:
        import requests, os
        os.makedirs(f'{os.path.dirname(__file__)}/mapyr',exist_ok=True)
        with open(f'{os.path.dirname(__file__)}/mapyr/__init__.py','+w') as f:
            f.write(requests.get('https://raw.githubusercontent.com/AIG-Livny/mapyr/master/__init__.py').text)
        import mapyr
    mapyr.process(config(), REQUIRED_VERSION)
```