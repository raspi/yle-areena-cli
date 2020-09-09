import datetime
import json
import time
import urllib.request
import logging
import os
import sys
from urllib.error import HTTPError
from urllib.parse import urlsplit, urlencode, unquote, urljoin, urlunparse
from urllib.parse import parse_qsl as queryparse
from pprint import pprint
from time import sleep
from base64 import urlsafe_b64decode
from base64 import urlsafe_b64encode
from pathlib import Path
from typing import List


# https://developer.yle.fi/tutorial-listing-programs/index.html
# https://developer.yle.fi/en/tutorials/index.html
# https://developer.yle.fi/en/api/index.html

class AppException(Exception):
    pass


class NotFound(AppException):
    url = ""

    def __init__(self, url: str):
        self.url = url

    def __str__(self):
        return f"error: 404: {self.url}"


class Category:
    """
    Category
    """
    id = None
    name = None

    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name

    def __str__(self):
        return f"{self.id: >15} {self.name}"


class Season:
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

    def __str__(self):
        return f"{self.id}\t\t[S{self.season:02}] {self.name}"

    def __dict__(self):
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

    def __str__(self):
        available = f"{self.start.isoformat()} - {self.end.isoformat()}, {self.availableHuman}"

        return f"S{self.season:02}E{self.episode:02} [{self.id}] {available}\n  {self.name}\n  {self.descr}"

    def __dict__(self):
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


class Series:
    """
    Series
    """
    id = None
    name = None

    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name

    def __str__(self):
        return f"{self.id}\t\t{self.name}"


SeasonList = List[Season]
EpisodeList = List[Episode]
SeriesList = List[Series]
CategoryList = List[Category]


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

    def _qstr(self, q: dict):
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
        urltmp = urlS.path.lstrip("/").replace("/", "-")
        urlQ = dict(queryparse(urlS.query))
        if 'app_id' in urlQ:
            del urlQ['app_id']
        if 'app_key' in urlQ:
            del urlQ['app_key']

        urltmp += urlsafe_b64encode(self._qstr(urlQ).encode('utf8')).decode('utf8')

        if cachetime is None:
            cachetime = self.defaultCacheTime

        cachefile = os.path.join(self.cacheDir, urltmp + ".json")

        if os.path.isfile(cachefile):
            now = datetime.datetime.now()
            fmodtime = datetime.datetime.fromtimestamp(os.path.getmtime(cachefile))

            if (fmodtime - now) <= cachetime:
                # Read from cache
                self.log.debug(f"Getting <URL: {url} > from cache")
                with open(cachefile, "r", encoding="utf8") as f:
                    return json.loads(f.read())

        sleep(0.2)
        data = None

        self.log.debug(f"Getting <URL: {url} >")
        try:
            with urllib.request.urlopen(url) as response:
                if response.code != 200:
                    raise ValueError("url couldn't be loaded")
                if response.headers.get_content_type() != "application/json":
                    raise ValueError("invalid content type")

                resp = response.read()

                if os.path.isfile(cachefile):
                    # Destroy stale cache
                    os.unlink(cachefile)

                with open(cachefile, "wb") as f:
                    f.write(resp)

                data = json.loads(resp)
        except HTTPError as e:
            raise NotFound(e.url)

        return data

    def _get_title(self, raw: dict) -> str:
        if 'fi' in raw:
            return raw['fi']
        elif 'en' in raw:
            return raw['en']
        else:
            return raw[raw.keys()[0]]

    def _get_date(self, raw: str) -> datetime.datetime:
        return datetime.datetime.strptime(raw, "%Y-%m-%dT%H:%M:%S+03:00")

    def getCategories(self) -> CategoryList:
        cachetime = datetime.timedelta(days=1)
        items = []
        itemscount = None

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

    def getSeries(self, catids: list = [], excludeCats: list = []) -> SeriesList:
        cachetime = datetime.timedelta(days=1)
        items = []
        itemscount = None

        offset = 0
        limit = 100

        while len(items) != itemscount and offset <= 15000:
            q = {
                "app_id": self.appid,
                "app_key": self.appkey,
                "limit": limit,
                "offset": offset,
                "availability": "ondemand",
            }

            categories = []

            if len(catids) > 0:
                categories.extend(catids)

            if len(excludeCats) > 0:
                # Exclude (Add '-' to front of category)
                categories.extend(map(lambda x: f"-{x}", excludeCats))

            if len(categories) > 0:
                q["category"] = ",".join(categories)

            url = f"https://{self.apidomain}/v1/series/items.json" + self._qstr(q)

            resp = self._dl_url(url, cachetime)
            meta = resp['meta']

            if itemscount is None:
                itemscount = meta['count']

            offset += limit

            for i in resp['data']:
                title = ""
                if 'fi' in i['title']:
                    title = i['title']['fi']
                elif 'en' in i['title']:
                    title = i['title']['en']
                else:
                    title = i['title'][i['title'].keys()[0]]
                items.append(Series(i['id'], title))

        return items

    def getEpisodesBySeriesId(self, seriesId: str, seasonId: str = None) -> EpisodeList:
        """
        List episodes
        :param seriesId: for example 1-4555656
        :param seasonId: optional season ID, for example 1-4553280
        :return:
        """

        cachetime = datetime.timedelta(hours=4)

        offset = 0
        limit = 100

        order = ["episode.hash:asc", "publication.starttime:asc", "title.fi:asc"]

        q = {
            "app_id": self.appid,
            "app_key": self.appkey,
            "offset": offset,
            "limit": limit,
            "order": ",".join(order),
            "type": "program",
            "availability": "ondemand",
        }

        if seasonId is not None:
            q['season'] = seasonId

        url = f"https://{self.areenadomain}/api/programs/v1/episodes/{seriesId}.json" + self._qstr(q)
        resp = self._dl_url(url, cachetime)
        data = resp['data']

        if len(data) == 0:
            raise NotFound(url)

        episodes = []
        for ep in data:
            start = None  # Date and time when episode become available
            end = None  # Date and time when episode becomes unavailable

            for p in ep['publicationEvent']:
                if 'yle-areena' in p['service']['id'] and 'yle-areena' in p['publisher'][0]['id']:
                    start = self._get_date(p['startTime'])
                    end = self._get_date(p['endTime'])
                    break

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
            seasons.append(Season(season['id'], season['seasonNumber'], self._get_title(season['title'])))

        return seasons

    def getProgramById(self, id: str) -> dict:
        cachetime = datetime.timedelta(hours=4)

        q = {
            "app_id": self.appid,
            "app_key": self.appkey,
        }

        url = f"https://{self.apidomain}/v1/programs/items/{id}.json" + self._qstr(q)

        resp = self._dl_url(url, cachetime)
        data = resp['data']
        print()
