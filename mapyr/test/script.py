#!/usr/bin/python3

import mapyr
import os

def run(rule:mapyr.core.Rule) -> int:
    with open(f'{os.path.dirname(__file__)}/src/script_artefact.c','w+') as f:
        f.write('int some_fnc(){return 0;}')
    return 0