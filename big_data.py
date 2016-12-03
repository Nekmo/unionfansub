import argparse
import json
import os
from urllib import parse
from terminaltables import SingleTable

import shutil
from fuzzywuzzy import process

ROOT_PATH = '/media/nekraid02/Downloads'
TARGET_DIR = '/media/nekhd/Anime'
SUCCESS_TARGET_DIR = '/media/nekraid02/Success'
DOWNLOAD_CONFIG = os.path.expanduser('~/.config/unionfansub-download.json')
SUCCESS_DATA_PATH = os.path.expanduser('~/.config/unionfansub-success.json')

target_directories = os.listdir(TARGET_DIR)


def truncatechars(text, max_length):
    text = str(text)
    return (text[:max_length] + '..') if len(text) > max_length else text


def format_uri(x):
    return 'file://{}'.format(parse.quote(x))


def add_subparser(subparser, fn):
    parser_orphan = subparsers.add_parser(fn.__name__)
    parser_orphan.set_defaults(func=fn)


def list_data(root):
    config = json.load(open(DOWNLOAD_CONFIG))
    paths = [os.path.join(root, d) for d in os.listdir(root)]
    return [dict(path=path, **config.get(path, {})) for path in paths]


def print_results(results):
    i = 0
    for item in results:
        i += 1
        print('{} ({}/{})'.format(item['path'], item.get('episode'), item.get('episodes')))
    print('\nTotal results: {}'.format(i))


def orphan(args, use_print=True):
    values = filter(lambda x: 'episodes' not in x, list_data(ROOT_PATH))
    if use_print:
        print_results(values)
    else:
        return values


def completed(args, use_print=True, target_dir=ROOT_PATH):
    values = filter(lambda x: x.get('finish') and x.get('success'), list_data(target_dir))
    if use_print:
        print_results(values)
    else:
        return values


def failed(args):
    print_results(filter(lambda x: x.get('finish') and not x.get('success'), list_data(ROOT_PATH)))


def incompleted(args):
    print_results(filter(lambda x: x.get('finish') == False and x.get('episode', 0) > 0, list_data(ROOT_PATH)))


def pending(args):
    print_results(filter(lambda x: not x.get('finish'), list_data(ROOT_PATH)))


def unstarted(args):
    print_results(filter(lambda x: not x.get('finish') and not x.get('episode'), list_data(ROOT_PATH)))


def match_target(args, datas=None):
    results = []
    # datas = completed(args, use_print=False)
    datas = [{'path': os.path.join(SUCCESS_TARGET_DIR, x)} for x in os.listdir(SUCCESS_TARGET_DIR)]
    datas = [dict(episodes=len([x for x in os.listdir(data['path']) if x.split('.')[-1] not in ['dl', 'log']]), **data)
             for data in datas]
    for data in datas:
        name = os.path.split(data['path'])[1]
        result = process.extractOne(name, target_directories, score_cutoff=90)
        if not result:
            continue
        results.append((list(reversed(result)), name, data))
    results.sort()
    datas = [
        (
            # truncatechars(name, 25),
            result[0],
            # truncatechars(result[1], 25),
            data['episodes'],
            format_uri(os.path.join(TARGET_DIR, result[1])),
            format_uri(data['path']),
        ) for result, name, data in results]
    table = SingleTable(datas)
    # for result, name, data in results:
    #     print('{}\t{}\t{}\t{}\tfile://{}'.format(name, result[0], result[1], data['episodes'], data['path']))
    print(table.table)


def save_success(args):
    if os.path.lexists(SUCCESS_DATA_PATH):
        success_data = json.load(open(SUCCESS_DATA_PATH))
    else:
        success_data = {}
    datas = [json.load(open(os.path.join(x['path'], '.anime.json'))) for x in completed(args, False, SUCCESS_TARGET_DIR)]
    for data in datas:
        url = data['url']
        if url not in success_data:
            success_data[url] = data
    json.dump(success_data, open(SUCCESS_DATA_PATH, 'w'))


def move_success(args):
    for anime in completed(args, False):
        name = os.path.split(anime['path'])[1]
        shutil.move(anime['path'], os.path.join(SUCCESS_TARGET_DIR, name))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    # TODO: los directorios incompletos deben ser comprobados manualmente.
    subparsers = parser.add_subparsers()
    add_subparser(subparsers, orphan)
    add_subparser(subparsers, completed)
    add_subparser(subparsers, failed)
    add_subparser(subparsers, incompleted)
    add_subparser(subparsers, pending)
    add_subparser(subparsers, unstarted)
    add_subparser(subparsers, match_target)
    add_subparser(subparsers, save_success)
    add_subparser(subparsers, move_success)
    args = parser.parse_args()
    args.func(args)
