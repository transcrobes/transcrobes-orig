# Transcrobes

![](https://gitlab.com/transcrobes/transcrobes/badges/master/pipeline.svg)
![](https://gitlab.com/transcrobes/transcrobes/badges/master/coverage.svg)
![](https://img.shields.io/docker/v/transcrobes/transcrobes)

Transcrobes is the central project for the Transcrobes project (https://transcrob.es) and houses the central API for interacting with the system.

Applications with independent lifecycles (web extensions, media player plugins, the SRS system, etc.) live in other repositories in the project group (also called transcrobes).

As the nexus point for the project, it contains various cross-concern elements and serves to house issues and discussions that don't clearly belong to one of the other sub-projects, in addition to the central API.

Documentation
=============
See https://transcrob.es

Status
======
This is alpha software with some occasional data loss bugs. It works, sorta, if you hold it right. There are not yet any tests and you should not attempt to use this project for anything like "production" until at least tests have been added.

Installation
============
See https://transcrob.es

Configuration
=============
See https://transcrob.es

Development
===========
If you are a (Python) developer learning Chinese, or you really want this to be compatible with learning other languages then your help is needed!

## Provisioned docker dev environment

To start experimenting / working with **transcrobes**, you just need to:

```
docker-compose up
```

to run the entire *dev environment* (visit `localhost:8003`). Here are the **default users**

| username | is_superuser | password   |
| :------- | :----------: | :--------- |
| john     |     true     | 478951236a |
| paul     |     false    | 698753214a |


Most core functionality requires translation and transliteration services. Currently only those provided by Azure's Translator Text API are supported, so you'll need a free key for **Azure cognitive services** [translator](https://docs.microsoft.com/en-gb/azure/cognitive-services/translator/). Microsoft provides a free tier, giving 2M characters worth of translation/transliteration/dictionary lookup services per month free (and definitely underreports, meaning you actually get quite a bit more than 2M), though it does require you to give MS a credit card number. However, rather than charge your credit card if you go over the free limit, it will issue errors, meaning you won't get charged unless you manually go into their portal and change from the free tier to the paid tier.

```t
#.env
TRANSCROBES_BING_SUBSCRIPTION_KEY=some_key
```

### Run tests

* **all tests** `docker exec -e TRANSCROBES_ZH_CORENLP_HOST="localhost:9000" transcrobes_server ./scripts/runtests.sh`
* **unit tests** `docker exec -e TRANSCROBES_ZH_CORENLP_HOST="localhost:9000" transcrobes_server ./scripts/rununittests.sh`

## Running transcrobes in a distinct **venv**

Alternatively, you can also get a working dev env using [poetry](https://python-poetry.org/docs/) (the package manager used in this project). Once set up,

```
poetry install
```

will install packages in a virtual env created somewhere in `$HOME/.cache/pypoetry/virtualenvs/transcrobes-Zf0zUOqi-py3.8`. This set up can be used in conjonction with docker-compose. In this set up,

* **venv**: runs transcrobes accessible at `localhost:8002`
* **docker-compose**: runs everything else


## Developer Certificate of Origin
Please sign all your commits by using `git -s`. In the context of this project this means that you are signing the document available at https://developercertificate.org/. This basically certifies that you have the right to make the contributions you are making, given this project's licence. You retain copyright over all your contributions - this sign-off does NOT give others any special rights over your copyrighted material in addition to the project's licence.

## Contributing
See [the website](https://transcrob.es/page/contribute) for more information. Please also take a look at our [code of conduct](https://transcrob.es/page/code_of_conduct) (or CODE\_OF\_CONDUCT.md in this repo).

## External Open Source code used in/by this repo and licences
###English-to-IPA
The portions dealing with English to IPA (via the CMU Pronouncing dictionary, see `transcrobes/lang/enrichers/en/transliterate/cmu/__init__.py`) are taken from https://github.com/mphilli/English-to-IPA, licenced under the MIT Licence, and are Copyright (c) 2018 Michael Phillips.

### Anki
Anki is included as a git submodule, and is licenced under AGPL v3. See https://github.com/dae/anki for copyright details

### anki-sync-server (@tsudoku remix)
anki-sync-server is included as a git submodule, and is licenced under AGPL v3. See https://github.com/tsudoko/anki-sync-server for copyright details.
