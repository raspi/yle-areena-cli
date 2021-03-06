# yle-areena-cli

![GitHub All Releases](https://img.shields.io/github/downloads/raspi/yle-areena-cli/total?style=for-the-badge)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/raspi/yle-areena-cli?style=for-the-badge)
![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/raspi/yle-areena-cli?style=for-the-badge)

[Yle Areena](https://areena.yle.fi/) API CLI. See [developer web site](https://developer.yle.fi/en/index.html).

Cache for API JSON fils is written to `.cache` directory. 

Use for example [yle-dl-docker](https://github.com/taskinen/yle-dl-docker) to download episodes.

## Usage examples

List episodes (1-4555656 = Das Boot):

    % python main.py episodes 1-4555656

List episodes (1-4555656 = Das Boot) for season 1:

    % python main.py episodes 1-4555656 --season 1-4553280

List seasons (1-4555656 = Das Boot):

    % python main.py seasons 1-4555656

List categories (such as comedy, drama, ..):

    % python main.py categories
    
Search for series (comedy, not for children):

    % python main.py search-series --category 5-136 --ignore 5-258,5-259

Show info for program (1-50534749 = Docventures: BLEED OUT):

    % python main.py program 1-50534749

Search series programs (1-4555656 = Das Boot):

    % python main.py search-programs --series 1-4555656

Search for program(s) by name:

    % python main.py search-programs -q docventures

Search for program by id (1-50534749 = Docventures: BLEED OUT):

    % python main.py search-programs --id 1-50534749


## Setup

Get Yle Areena API key from [Yle's site](https://tunnus.yle.fi/#api-avaimet).

    % cp config.json.dist config.json
    % $EDITOR config.json
    % python main.py --help

## Requirements

* [Python](https://www.python.org/) 3.6+

## Development

* https://developer.yle.fi/en/api/index.html
* https://developer.yle.fi/en/tutorials/index.html
* https://developer.yle.fi/tutorial-listing-programs/index.html

Make new release:

    ./mkrel.sh <version>

For example:    

    ./mkrel.sh 1.2.3
