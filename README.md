# XBN Timestamp Project
![Project overview](https://github.com/vladasbarisas/XBN/raw/master/overview-diagram.png)

## About this repository
[XBN](https://xbn.fm) wants to put chapter markers in their podcasts, and there
isn't any good software infrastructure yet to support that. This is the second part of the two-part system that generates various metadata to be embedded into podcast files or released alongside the podcast file. This repository is also the working directory where most of the reference/development files can be found.

## What you'll find here:
* **PostShow.py** - Audacity Marker Converter on the graph, generate CUE, LRC and simple timestamp files from an Audacity marker file
* **Gelo** - Podcast chapter metadata gathering tool
* **mp3-chapter-scripts** - S0ph0s's scripts to embed chapters into MP3s. Use `chaptagger4.py` in production.
* **auxiliary-scripts** - various scripts that aren't part of the main package
* **MarkerGen** - Script that was used to extract approximate metadata from [xananp's](https://twitter.com/xananp) tweets. Kept for posterity reasons.
* **old-reference-livescript.js** - script that was previously used in production, now superseded by Gelo

## Usage:
**Please refer to Gelo documentation for Gelo-specific usage instructions.**

```
usage: PostShow.py [-h] input output title filename

positional arguments:
  input       path to audacity file (MyEpisode.txt)
  output      output directory with a leading slash (C:\MyEpisode\)
  title       episode title (001 - My First Podcast)
  filename    episode file name (episode1.mp3)

optional arguments:
  -h, --help  show this help message and exit
```

## I'm only here for the metadata files

Pre-generated metadata files can be found [here](https://github.com/vladasbarisas/XBN-Metadata).