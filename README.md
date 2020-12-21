# Transcrobes

Transcrobes is the central project for the Transcrobes project (https://transcrob.es) and houses the central API for interacting with the system, as well as most of the modules for interacting with the API (movie player, ebook reader, spaced repetition system, web browser extension, etc.)

Documentation
=============
See https://transcrob.es

Status
======
Transcrobes is experimental software, and is not yet fully stable.

Installation
============
See https://transcrob.es

Configuration
=============
See https://transcrob.es

Development
===========
If you are a Python and/or JS/TS developer learning Chinese, or you really want this to be compatible with learning other languages, then your help is needed!

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
Standing on the shoulders of giants, this project relies on a great number of open source projects, either as dependencies or as inspiration (with copy/paste). Dependencies are mentioned in the package config files `pyproject.toml` and `package-lock.json` and other non-project-sourced code is clearly marked in the source code.
