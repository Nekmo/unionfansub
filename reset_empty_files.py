import json
import os
from os3.fs.directory import Dir

ROOT_PATH = '/media/nekraid02/Downloads'
DOWNLOAD_CONFIG = os.path.expanduser('~/.config/unionfansub-download.json')

parents = {}
data = json.load(open(DOWNLOAD_CONFIG, 'r'))


def save_config(config):
    json.dump(config, open(DOWNLOAD_CONFIG, 'w'), sort_keys=True, indent=4, separators=(',', ': '))


for file in Dir(ROOT_PATH, deep=True).filter(size=0, type='f'):
    parent = file.parent()
    if parent.path not in parents:
        parents[parent.path] = parent
    os.remove(file.path)


for path in parents:
    data[path]['episode'] = 0
    data[path]['finish'] = False
    data[path]['success'] = False

save_config(data)
