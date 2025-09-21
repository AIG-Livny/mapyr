# Mapyr v.0.9.0

Mapyr is a small build system written in Python 3.  It uses Python for build files (no new languages required) and inherits the Makefile rule system, extending and complementing it.

Advantages of Mapyr:
 - Small size
 - Project system
 - Simple hierarchy
 - Modular addon system for easily adding support for new languages (language modules are provided for convenience, but not required)

# Quick start
C/C++ example:

build.py:
```python
#!/usr/bin/env python

from mapyr import *

def get_project(name:str) -> ProjectBase:
    cfg = c.Config()

    # Dirs to find source files
    cfg.SRC_DIRS = ['src']

    # Create project ( name, output filename, config )
    project = c.Project('main','bin/main',cfg)

    # Default rules for C project like: build, clean, and executable
    c.add_default_rules(project)

    return project

if __name__ == "__main__":
    process(get_project)
```
Run `./build.py`

# Install
```
pip install mapyr
```

# Usage
Mapyr starts with a build.py file, call `process` funcution and which calls get_project.

## Rule System

Mapyr's rule system is derived from GNU Make:

* Target: A file (or phony target) that must exist or be built.
* Prerequisites: A list of rules that must be built before this rule.
* Execution: The commands to build the target.

If any prerequisite is newer than the target, the rule is rebuilt.


### Projects

Projects are used to share configurations.  A project groups multiple rules into a single unit, managing private, protected, and public configurations.  This is similar to access modifiers in C++, but less strict. You choose which configurations to inherit from subprojects.  The separation helps clarify a project's public interface versus its internal implementation.

* Private: Accessible only within the project.
* Protected: Accessible within the project and its children.
* Public: Accessible to any project that includes this one as a subproject.


### Examples

See the examples in the test directory.