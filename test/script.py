#!/usr/bin/python3

import mapyr

def run(rule:mapyr.Rule) -> int:
    with open('src/script_artefact.c','w+') as f:
        f.write('int some_fnc(){return 0;}')
    return 0