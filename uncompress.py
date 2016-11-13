#!/usr/bin/env python
import json
import re

import subprocess
from os3.fs.shortcuts import ls


DOWNLOADS_DIR = '/media/nekraid02/Success'


def only_first_rar(element):
    if not element.name.endswith('.rar'):
        return False
    if re.match(r'.*\.part0*1\.rar$', element.name, re.IGNORECASE):
        return True
    if re.match(r'.*\.part[0-9]+\.rar$', element.name, re.IGNORECASE):
        return False
    return True


def get_rar_parts(rar):
    if re.match(r'.*\.part0*1\.rar$', rar.name, re.IGNORECASE):
        pattern = '.'.join(rar.name.split('.')[:-2])
        pattern = re.escape(pattern) + r'\.part\d+\.rar$'
        return lambda x: re.match(pattern, x.name, re.IGNORECASE)
    else:
        return lambda x: x.name == rar.name


def get_password(directory):
    anime_data = directory.sub('.anime.json')
    if not anime_data.exists():
        data = {}
    else:
        with open(anime_data.path) as f:
            data = json.load(f)
    return data.get('password')


for directory in ls(DOWNLOADS_DIR, type='d'):
    rars = directory.ls().filter(only_first_rar)
    if not rars.count():
        continue
    password = get_password(directory)
    for rar in rars:
        params = ('unrar', '-o+')
        if password:
            params += ('-p{}'.format(password),)
        params += ('x', rar.path)
        p = subprocess.Popen(params, cwd=directory.path)
        p.communicate()
        if not p.returncode:
            print('Remove')
            part_rars = directory.ls().filter(get_rar_parts(rar))
            print('Remove parts: ', part_rars)
            part_rars.remove()
        else:
            print('Error!!!')
