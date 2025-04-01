# Mapyr v.0.8.2

Mapyr - is a small build system written in Python3, uses python as build file (no new languages) and inherits the Makefile rule system, extending and complementing it.

Advantages of Mapyr:
 - Small size
 - Project system
 - Simple hierarchy
 - Modular addon system makes it easy to add new languages or
 - It can be used as is for any language. Language modules just for convenience.

# Usage
Mapyr starts with `build.py` file. Footer will clone the Mapyr repo if it no exists yet. The Mapyr repository is not expected to become part of your project, but `build.py`.

Example of `build.py`:
```python
#!/usr/bin/env python

from mapyr import *

def get_project(name:str) -> 'ProjectBase':
    cfg = ConfigBase()
    return ProjectBase('debug','target-file', cfg)

if __name__ == "__main__":
    process(get_project)
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