#!/usr/bin/python3

import mapyr

def generate(parent:mapyr.Project) -> int:
    with open('src/script_artefact.c','w+') as f:
        f.write('int some_fnc(){return 0;}')
    return 0