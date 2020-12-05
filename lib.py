import datetime
import json
import urllib.request
import logging
import os
from urllib.error import HTTPError
from urllib.parse import urlsplit, urlencode
from urllib.parse import parse_qsl as queryparse
from time import sleep
from pathlib import Path
from typing import List


# https://developer.yle.fi/tutorial-listing-programs/index.html
# https://developer.yle.fi/en/tutorials/index.html
# https://developer.yle.fi/en/api/index.html

class AppException(Exception):
    pass


class NoResultsFound(AppException):
    url = ""

    def __init__(self, url: str):
        self.url = url

    def __str__(self) -> str:
        return f"error: no results found for {self.url}"


class Category(dict):
    """
    Category
    """
    id = None
    name = None

    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name

    def __str__(self) -> str:
        return f"{self.id: >15} {self.name}"

    def __dict__(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
        }


class Season(dict):
    """
    Season
    """
    id = None
    name = None
    season = 0

    def __init__(self, id: str, season: int, name: str):
        self.id = id
        self.season = season
        self.name = name

    def __str__(self) -> str:
        return f"{self.id}\t\t[S{self.season:02}] {self.name}"

    def __dict__(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "s": self.season,
        }


class Episode(dict):
    """
    Episode
    """
    id = None
    name = ""
    season = None
    episode = None
    descr = None
    start = datetime.datetime.now()
    end = datetime.datetime.now()
    availableHuman = datetime.timedelta(seconds=0)

    def __init__(self, id: str, season: int, episode: int, name: str, descr: str,
                 start: datetime.datetime = datetime.datetime.now(),
                 end: datetime.datetime = datetime.datetime.now()
                 ):
        self.id = id
        self.season = season
        self.episode = episode
        self.name = name
        self.descr = descr
        self.start = start
        self.end = end
        self.availableHuman = self.end - datetime.datetime.now().replace(microsecond=0)

    def __str__(self) -> str:
        available = f"{self.start.isoformat()} - {self.end.isoformat()}, {self.availableHuman}"

        return f"S{self.season:02}E{self.episode:02} [{self.id}] {available}\n  {self.name}\n  {self.descr}"

    def __dict__(self) -> dict:
        return {
            "s": self.season,
            "e": self.episode,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "id": self.id,
            "name": self.name,
            "availableSeconds": int(self.availableHuman.total_seconds()),
            "availableHuman": self.availableHuman.__str__(),
            "descr": self.descr,
        }


CategoryList = List[Category]


class Series(dict):
    """
    Series
    """
    id = None
    name = None
    cats = None

    def __init__(self, id: str, name: str, cats: CategoryList = []):
        self.id = id
        self.name = name
        self.cats = cats

    def __str__(self) -> str:
        cats = []
        for c in self.cats:
            cats.append(f"{c.name} <{c.id}>")

        return f"{self.id: >10} {self.name}\n\t\t[{', '.join(cats)}]"

    def __dict__(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "cats": self.cats,
        }


class Program(dict):
    """
    Program
    """
    id = ""
    name = ""
    descr = None
    start = datetime.datetime.now()
    end = datetime.datetime.now()
    availableHuman = datetime.timedelta(seconds=0)
    cats = []

    def __init__(self, id: str, name: str, descr: str,
                 start: datetime.datetime = datetime.datetime.now(),
                 end: datetime.datetime = datetime.datetime.now(),
                 cats: CategoryList = []
                 ):
        self.id = id
        self.name = name
        self.descr = descr
        self.start = start
        self.end = end
        self.cats = cats
        self.availableHuman = self.end - datetime.datetime.now().replace(microsecond=0)

    def __str__(self) -> str:
        available = f"{self.start.isoformat()} - {self.end.isoformat()}, {self.availableHuman}"

        catnames = []
        for c in self.cats:
            catnames.append(c.name)

        catids = []
        for c in self.cats:
            catids.append(c.id)

        out = f"[{self.id}] {available}\n    {self.name}\n    {self.descr}\n"
        out += f"    - Categories: [{', '.join(catnames)}]\n"
        out += f"    - Category IDs: [{', '.join(catids)}]\n"

        return out

    def __dict__(self) -> dict:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "id": self.id,
            "name": self.name,
            "availableSeconds": int(self.availableHuman.total_seconds()),
            "availableHuman": self.availableHuman.__str__(),
            "descr": self.descr,
            "categories": self.cats,
        }


SeasonList = List[Season]
EpisodeList = List[Episode]
SeriesList = List[Series]
ProgramList = List[Program]


class YleAreena:
    """
    HTTP REST Client
    """
    appid = None
    appkey = None
    log = None
    cacheDir = ".cache"
    defaultCacheTime = datetime.timedelta(minutes=15)
    apidomain = "external.api.yle.fi"
    areenadomain = "areena.yle.fi"

    def __init__(self, log: logging.Logger, appid: str, appkey: str):
        self.log = log
        self.appid = appid
        self.appkey = appkey

        if not os.path.isdir(self.cacheDir):
            # Create directory
            Path(self.cacheDir).mkdir(parents=True, exist_ok=True)

    def _qstr(self, q: dict) -> str:
        """
        Dictionary to URL query string
        """
        return "?" + urlencode(q)

    def _dl_url(self, url: str, cachetime: datetime.timedelta = None) -> dict:
        """
        Download JSON from given URL and cache the result
        """

        # Remove all from url except path and query string
        urlS = urlsplit(url)
        urltmp: str = urlS.path.lstrip("/").replace("/", "-")
        urlQ: dict = dict(queryparse(urlS.query))
        if 'app_id' in urlQ:
            del urlQ['app_id']
        if 'app_key' in urlQ:
            del urlQ['app_key']

        urltmp += self._qstr(urlQ)

        if cachetime is None:
            cachetime = self.defaultCacheTime

        cachefile = os.path.join(self.cacheDir, urltmp + ".json")

        if os.path.isfile(cachefile):
            # Cache file exists
            now = datetime.datetime.now()
            fmodtime = datetime.datetime.fromtimestamp(os.path.getmtime(cachefile))

            if (fmodtime - now) <= cachetime:
                # Cache is not expired yet. Read from cache
                self.log.debug(f"Getting <URL: {url} > from cache")
                with open(cachefile, "r", encoding="utf8") as f:
                    return json.loads(f.read())

        data: dict = {}

        self.log.debug(f"Getting <URL: {url} >")
        try:
            # Get from HTTP
            sleep(0.2)
            with urllib.request.urlopen(url) as response:
                if response.code != 200:
                    raise ValueError("url couldn't be loaded")
                if response.headers.get_content_type() != "application/json":
                    raise ValueError("invalid content type")

                resp: bytes = response.read()

                if os.path.isfile(cachefile):
                    # Destroy stale cache
                    os.unlink(cachefile)

                with open(cachefile, "wb") as f:
                    f.write(resp)

                data = json.loads(resp)
        except HTTPError as e:
            raise e

        return data

    def _get_title(self, raw: dict) -> str:
        """
        Get title / description in some language
        :param raw:
        :return:
        """

        languages: list = ['fi', 'en', 'sv']

        for i in languages:
            if i in raw:
                return raw[i]

        return raw[list(raw.keys())[0]]

    def _get_date(self, raw: str) -> datetime.datetime:
        d = datetime.datetime.strptime(raw, "%Y-%m-%dT%H:%M:%S%z")
        return datetime.datetime(d.year, d.month, d.day, d.hour, d.minute, d.second)

    def getCategories(self) -> CategoryList:
        cachetime = datetime.timedelta(days=1)
        items: list = []
        itemscount: int = None

        offset = 0
        limit = 100

        while len(items) != itemscount:
            url = f"https://{self.apidomain}/v1/programs/categories.json" + self._qstr({
                "app_id": self.appid,
                "app_key": self.appkey,
                "limit": limit,
                "offset": offset,
            })

            resp = self._dl_url(url, cachetime)
            meta = resp['meta']

            if itemscount is None:
                itemscount = meta['count']

            offset += limit

            for i in resp['data']:
                items.append(Category(i['id'], i['title']['fi']))

        return items

    def getServices(self) -> list:
        cachetime = datetime.timedelta(days=1)
        items = []
        itemscount = None

        offset = 0
        limit = 100

        while len(items) != itemscount:
            url = f"https://{self.apidomain}/v1/programs/services.json" + self._qstr({
                "app_id": self.appid,
                "app_key": self.appkey,
                "limit": limit,
                "offset": offset,
            })

            resp = self._dl_url(url, cachetime)
            meta = resp['meta']

            if itemscount is None:
                itemscount = meta['count']

            offset += limit

            for i in resp['data']:
                items.append(i)

        return items

    def getSchedules(self) -> list:
        cachetime = datetime.timedelta(days=1)
        items = []
        itemscount = None

        offset = 0
        limit = 100

        while len(items) != itemscount:
            url = f"https://{self.apidomain}/v1/programs/schedules.json" + self._qstr({
                "app_id": self.appid,
                "app_key": self.appkey,
                "limit": limit,
                "offset": offset,
            })

            resp = self._dl_url(url, cachetime)
            meta = resp['meta']

            if itemscount is None:
                itemscount = meta['count']

            offset += limit

            for i in resp['data']:
                items.append(i)

        return items

    def getSeries(self, category_id_list: list = [], exclude_categories_list: list = []) -> SeriesList:
        """
        Search series
        :param category_id_list: optional categories
        :param exclude_categories_list: optional categories not to be included
        :return:
        """

        cachetime = datetime.timedelta(hours=4)

        items = []
        itemscount = None

        offset = 0
        limit = 100
        order = ["episode.hash:asc", "publication.starttime:asc", "title.fi:asc"]

        while len(items) != itemscount and offset <= 15000:
            q = {
                "app_id": self.appid,
                "app_key": self.appkey,
                "availability": "ondemand",
                "type": "program",
                "limit": limit,
                "offset": offset,
                "order": ",".join(order),
            }

            categories = []

            if len(category_id_list) > 0:
                categories.extend(category_id_list)

            if len(exclude_categories_list) > 0:
                # Exclude (Add '-' to front of category)
                categories.extend(map(lambda x: f"-{x}", exclude_categories_list))

            if len(categories) > 0:
                # Add to query
                q["category"] = ",".join(categories)

            url = f"https://{self.apidomain}/v1/series/items.json" + self._qstr(q)

            resp = self._dl_url(url, cachetime)
            meta = resp['meta']

            if itemscount is None:
                itemscount = meta['count']

            offset += limit

            for i in resp['data']:
                if len(i['title']) == 0:
                    continue

                categories = []
                for c in i['subject']:
                    categories.append(Category(c['id'], self._get_title(c['title'])))

                items.append(Series(
                    i['id'],
                    self._get_title(i['title']),
                    categories,
                ))

        return items

    def getEpisodesBySeriesId(self, series_id: str, season_id: str = None) -> EpisodeList:
        """
        List episodes
        :param series_id: for example 1-4555656
        :param season_id: optional season ID, for example 1-4553280
        :return:
        """

        cache_time = datetime.timedelta(hours=4)

        offset = 0
        limit = 100

        order = ["episode.hash:asc", "publication.starttime:asc", "title.fi:asc"]

        q = {
            "app_id": self.appid,
            "app_key": self.appkey,
            "publisher": "yle-areena",
            "type": "program",
            "availability": "ondemand",
            "offset": offset,
            "limit": limit,
            "order": ",".join(order),
        }

        if season_id is not None:
            q['season'] = season_id

        url = f"https://{self.areenadomain}/api/programs/v1/episodes/{series_id}.json" + self._qstr(q)
        resp = self._dl_url(url, cache_time)
        data = resp['data']

        episodes: EpisodeList = []
        if len(data) == 0:
            return episodes

        for ep in data:
            start = None  # Date and time when episode became available
            end = None  # Date and time when episode becomes unavailable

            for p in ep['publicationEvent']:
                if 'yle-areena' in p['service']['id'] and 'yle-areena' in p['publisher'][0]['id']:
                    start = self._get_date(p['startTime'])
                    if 'endTime' in p:
                        end = self._get_date(p['endTime'])
                    break

            if end is None:
                # End was not given, use custom time
                end = datetime.datetime.now() + datetime.timedelta(weeks=52 * 10)

            episodes.append(Episode(
                ep['id'],
                ep['partOfSeason']['seasonNumber'],
                ep['episodeNumber'],
                self._get_title(ep['title']),
                self._get_title(ep['description']),
                start,
                end,
            ))

        return episodes

    def getSeasonsById(self, id: str) -> SeasonList:
        """
        List season IDs for certain series
        :param id:
        :return:
        """

        cachetime = datetime.timedelta(hours=4)

        offset = 0
        limit = 100

        q = {
            "app_id": self.appid,
            "app_key": self.appkey,
            "offset": offset,
            "limit": limit,
        }

        url = f"https://{self.apidomain}/v1/series/items/{id}.json" + self._qstr(q)

        resp = self._dl_url(url, cachetime)
        data = resp['data']
        seasons = []
        for season in data['season']:
            seasons.append(Season(
                season['id'],
                season['seasonNumber'],
                self._get_title(season['title']),
            ))

        return seasons

    def searchProgramById(self, id: str) -> Program:
        """
        Search programs by given ID

        :param id:
        :return:
        """
        cache_time = datetime.timedelta(hours=4)

        q = {
            "app_id": self.appid,
            "app_key": self.appkey,
        }

        url = f"https://{self.apidomain}/v1/programs/items/{id}.json" + self._qstr(q)

        resp = self._dl_url(url, cache_time)
        data = resp['data']

        start = None  # Date and time when episode become available
        end = None  # Date and time when episode becomes unavailable

        for p in data['publicationEvent']:
            if 'yle-areena' in p['service']['id'] and 'yle-areena' in p['publisher'][0]['id']:
                start = self._get_date(p['startTime'])
                end = self._get_date(p['endTime'])
                break

        categories = []
        for c in data['subject']:
            categories.append(Category(c['id'], self._get_title(c['title'])))

        return Program(
            data['id'],
            self._get_title(data['title']),
            self._get_title(data['description']),
            start,
            end,
            categories,
        )

    def searchPrograms(self, query: str = None, id: str = None, series: str = None,
                       categories_id_list: list = [], exclude_categories_list: list = []) -> ProgramList:
        cache_time = datetime.timedelta(hours=4)
        """
        Search for program(s)
        
        """

        offset = 0
        limit = 100

        q = {
            "app_id": self.appid,
            "app_key": self.appkey,
            "publisher": "yle-areena",
            "availability": "ondemand",
            "limit": limit,
            "offset": offset,
        }

        if query is not None:
            q['q'] = query

        if id is not None:
            q['id'] = id

        if series is not None:
            q['series'] = series

        categories = []

        if len(categories_id_list) > 0:
            categories.extend(categories_id_list)

        if len(exclude_categories_list) > 0:
            # Exclude (Add '-' to front of all categories)
            categories.extend(map(lambda x: f"-{x}", exclude_categories_list))

        if len(categories) > 0:
            # Add to query
            q["category"] = ",".join(categories)

        url = f"https://{self.apidomain}/v1/programs/items.json" + self._qstr(q)

        programs: ProgramList = []
        resp = self._dl_url(url, cache_time)
        for data in resp['data']:
            if not data['title']:
                continue

            if not data['description']:
                data['description'] = {"fi": "-"}

            start = None  # Date and time when episode become available
            end = None  # Date and time when episode becomes unavailable

            for p in data['publicationEvent']:
                if 'yle-areena' in p['service']['id'] and 'yle-areena' in p['publisher'][0]['id']:
                    start = self._get_date(p['startTime'])
                    if 'endTime' in p:
                        end = self._get_date(p['endTime'])
                    break

            category_ids_list: List[Category] = []
            for c in data['subject']:
                category_ids_list.append(Category(c['id'], self._get_title(c['title'])))

            if end is None:
                # End was not given, use custom time
                end = datetime.datetime.now() + datetime.timedelta(weeks=52 * 10)

            programs.append(Program(
                data['id'],
                self._get_title(data['title']),
                self._get_title(data['description']),
                start,
                end,
                category_ids_list
            ))

        return programs
