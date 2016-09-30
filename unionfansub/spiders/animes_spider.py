import re
import scrapy


def parse_url(url):
    if not url.startswith(url):
        return url
    url = re.sub('http://sh\.st/st/[0-9a-fA-F]{32}/out\.unionfansub\.com/[0-9]{5,10}/(.+)', r'https://\1', url)
    return url.replace('~~4dfl7SUCKS~~', '#')


class AnimesSpider(scrapy.Spider):
    name = "animes"

    def start_requests(self):
        urls = [
            'http://foro.unionfansub.com/announcements.php?aid=3',
        ]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        filename = 'animes.html'
        with open(filename, 'wb') as f:
            f.write(response.body)
        self.log('Saved file %s' % filename)
        for anime in response.css('.listado a'):
            yield scrapy.Request(response.urljoin(anime.css('::attr(href)').extract_first()),
                                 callback=self.parse_animes)

    def parse_animes(self, response):
        thumbs = []
        downloads = []
        post_content = response.css('.post_content')[0]
        spoilers = post_content.css('.spoil')
        languages = post_content.xpath('//strong[text()[contains(.,"Audio")]]/parent::*/span'
                                       '[contains(@class, "flag")]/@title').extract()
        fansubs = post_content.xpath('//strong[text()[contains(.,"Fansub")]]/parent::*/a/text()').extract()
        target = post_content.xpath('//strong[text()[contains(.,"Público")]]/parent::*/a/text()').extract()
        themes = post_content.xpath('//strong[text()[contains(.,"Ambientación")]]/parent::*/a/text()').extract()
        genres = post_content.xpath('//strong[text()[contains(.,"Género")]]/parent::*/a/text()').extract()
        director = post_content.xpath('//strong[text()[contains(.,"Director")]]/parent::*/text()').extract_first()
        episodes = post_content.xpath('//span[@class[contains(.,"episodios")]]/text()').extract_first()
        duration = post_content.xpath('//strong[text()[contains(.,"Duración")]]/parent::*/text()').extract_first()
        year = post_content.xpath('//span[@class[contains(.,"produccion")]]/text()').extract_first()
        source = post_content.xpath('//strong[text()[contains(.,"Video")]]/parent::*/*[@class[contains(., '
                                    '"source")]]/@title').extract_first()
        resolution = post_content.xpath('//strong[text()[contains(.,"Video")]]/parent::*/*[@class[contains(., '
                                        '"resolucion")]]/text()').extract_first()
        codec = post_content.xpath('//strong[text()[contains(.,"Video")]]/parent::*/*[@class[contains(., '
                                   '"codec")]]/text()').extract_first()
        container = post_content.xpath('//strong[text()[contains(.,"Contenedor")]]/parent::*/text()').extract_first()
        xinfo = post_content.xpath('//strong[text()[contains(.,"Contenedor")]]/parent::*/*[@class'
                                   '[contains(.,"xinfo")]]/text()').extract_first()
        password = post_content.xpath('//strong[text()[contains(.,"Contraseña")]]/parent::*/text()').extract_first()
        torrent_files = post_content.xpath('//*[@id="filelist"]/tr/td[not(@style)]/text()').extract()
        torrent_file_sizes = post_content.xpath('//*[@id="filelist"]/tr/td[@style]/text()').extract()
        torrents = [{'name': y, 'size': torrent_file_sizes[x]} for x, y in enumerate(torrent_files)]
        subs = post_content.css('.subtitulos .flag::attr(title)').extract()
        for spoiler in spoilers:
            images = spoiler.css('a::attr(href)').extract()
            if images and images[0].startswith('http://galeria.unionfansub.com'):
                thumbs.extend(images)
            else:
                name = spoiler.css('h5::text').extract_first()
                links = spoiler.css('a')
                downloads.append({'name': name,
                                  'links': [{'name': x.css('::text').extract_first(),
                                             'link': parse_url(x.css('::attr(href)').extract_first())} for x in links]})
        alts = response.css('a[title="Versión alternativa"]::attr(href)').extract()
        recs = response.css('a[title="Versión recomendada"]::attr(href)').extract()
        alts += recs
        name = response.css('.ficha h2::text').extract_first()
        original = response.xpath('//strong[text()="Título original: "]/parent::div/text()').extract_first()
        yield {
            'url': response.url,
            'status': response.css('.estado::text').extract_first(),
            'fansubs': fansubs,
            'target': target,
            'themes': themes,
            'genres': genres,
            'episodes': episodes,
            'director': director,
            'duration': duration,
            'year': year,
            'source': source,
            'resolution': resolution,
            'codec': codec,
            'container': container,
            'xinfo': xinfo,
            'password': password,
            'torrents': torrents,
            'name': name.strip(' ') if name else None,
            'original_name': original.strip(' ') if original else None,
            'downloads': downloads, 'thumbs': thumbs,
            'languages': languages,
            'subtitles': subs,
            'recs': [response.urljoin(rec) for rec in recs],
            'alternatives': [response.urljoin(alt) for alt in alts],
        }
        for alt in alts:
            yield scrapy.Request(response.urljoin(alt), callback=self.parse_animes)
