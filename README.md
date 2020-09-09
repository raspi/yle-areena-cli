# yle-areena-cli
Yle Areena API CLI. See [developer web site](https://developer.yle.fi/en/index.html).

Cache for API JSON fils is written to `.cache` directory. 

Use for example [yle-dl-docker](https://github.com/taskinen/yle-dl-docker) to download episodes.

## Usage examples

List episodes (Das Boot):

    % python main.py episodes 1-4555656

## Setup

Get Yle Areena API key from [Yle's site](https://tunnus.yle.fi/#api-avaimet).

    % cp config.json.dist config.json
    % $EDITOR config.json
    % python main.py --help


## Requirements

* [Python](https://www.python.org/) 3.6+
