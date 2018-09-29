# XBN Timestamp Project
![Project
overview](https://git.xbn.fm/s0ph0s/show-scripts/raw/master/overview-diagram.png)


## About this repository

[XBN](https://xbn.fm) wants to put chapter markers in their podcasts, and there
isn't any good software infrastructure yet to support that. This is the second
part of the two-part system that generates various metadata to be embedded into
podcast files or released alongside the podcast file. This repository is also
the working directory where most of the reference/development files can be
found.


## What you'll find here:

* **PostShow.py** - Audacity Marker Converter on the graph, generate CUE, LRC
  and simple timestamp files from an Audacity marker file
* **PostShowV2.py** - new and improved version of PostShow developed by
  [s0ph0s](https://github.com/s0ph0s-2). Changelog can be found
  [here](https://github.com/vladasbarisas/XBN/pull/2)
* **Gelo** - Podcast chapter metadata gathering tool
* **mp3-chapter-scripts** - S0ph0s's scripts to embed chapters into MP3s. Use
  `chaptagger4.py` in production
* **auxiliary-scripts** - various scripts that aren't part of the main package
* **MarkerGen** - Script that was used to extract approximate metadata from
  [xananp's](https://twitter.com/xananp) tweets. Kept for posterity reasons
* **old-reference-livescript.js** - script that was previously used in
  production, now superseded by Gelo

## Usage:

**Please refer to Gelo documentation for Gelo-specific usage instructions.**

```
usage: PostShowV2.py [-h] [-c CONFIG] [-m MARKERS] [-p PROFILE] [--no-encode]
                     wav outdir

Convert and tag WAVs and chapter metadata for podcasts.

positional arguments:
  wav                   WAV file to convert/use
  outdir                directory in which to write output files. Will be
                        created if nonexistent.

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        configuration file to use, defaults to $HOME/.config/
                        postshow.ini
  -m MARKERS, --markers MARKERS
                        marker file to convert/use. Only Audacity labels are
                        currently supported
  -p PROFILE, --profile PROFILE
                        the configuration profile on which to base default
                        values
  --no-encode           the MP3 file already exists, don't encode the WAV
                        file.

example: PostShowV2.py -m fnt-200.txt fnt-200.wav output/folder/
```

## I'm only here for the metadata files

Pre-generated metadata files can be found
[here](https://github.com/vladasbarisas/XBN-Metadata).
