import json

import os
from collections import Counter

import uuid
from file_cache.csv_key_value import KeyValueCache
from file_cache.file import FileCache
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from spice_api import spice

MIN_MATCHING_RATIO = 80
ANIME_LIST_CACHE = '%2Fmedia%2Fnekraid01%2FAnime%2C%2Fmedia%2Fnekraid02%2FAnime'
OUTPUT = '/media/nekraid02/Downloads'

creds = spice.load_auth_from_file('mal_auth')
words_cache = KeyValueCache('mal')
file_cache = FileCache('mal')
al_cache = FileCache('anime-list')


def escape_name(name):
    return name.replace('/', '⁄')


def list_contains(queries, elements):
    def match_element(qs, el):
        for query in qs:
            if query in el:
                return True
    if not isinstance(queries, (list, tuple)):
        queries = [queries]
    for element in elements:
        if match_element(queries, element):
            return True
    return False


def search(query):
    query = query.strip(' ')
    cache = words_cache.load(query)
    if cache:
        # Load from cache
        files = [int(x) for x in cache['value'].split(',') if x]
        return [file_cache.load(x) for x in files]
    results = spice.search(query, spice.get_medium('anime'), creds)
    results = [result.to_json() for result in results]
    # Save to cache
    words_cache.save(query, ','.join([str(x['id']) for x in results]))
    for result in results:
        file_cache.save(result, result['id'], 'json')
    return results


def get_best_result(results, name):
    if not results:
        return
    titles = [result['title'] for result in results]
    title_result = process.extractOne(name, titles)[0]
    for result in results:
        if result['title'] == title_result:
            return result
    return None


def sort_anime_datas(data):
    score = 0
    if data['status'] == 'Activo':
        return 0
    if list_contains(['Castellano'], data['subtitles']):
        score += 3
    if list_contains(['Castellano'], data['languages']):
        score += 2
    if list_contains(['Japonés'], data['languages']):
        score += 1
    return score


class AnimeData(dict):
    def __init__(self, data, mal_title):
        super(AnimeData, self).__init__(**data)
        self.name = data['name']
        self.directory = self.get_path()
        self['mal_title'] = mal_title

    def get_path(self, i=0):
        if i:
            name = '{} ({})'.format(self.name, i)
        else:
            name = self.name
        return os.path.join(OUTPUT, escape_name(name))

    def create(self):
        self.create_dirs()
        self.create_content_file()
        self.create_downloads()
        self.create_data()

    def create_content_file(self):
        if not self['mal_title']:
            return
        with open(os.path.join(self.directory, '.content.yml'), 'w') as f:
            f.write("animes: {}\n".format(self['mal_title']))

    def create_dirs(self):
        i = 0
        while True:
            self.directory = self.get_path(i)
            if os.path.lexists(self.directory):
                i += 1
                continue
            os.makedirs(self.directory)
            break

    def create_downloads(self):
        names = []
        for download in self['downloads']:
            name = download['name']
            if name in names:
                name += '{} ({})'.format(name, Counter(names)[name])
            names.append(download['name'])
            path = os.path.join(self.directory, '{}.dl'.format(escape_name(name)))
            json.dump(download, open(path, 'w'))

    def create_data(self):
        path = os.path.join(self.directory, '.anime.json')
        json.dump(self, open(path, 'w'))


class Anime(object):
    _mal = None

    def __init__(self, data):
        self.datas = [data]
        self.name = data['name']
        self.original_name = data['original_name']

    def add(self, data):
        self.datas.append(data)

    def matching(self, data):
        return fuzz.ratio(data['name'], self.datas[0]['name'])

    def mal(self):
        if self._mal is None:
            for name in filter(lambda x: x, (self.name, self.original_name)):
                results = search(self.name)
                if not results:
                    continue
                self._mal = get_best_result(results, name)
                break
        return self._mal

    def recs(self):
        recs = set()
        for data in self.datas:
            recs.update(data['recs'])
        return recs

    @property
    def mal_title(self):
        return (self.mal() or {}).get('title')

    def get_data_ratio(self, data=None, recs=None):
        data = data or self.get_best()
        if data is None:
            return -1
        recs = recs or self.recs()
        return sort_anime_datas(data) + (2 if data['url'] in recs else 0)

    def get_best(self):
        recs = self.recs()
        datas = sorted(self.datas, reverse=True, key=lambda x: self.get_data_ratio(x, recs))
        if datas and self.get_data_ratio(datas[0], recs):
            return AnimeData(datas[0], self.mal_title)

    def get_urls(self):
        return [data['url'] for data in self.datas]

    def __repr__(self):
        return '{} ({})'.format(self.name, len(self.datas))

    def __lt__(self, other):
        return self.name < other.name


def get_local_animes():
    return al_cache.load(ANIME_LIST_CACHE)['tvshows']


def get_animes_data(links, animes_by_link):
    for link in links:
        anime_data = animes_by_link.get(link)
        if not anime_data or not anime_data.get('name'):
            # Invalid data or url
            continue
        yield anime_data


def get_animes_group(datas):
    if not datas:
        return []
    animes = [Anime(datas[0])]
    for data in datas[1:]:
        ratios = {anime.matching(data): anime for anime in animes}
        best = sorted(ratios, reverse=True)[0]
        if best >= MIN_MATCHING_RATIO:
            ratios[best].add(data)
        else:
            animes.append(Anime(data))
    return animes


def get_by_anime(data):
    groups = {}
    animes_by_link = {}
    for anime in data:
        my_url = anime['url']
        animes_by_link[my_url] = anime
        similars = groups.get(my_url, set())
        similars.update(anime['alternatives'])
        similars.add(my_url)
        for url in anime['alternatives'] + [my_url]:
            groups[url] = similars
    groups = set([frozenset(link) for link in groups.values()])
    # TODO: esta lógica hay que hacerla más compleja. Hacer un matching entre títulos
    # para ver si de verdad son la misma obra. Crear tantos animes como títulos similares
    # en el conjunto.
    animes = []
    for group in groups:
        datas = list(get_animes_data(group, animes_by_link))
        animes_group = get_animes_group(datas)
        animes.extend(animes_group)
    return animes

    # return [Anime([animes_by_link[link] for link in group if link in animes_by_link]) for group in groups]
    # print(len(groups))
    # print(groups)


def local_matching(animes):
    local = get_local_animes()
    for anime in animes:
        mal_title = anime.mal_title
        local_match = list(filter(lambda x: x['about']['title'] == mal_title, local))
        if local_match:
            yield anime


def main():
    json_data = json.load(open('anime.json'))
    animes = sorted(get_by_anime(json_data))
    matchs = list(local_matching(animes))
    missings = set(animes) - set(matchs)
    mal_titles = {}
    for missing in missings:
        best = missing.get_best()
        if best is None:
            continue
        title = missing.mal_title
        if not title:
            title = uuid.uuid4().hex
        if title in mal_titles:
            print('Duplicado! {} - Ratios: {} <> {}'.format(title, missing.get_data_ratio(best),
                                                            mal_titles[title].get_data_ratio()))
        if title in mal_titles and missing.get_data_ratio(best) < mal_titles[title].get_data_ratio():
            continue
        mal_titles[title] = missing
    for mal_title in mal_titles.values():
        best = mal_title.get_best()
        best.create()
        # print(missing.name, missing.get_urls() if not best else [best['languages'], best['subtitles']])

        # Comprobar duplicados y descargar el de mejor ratio/cualidades? valorar en función número.


if __name__ == '__main__':
    main()


