# Transcrobes
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

