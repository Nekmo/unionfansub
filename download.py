#!/usr/bin/env python
import glob
import json
import os
import threading
from subprocess import Popen

import subprocess

import time
from sys import argv

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


def save_config(config):
    with open(STATUS_FILE + '.bak', 'w') as f:
        f.write(open(STATUS_FILE, 'r').read())
    json.dump(config, open(STATUS_FILE, 'w'), sort_keys=True, indent=4, separators=(',', ': '))


def save_config_dir(path, config_dir):
    with file_semaphore:
        config = read_config()
        config[path] = config_dir
        save_config(config)


def _write_log_file(file, code, episode, output, error, dl, verbose=True, include_dl=False):
    with open(file, 'a') as f:
        f.write('{}{} ({}) episode: {}\n'.format(
            '{}:'.format(dl) if include_dl else '',
            'ERROR' if code else 'SUCCESS', code, episode
        ))
        if code or verbose:
            f.write('Stdout:\n{}\n'.format(output))
            f.write('Stderr:\n{}\n'.format(error))


def write_log(code, episode, output, error, dl, file=''):
    if code == 0:
        print('SUCCESS: {}:{}. {}'.format(dl, episode, file))
    else:
        print('ERROR: {}:{} (error code: {}) [file: {}]'.format(dl, episode, code, file))
        print('Stdout:\n{}'.format(output))
        print('Stderr:\n{}'.format(error))
    _write_log_file('{}.log'.format(dl), code, episode, output, error, dl)
    _write_log_file(STATUS_LOG_FILE, code, episode, output, error, dl, False, True)


def get_remotename(url):
    params = ['plowprobe']
    p = Popen(params + [url], stdin=subprocess.PIPE,
              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = p.communicate()
    output, error = output.decode('utf-8', 'ignore'), error.decode('utf-8', 'ignore')
    lines = output.split('\n')
    return lines[0][2:].rstrip(' ')


def is_mega(url):
    return '//mega.co.nz/' in url or '//mega.nz/' in url


def download_dl(episode, dl, mega_auth=False):
    links = json.load(open(dl))['links']
    if len(links) < episode:
        return None
    url = links[episode - 1]['link']
    directory = os.path.split(dl)[0]
    remotename = get_remotename(url)
    local_path = os.path.join(directory, remotename)
    if os.path.lexists(local_path) and os.path.getsize(local_path) > 1024 * 1024:
        print('El archivo {} ya existía en local.'.format(local_path))
        return True
    if mega_auth:
        params = ['/usr/bin/python2', os.path.join(os.getcwd(), 'mega_premium_download.py')]
    else:
        params = ['plowdown', '--temp-directory={}'.format(TMP)]
        if is_mega(url):
            params += ['--ignore-crc']
    p = Popen(params + [url], stdin=subprocess.PIPE,
              env=dict(AUTH_FILE=os.path.join(os.getcwd(), 'mega_auth'),
                       TEMP_DIR=TMP, **os.environ.copy()),
              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
              cwd=directory)
    output, error = p.communicate()
    output, error = output.decode('utf-8', 'ignore'), error.decode('utf-8', 'ignore')
    code = p.returncode
    if is_mega(url) and os.path.lexists(local_path) and not os.path.getsize(local_path) and not mega_auth:
        # Nos hemos quedado sin espacio gratuito. Es necesario usar credenciales.
        print('Nos hemos quedado sin espacio en mega!')
        return download_dl(episode, dl, True)
    elif is_mega(url) and os.path.lexists(local_path) and not os.path.getsize(local_path) and mega_auth:
        print('ERROR!!! Se está autenticando en Mega pero sigue habiendo una restricción de datos.')
        return False
    write_log(code, episode, output, error, dl, remotename)
    if code == 0:
        return True


def download_episode(dls, episode):
    for dl in dls:
        if download_dl(episode, dl):
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


def threaded_download_episodes(config, path, dls, daemon=True):
    with threads_semaphore:
        l = threading.Thread(target=_threaded_download_episodes, args=(config, path, dls))
        l.daemon = daemon
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
        threaded_download_episodes(config, path, dls, False)


if __name__ == '__main__':
    if len(argv) > 1 and 'reset_faileds' == argv[1]:
        config = read_config()
        for data in config.values():
            if data['finish'] and not data['success']:
                data['finish'] = False
        save_config(config)
    else:
        download()
