import argparse
import json
import os

from fuzzywuzzy import process

ROOT_PATH = '/media/nekraid02/Downloads'
TARGET_DIR = '/media/nekhd/Anime'
DOWNLOAD_CONFIG = os.path.expanduser('~/.config/unionfansub-download.json')
SUCCESS_DATA_PATH = os.path.expanduser('~/.config/unionfansub-success.json')

target_directories = os.listdir(TARGET_DIR)


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


def completed(args, use_print=True):
    values = filter(lambda x: x.get('finish') and x.get('success'), list_data(ROOT_PATH))
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


def match_target(args):
    results = []
    for data in completed(args, use_print=False):
        name = os.path.split(data['path'])[1]
        result = process.extractOne(name, target_directories, score_cutoff=90)
        if not result:
            continue
        results.append((list(reversed(result)), name, data))
    results.sort()
    for result, name, data in results:
        print('{}\t{}\t[{}]\t\tfile://{}'.format(name, result, data['episodes'], data['path']))


def save_success(args):
    if os.path.lexists(SUCCESS_DATA_PATH):
        success_data = json.load(open(SUCCESS_DATA_PATH))
    else:
        success_data = {}
    datas = [json.load(open(os.path.join(x['path'], '.anime.json'))) for x in completed(args, False)]
    for data in datas:
        url = data['url']
        if url not in success_data:
            success_data[url] = data
    json.dump(success_data, open(SUCCESS_DATA_PATH, 'w'))


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
    args = parser.parse_args()
    args.func(args)
