import argparse
import json
import logging
import os
import sys
from pprint import pprint
from argparse import FileType
from lib import YleAreena, NotFound

__VERSION__ = "0.0.1"
__AUTHOR__ = u"Pekka Järvinen"
__YEAR__ = 2020
__DESCRIPTION__ = u"Yle Areena API CLI"
__EPILOG__ = u"%(prog)s v{0} (c) {1} {2}-".format(__VERSION__, __AUTHOR__, __YEAR__)

thisfile = os.path.basename(__file__)

__EXAMPLES__ = [
    '',
    '{} episodes 1-4555656'.format(thisfile),
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

        episodes = subp.add_parser("episodes")
        episodes.add_argument("id")
        episodes.add_argument("-s", "--season", required=False)

        args = parser.parse_args()

        if int(args.verbose) > 0:
            logging.getLogger().setLevel(logging.DEBUG)
            self.log.info("Being verbose")

        config = {}
        with args.config as f:
            config = json.loads(f.read())

        self.client = YleAreena(self.log, config['appid'], config['appkey'])

        if args.json:
            self.printJson = True

        if args.command == 'episodes':
            try:
                args.season = int(args.season)
            except TypeError:
                pass

            self.episodes(args.id, args.season)

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


if __name__ == "__main__":
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt="%H:%M:%S",
    )

    log = logging.getLogger(__name__)

    CLI(log)
