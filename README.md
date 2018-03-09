# XBN Timestamp Project
![Project overview](https://github.com/ManualManul/plan.jpg)

## Modules:
* **PostShow.py** - Audacity Marker Converter, generates CUR, LRC, Simple TXT and MP3s with embedded chapters from an Audacity marker file
* **LRC** - Gaia's repo of LyRiCs (syncronized lyrics) files
* **MarkerGen** - Tool to extract approximate metadata from [xananp's](https://twitter.com/xananp) tweets. *Inaccuracy up to 1 minute*, might be okay for older episodes?
* **mp3-chapter-scripts** - S0ph0s's scripts to embed chapters into MP3s. Also possible using ffmpeg, refer to script `MarkerGen/AddChapterMarkers-MP3.sh`

## To-do:
- [x] Convert .lrc to .cue
- [x] One script to generate them all
- [ ] Convert MarkerGen metadata to .lrc/.cue
- [ ] Implement drop-down and clickable timestamps on the website
