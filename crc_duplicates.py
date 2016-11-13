import csv

import itertools
import os
from collections import OrderedDict
from collections import defaultdict
from urllib.parse import quote

FILES = ('nekraid01.csv', 'downloads.csv', 'success.csv')
duplicate_paths = defaultdict(list)


def read_rows(file):
    with open(file) as f:
        return list(csv.reader(f))


def get_directory(path):
    return os.path.dirname(path)


def get_uri(path):
    return 'file://{}'.format(quote(path))


def get_repr_path(path):
    path = get_directory(path.replace('/volume1/Nekraid02/', '/media/nekraid02/'))
    return '{} "{}"'.format(get_uri(path), path)


def path_name(path):
    if '/media/nekraid01/' in path:
        return 'nekraid01'
    elif '/volume1/Nekraid02/Success/' in path:
        return 'Success'
    else:
        return 'Download'


def line_format(line):
    return '[{}]\t{}\tfile://{}'.format(
        path_name(line[0]), line[1],
        quote(os.path.split(line[0].replace('/volume1/Nekraid02/', '/media/nekraid02/'))[0]))


rows = itertools.chain(*[read_rows(file) for file in FILES])
crcs = defaultdict(list)

for row in rows:
    crcs[row[2]].append(row)


duplicates = [x for x in crcs.values() if len(x) > 1]


for duplicate in duplicates:
    paths = tuple(sorted(frozenset(tuple([get_repr_path(row[0]) for row in duplicate]))))
    duplicate_paths[paths].extend(['  [{}] {}'.format(path_name(x[0]), x[1]) for x in duplicate])


duplicate_paths = {key: value for key, value in duplicate_paths.items() if len(key) > 1}


for paths, datas in sorted(duplicate_paths.items()):
    print('\n'.join(paths))
    for data in datas:
        print(data)
    print('\n\n')
