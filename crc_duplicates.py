import csv

import itertools
import os
from collections import defaultdict
from urllib.parse import quote

FILES = (
    'nekraid01.csv',
    # 'downloads.csv',
    'success.csv'
)
INVALID_EXTS = ('yml', 'dl', 'txt', 'ico', 'rtf', 'dll', 'directory')
duplicate_paths = defaultdict(list)


def read_rows(file):
    with open(file) as f:
        return list(csv.reader(f))


def repair_path(path):
    return path.replace('/volume1/Nekraid02/', '/media/nekraid02/')


def get_directory(path):
    return repair_path(os.path.dirname(path))


def get_uri(path):
    return 'file://{}'.format(quote(path))


def get_repr_path(directory):
    return '{} "{}"'.format(get_uri(directory), directory)


def remove_invalid_exts(files):
    return list(filter(lambda file: file.split('.')[-1] not in INVALID_EXTS,  files))


def path_name(path):
    if '/media/nekraid01/' in path:
        return 'nekraid01'
    elif '/volume1/Nekraid02/Success/' in path or '/media/nekraid02/Success' in path:
        return 'Success'
    else:
        return 'Download'


def all_exists(paths):
    for path in paths:
        if not os.path.lexists(path):
            return False
    return True


rows = itertools.chain(*[read_rows(file) for file in FILES])
crcs = defaultdict(list)

for row in rows:
    row = list(row)
    row[0] = repair_path(row[0])
    crcs[row[2]].append(row)


duplicates = [x for x in crcs.values() if len(x) > 1 and all_exists(map(lambda y: y[0], x))]


for duplicate in duplicates:
    paths = tuple(sorted(frozenset(tuple([get_directory(row[0]) for row in duplicate]))))
    # duplicate_paths[paths].extend(['  [{}] {}'.format(path_name(x[0]), x[1]) for x in duplicate])
    duplicate_paths[paths].extend([repair_path(x[0]) for x in duplicate])


duplicate_paths = {key: remove_invalid_exts(value) for key, value in duplicate_paths.items() if len(key) > 1}
duplicate_paths = {key: value for key, value in duplicate_paths.items() if len(value) > 1}
duplicate_paths = {key: value for key, value in duplicate_paths.items() if all_exists(key)}


for paths, datas in sorted(duplicate_paths.items()):
    print('\n'.join(map(get_repr_path, paths)))
    for f in datas:
        print('[{}] {}'.format(path_name(f), os.path.split(f)[1]))
    print('\n\n')
