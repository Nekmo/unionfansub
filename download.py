#!/usr/bin/env python
import glob
import json
import os
import threading
from subprocess import Popen

import subprocess

import time

from filelock import FileLock, SoftFileLock

OUTPUT = '/media/nekraid02/Downloads'
STATUS_FILE = os.path.expanduser('~/.config/unionfansub-download.json')
STATUS_LOG_FILE = os.path.expanduser('~/.config/unionfansub-download.log')
TMP = '/media/datos/tmp/'
THREADS = 5

threads_semaphore = threading.BoundedSemaphore(value=THREADS)
file_semaphore = threading.BoundedSemaphore(value=1)


def sort_dls(file):
    data = open(file).read()
    if '1fichier' in data:
        return 2
    elif 'mega' in data:
        return 1
    return -1


def default_config_dir():
    return {'episode': 0, 'episodes': 0, 'success': False, 'finish': False}


def get_directories():
    return [os.path.join(OUTPUT, x) for x in sorted(os.listdir(OUTPUT))]


def read_config():
    return json.load(open(STATUS_FILE))


def get_episodes_len(dl):
    return len(json.load(open(dl))['links'])


def save_config_dir(path, config_dir):
    with file_semaphore:
        config = read_config()
        config[path] = config_dir
        json.dump(config, open(STATUS_FILE, 'w'), sort_keys=True, indent=4, separators=(',', ': '))


def _write_log_file(file, code, episode, output, error, dl, verbose=True, include_dl=False):
    with open(file, 'a') as f:
        f.write('{}{} ({}) episode: {}\n'.format(
            '{}:'.format(dl) if include_dl else '',
            'ERROR' if code else 'SUCCESS', code, episode
        ))
        if code or verbose:
            f.write('Stdout:\n{}\n'.format(output))
            f.write('Stderr:\n{}\n'.format(error))


def write_log(code, episode, output, error, dl):
    if code == 0:
        print('SUCCESS: {}:{}'.format(dl, episode))
    else:
        print('ERROR: {}:{} (error code: {})'.format(dl, episode, code))
        print('Stdout:\n{}'.format(output))
        print('Stderr:\n{}'.format(error))
    _write_log_file('{}.log'.format(dl), code, episode, output, error, dl)
    _write_log_file(STATUS_LOG_FILE, code, episode, output, error, dl, False)


def download_episode(dls, episode):
    for dl in dls:
        links = json.load(open(dl))['links']
        directory = os.path.split(dl)[0]
        if len(links) < episode:
            continue
        url = links[episode - 1]['link']
        p = Popen(['plowdown', '--temp-directory={}'.format(TMP), url], stdin=subprocess.PIPE,
                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                  cwd=directory)
        output, error = p.communicate()
        output, error = output.decode('utf-8'), error.decode('utf-8')
        code = p.returncode
        write_log(code, episode, output, error, dl)
        if code == 0:
            return True
    return False


def download_episodes(config, path, dls):
    episodes = get_episodes_len(dls[0])
    config_dir = config.get(path, default_config_dir())
    config_dir['episodes'] = episodes
    save_config_dir(path, config_dir)
    for episode in range(config_dir['episode'] + 1, episodes + 1):
        if download_episode(dls, episode):
            config_dir['episode'] += 1
            save_config_dir(path, config_dir)
        else:
            config_dir['finish'] = True
            save_config_dir(path, config_dir)
            return
    config_dir['finish'] = True
    config_dir['success'] = True
    save_config_dir(path, config_dir)


def _threaded_download_episodes(config, path, dls):
    with threads_semaphore:
        download_episodes(config, path, dls)


def threaded_download_episodes(config, path, dls):
    with threads_semaphore:
        l = threading.Thread(target=_threaded_download_episodes, args=(config, path, dls))
        l.daemon = True
        l.start()
        time.sleep(1)


def download():
    config = read_config()
    for path in get_directories():
        if path in config and config[path].get('finish'):
            continue
        print('********* {}'.format(path))
        dls = filter(lambda x: sort_dls(x) >= 0, [os.path.join(path, x) for x in glob.glob1(path, '*.dl')])
        dls = list(sorted(dls, key=sort_dls, reverse=True))
        if not dls:
            continue
        # download_episodes(config, path, dls)
        threaded_download_episodes(config, path, dls)


if __name__ == '__main__':
    download()

