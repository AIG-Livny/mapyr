# Mapyr v.0.1

Mapyr - is python build system GCC/clang oriented. 

For simple and complex projects with subprojects in it. 

# Quick start
Create `src/main.c` and `Mapyrfile` with this content and run `./Mapyrfile`
```py
#!/usr/bin/python3
def config() -> "ProjectConfig":
    p = ProjectConfig()

    p.OUT_FILE = "bin/cloed"

    return p

#-----------FOOTER-----------
# https://github.com/AIG-Livny/mapyr.git
if __name__ == "__main__": 
    try:
        from mapyr.common import *
    except:
        import requests
        import os
        r = requests.get('https://raw.githubusercontent.com/AIG-Livny/mapyr/master/common.py')
        os.makedirs('mapyr',exist_ok=True)
        with open('mapyr/common.py','+w') as f:
            f.write(r.text)
        from mapyr.common import *
    process(config()) 
```

# Variables list
Almost all variables is optional, except `OUT_FILE`. In brackets default value if exists.

- `OUT_FILE` - name of out file. Name and extension defines type of file:
 	- executable: without extension or `.exe`
	- static library:	`lib%.a`
	- dynamic library:	`%.dll` or `%.so`

- `PKG_SEARCH` - libraries to search in `pkg-config` and add flags 

- `COMPILER` - (g++) - compiler, global variable, come from main project

- `LOCAL_COMPILER` - (COMPILER) - be used if present ignoring COMPILER var. 

- `SUBPROJECTS` - list of directories where subprojects's `Makefile`'s contains. Example:
    ```
    SUBPROJECTS += lib/somesublib
    SUBPROJECTS += lib/anothersublib
    ```
    All subprojects recieves command via `subprojects.` prefix.
    ```
    make subprojects.all
    make subprojects.clean
    ```
    Will pass `all` and `clean` commands.

- `SRC_DIRS` - (src) - list directories where looking for sources 

- `SRC_RECURSIVE_DIRS` - list directories where starts recursive search of sources

- `SRC_EXTS` - (*.cpp *.c) - source extensions

- `INCLUDE_DIRS` - (SRC_DIRS) - list directories where looking for headers

- `EXPORT_INCLUDE_DIRS` - (INCLUDE_DIRS) - if specified upper project will get only these directories automatically. This variable is for dividing private and public includes.

- `EXPORT_DEFINITIONS` - list of definitions that will be sended to upper project. In example: you have library with `#ifdef` statements, you configure and build library as independent project. When upper project will include `.h`, he will not to know about any definitions that was used during building library, so `EXPORT_DEFINITIONS` can pass them up. These definitions also used in building project itself.

    ```
    EXPORT_DEFINITIONS += USE_OPTION
    ```

- `LIB_DIRS` - list directories where looking for libraries

- `OBJ_PATH` - (obj) - where to store object files.

- `LINK_FLAGS` - link stage flags

- `CFLAGS` - (-O3) - compile stage flags. It is global variable that be passed to subprojects and rewrite local `CFLAGS` variable. To use private flags see `LOCAL_CFLAGS`

- `LOCAL_CFLAGS` - compile stage flags. These flags affects on only local project and not will passed into subprojects.

- `SOURCES` - list of source files. Can be used to specify files that can not be found by recursive search. In example: sertain source file from other project, without any excess sources.

- `LIBS` - list of libraries to link.

- `AR` - archiver

- `AR_FLAGS` - archivier flags

- `EXCLUDE_SOURCES` - list of sources exclusions

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
       |___Mapyrfile
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
       |___Mapyrfile
```

# Mapyr example

```py
#!/usr/bin/python3
def config() -> "ProjectConfig":
    p = ProjectConfig()

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

    return p

#-----------FOOTER-----------
# https://github.com/AIG-Livny/mapyr.git
if __name__ == "__main__": 
    try:
        from mapyr.common import *
    except:
        import requests
        import os
        r = requests.get('https://raw.githubusercontent.com/AIG-Livny/mapyr/master/common.py')
        os.makedirs('mapyr',exist_ok=True)
        with open('mapyr/common.py','+w') as f:
            f.write(r.text)
        from mapyr.common import *
    process(config())
```