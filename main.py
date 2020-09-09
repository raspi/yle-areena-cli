#!/bin/env/python
import argparse
import json
import logging
import os
import sys
from pprint import pprint
from lib import YleAreena, NotFound

__VERSION__ = None
with open("VERSION", "r", encoding="utf8") as f:
    __VERSION__ = "".join(f.readlines()).strip()

__AUTHOR__ = u"Pekka Järvinen"
__YEAR__ = 2020
__DESCRIPTION__ = u"Yle Areena API CLI"
__EPILOG__ = u"%(prog)s v{0} (c) {1} {2}-".format(__VERSION__, __AUTHOR__, __YEAR__)

thisfile = os.path.basename(__file__)

__EXAMPLES__ = [
    '',
    '{} seasons 1-4555656'.format(thisfile),
    '{} episodes 1-4555656'.format(thisfile),
    '{} episodes 1-4555656 --season 1-4553280'.format(thisfile),
    '{} search-series --category 5-136 --ignore 5-258,5-259'.format(thisfile),
    '{} program 1-50534749'.format(thisfile),
    '{} categories'.format(thisfile),
]


class CLI:
    log = None
    printJson = False
    client = None

    def __init__(self, log: logging.Logger):
        self.log = log

        parser = argparse.ArgumentParser(
            description=__DESCRIPTION__,
            epilog=__EPILOG__,
            usage=os.linesep.join(map(lambda x: "  " + x, __EXAMPLES__)),
        )

        # More information

        parser.add_argument('--verbose', '-v', action='count', required=False, default=0, dest='verbose',
                            help="Be verbose. -vvv..v Be more verbose.")

        parser.add_argument('--json', '-J', dest='json', action='store_true', default=False,
                            help="Print JSON")

        parser.add_argument('--config', '-c', default="config.json", dest="config",
                            type=argparse.FileType('r', encoding="utf8"),
                            help="JSON configuration file name containing secrets", required=False)

        subp = parser.add_subparsers(dest='command', required=True, help="Command")

        # Get episodes for series X
        episodes = subp.add_parser("episodes")
        episodes.add_argument("id")
        episodes.add_argument("-s", "--season", required=False, help="Season id (not season number)")

        # Get category IDs
        categories = subp.add_parser("categories")

        # Get season IDs
        seasons = subp.add_parser("seasons")
        seasons.add_argument("id")

        # Search series
        search_series = subp.add_parser("search-series")
        search_series.add_argument("--category", "-c", dest='categories', required=False,
                                   help="Category IDs (See 'categories' command for list")
        search_series.add_argument("--ignore", "-i", dest='ignore', required=False, help="Category IDs to ignore")

        # Program
        program = subp.add_parser("program")
        program.add_argument("id")

        # Parse arguments
        args = parser.parse_args()

        if int(args.verbose) > 0:
            # Verbose
            self.log.setLevel(logging.DEBUG)
            self.log.info("Being verbose")

        config = {}
        with args.config as f:
            config = json.loads(f.read())

        self.client = YleAreena(self.log, config['appid'], config['appkey'])

        if args.json:
            self.printJson = True

        if args.command == 'episodes':
            self.episodes(args.id, args.season)
        elif args.command == 'categories':
            self.categories()
        elif args.command == 'seasons':
            self.seasons(args.id)
        elif args.command == 'search-series':
            cats = []
            ignorecats = []

            if args.categories is not None:
                cats = args.categories.split(",")
            if args.ignore is not None:
                ignorecats = args.ignore.split(",")

            self.search_series(cats, ignorecats)
        elif args.command == 'program':
            self.program(args.id)

    def program(self, id: str):
        """
        Get program info
        :param id:
        :return:
        """

        p = self.client.getProgramById(id)

        if self.printJson:
            print(json.dumps(p.__dict__()))
        else:
            print(p)

    def episodes(self, serid: str, season: int = None):
        """
        List episodes

        :param serid: for example 1-4555656 (Das Boot)
        :param season: 1-N or None for all
        :return:
        """

        for i in self.client.getEpisodesBySeriesId(serid, season):
            if self.printJson:
                print(json.dumps(i.__dict__()))
            else:
                print(i)

    def categories(self):
        """
        List categories
        :return:
        """
        for i in self.client.getCategories():
            if self.printJson:
                print(json.dumps(i.__dict__()))
            else:
                print(i)

    def seasons(self, seriesId: str = None):
        """
        List seasons of certain series
        :param seriesId:
        :return:
        """

        for i in self.client.getSeasonsById(seriesId):
            if self.printJson:
                print(json.dumps(i.__dict__()))
            else:
                print(i)

    def search_series(self, categoryIds: list = [], notCategoryIds: list = []):
        for i in self.client.getSeries(categoryIds, notCategoryIds):
            if self.printJson:
                print(json.dumps(i.__dict__()))
            else:
                print(i)


if __name__ == "__main__":
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt="%H:%M:%S",
    )

    log = logging.getLogger(__name__)

    CLI(log)
