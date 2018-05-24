#!/usr/bin/env python3
"""Run conversion and tagging tasks for XBN shows."""

import os
import csv
import math
# import urwid
import signal
import argparse
import datetime
import tempfile
import threading
import subprocess
import mutagen.id3
import mutagen.mp3
import configparser
import urllib.parse

REQUIRED_TEXT_KEYS = ['slug', 'filename', 'bitrate', 'title', 'album',
                      'artist', 'season', 'language', 'genre']
REQUIRED_BOOL_KEYS = ['write_date', 'write_trackno', 'lyrics_equals_comment']


class Chapter(object):
    """A podcast chapter."""

    def __init__(self, start: int, end: int, url=None, image=None, text=None,
                 indexed=True):
        """Create a new Chapter.

        :param start: The start time of the chapter, in milliseconds.
        :param end: The end time of the chapter, in milliseconds.
        :param url: An optional URL to include in the chapter.
        :param image: An optional path to an image, which will be read and
        embedded in the chapter.
        :param text: An optional string description of the chapter.
        :param indexed: Whether to include this chapter in the Table of
        Contents.
        """
        self.elem_id = None
        self.text = text
        self.start = start
        self.end = end
        self.url = url
        self.image = image
        self.indexed = indexed

    def __repr__(self):
        """Turn this Chapter into a string."""
        return ("Chapter(start={start}, end={end}, url={url}, image={image}, "
                "text={text}, indexed={indexed})").format(
            start=self.start,
            end=self.end,
            url=self.url if self.url is None else '"' + self.url + '"',
            image=self.image,
            text=self.text if self.text is None else '"' + self.text + '"',
            indexed=self.indexed
        )

    def as_chap(self) -> mutagen.id3.CHAP:
        """Convert this object into a mutagen CHAP object."""
        sub_frames = []
        if self.text is not None:
            sub_frames.append(mutagen.id3.TIT2(text=self.text))
        if self.url is not None:
            sub_frames.append(mutagen.id3.WXXX(
                desc='chapter url',
                url=self.url))
        if self.image is not None:
            raise NotImplementedError("I haven't done this bit yet.")
        return mutagen.id3.CHAP(
            element_id=self.elem_id,
            start_time=self.start,
            end_time=self.end,
            sub_frames=sub_frames
        )


class MP3Tagger:
    """Tag an MP3."""

    def __init__(self, path: str):
        """Create a new tagger."""
        self.path = path
        # Create an ID3 tag if none exists
        try:
            self.tag = mutagen.id3.ID3(path)
        except mutagen.MutagenError:
            broken = mutagen.id3.ID3FileType(path)
            broken.add_tags(ID3=mutagen.id3.ID3)
            self.tag = broken.ID3()
        # Determine the length of the MP3 and write it to a TLEN frame
        mp3 = mutagen.mp3.MP3(path)
        length = int(round(mp3.info.length * 1000, 0))
        self.tag.add(mutagen.id3.TLEN(text=str(length)))

    @staticmethod
    def _no_padding(arg):
        return 0

    def save(self):
        """Save the tag."""
        self.tag.save(self.path, v2_version=3, padding=self._no_padding)

    def set_title(self, title: str) -> None:
        """Set the title of the MP3."""
        self.tag.delall('TIT2')
        self.tag.add(mutagen.id3.TIT2(text=title))

    def set_artist(self, artist: str) -> None:
        """Set the artist of the MP3."""
        self.tag.delall('TPE1')
        self.tag.add(mutagen.id3.TPE1(text=artist))

    def set_album(self, album: str) -> None:
        """Set the album of the MP3."""
        self.tag.delall('TALB')
        self.tag.add(mutagen.id3.TALB(text=album))

    def set_season(self, season: str) -> None:
        """Set the season of the MP3."""
        self.tag.delall('TPOS')
        self.tag.add(mutagen.id3.TPOS(text=season))

    def set_genre(self, genre: str) -> None:
        """Set the genre of the MP3."""
        self.tag.delall('TCON')
        self.tag.add(mutagen.id3.TCON(text=genre))

    def set_composer(self, composer: str) -> None:
        """Set the composer of the MP3."""
        self.tag.delall('TCOM')
        self.tag.add(mutagen.id3.TCOM(text=composer))

    def set_accompaniment(self, accompaniment: str) -> None:
        """Set the accompaniment of the MP3."""
        self.tag.delall('TPE2')
        self.tag.add(mutagen.id3.TPE2(text=accompaniment))

    def set_date(self, year: str) -> None:
        """Set the date of recording of the MP3."""
        self.tag.delall('TDRC')
        self.tag.add(mutagen.id3.TDRC(text=year))

    def set_trackno(self, trackno: str) -> None:
        """Set the track number of the MP3."""
        self.tag.delall('TRCK')
        self.tag.add(mutagen.id3.TRCK(text=trackno))

    def set_language(self, language: str) -> None:
        """Set the language of the MP3."""
        self.tag.delall('TLAN')
        self.tag.add(mutagen.id3.TLAN(text=language))

    def add_comment(self, lang: str, desc: str, comment: str) -> None:
        """Add a comment to the MP3."""
        self.tag.add(mutagen.id3.COMM(lang=lang, desc=desc, text=comment))

    def add_lyrics(self, lang: str, desc: str, lyrics: str) -> None:
        """Add lyrics to the MP3."""
        self.tag.add(mutagen.id3.USLT(lang=lang, desc=desc, text=lyrics))

    def add_chapter(self, chapter: Chapter):
        """Add a chapter to the MP3."""
        self.tag.add(chapter.as_chap())

    def add_chapters(self, chapters: list):
        """Add a whole list of chapters to the MP3."""
        for chapter in chapters:
            self.add_chapter(chapter)


class MP3Encoder(threading.Thread):
    """Shell out to LAME to encode the WAV file as an MP3."""

    def setup(self, infile: str, outfile: str, bitrate: str):
        """Configure the input and output files, and the encoder bitrate.

        :param infile: Path to WAV file.
        :param outfile: Path to create MP3 file at.
        :param bitrate: LAME CBR bitrate, in Kbps.
        """
        self.infile = infile
        self.outfile = outfile
        self.bitrate = bitrate
        self.p = None

    def run(self):
        self.p = subprocess.Popen(['lame', '-t', '-b', self.bitrate, '--cbr',
                                   self.infile, self.outfile],
                                  stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
        # Do whatever is necessary to watch progress from lame
        self.p.wait()

    def request_stop(self):
        self.p.terminate()


class EpisodeMetadata(object):
    """Metadata about an episode."""

    def __init__(self, number: str, name: str, comment: str):
        self.number = number
        self.name = name
        self.comment = comment
        self.title = None
        self.album = None
        self.artist = None
        self.season = None
        self.genre = None
        self.language = None
        self.composer = None
        self.accompaniment = None
        self.date = None
        self.lyrics = None
        self.chapters = []
        self.toc = []


class MCS:
    """Marker Conversion Space

    Load markers from a file into an internal representation, which can then
    be output as other formats. Filetype detection for input files is done
    based on the extension. If the extension is wrong, it may cause issues.

    Supported input formats:
    * Audacity labels

    Supported output formats:
    * CUE file
    * LRC file
    * Internal representation (for use in other parts of the program)

    Create a new instance and call ``load('path/to/file.ext')`` on it to load
    the markers, then ``save('path/to/file.ext', TYPE)``, where ``TYPE`` is
    one of the constants on this class:
    * LRC
    * CUE
    """

    AUDACITY = 0
    LRC = 10
    CUE = 11
    UMR = 12
    SIMPLE = 13

    def __init__(self, metadata=None, media_filename=None):
        self.load_path = None
        self.metadata = metadata
        self.media_filename = media_filename if media_filename is None else \
            os.path.basename(media_filename)
        self.chapters = []

    def _canonicalize(self) -> None:
        """Set the element ID for each chapter."""
        for i in range(0, len(self.chapters)):
            self.chapters[i].elem_id = 'chp{}'.format(i)

    @staticmethod
    def _get_time(seconds: float):
        """Convert a number of seconds into the matching datetime.datetime.

        This code accepts a count of seconds from the start of the show and
        adds that time difference to midnight of the current day, returning a
        datetime that can be printed as necessary.

        :param seconds: The number of seconds to create a delta for.
        :param metadata: The metadata to use in the conversion.  If provided, it
        will cause the output plugins to write relevant metadata to the head
        of the file.
        """
        return datetime.datetime.combine(
            datetime.datetime.today().date(),
            datetime.time(hour=0)
        ) + datetime.timedelta(seconds=seconds)

    def load(self, path: str):
        """Load a file.

        If the markers in the file are not already in chronological order,
        this class will misbehave.

        :param path: The name of the file to load.
        """
        type = path.split('.')[-1:][0]
        if type == "txt":
            # Decoding Audacity labels
            self._load_audacity(path)
        else:
            raise PostShowError("Unsupported marker file: {}".format(type))
        self._canonicalize()

    def _load_audacity(self, path: str):
        """Load an Audacity labels file.

        This plugin also supports URLs, if they are appended to the end of
        the marker with a pipe character:
            Some Marker Name|https://example.com
        """
        with open(path, 'r', encoding='utf-8') as fp:
            reader = csv.reader(fp, delimiter='\t', quoting=csv.QUOTE_NONE)
            for row in reader:
                if not row:
                    break
                try:
                    start = float(row[0]) * 1000
                    end = float(row[1]) * 1000
                except ValueError:
                    continue
                # Round start and end times to integer milliseconds.
                start = int(round(start, 0))
                end = int(round(end, 0))
                mark = row[2]
                text = row[2]
                url = None
                # Identify URLs
                url_parsed = None
                if '|' in mark:
                    url = mark[mark.rindex('|') + 1:]
                    text = mark[:mark.rindex('|')]
                    url_parsed = urllib.parse.urlparse(url)
                if url_parsed is not None and url_parsed.scheme != '' and \
                        url_parsed.netloc != '':
                    chap = Chapter(start, end, url=url, text=text)
                else:
                    chap = Chapter(start, end, text=text)
                self.chapters.append(chap)

    def save(self, path: str, type: int):
        if type == self.LRC:
            self._save_lrc(path)
        elif type == self.CUE:
            self._save_cue(path)
        elif type == self.SIMPLE:
            self._save_simple(path)

    def _save_lrc(self, path: str):
        with open(path, 'w') as fp:
            if self.metadata is not None:
                fp.write('[ti:{}]\n'.format(self.metadata.title))
                fp.write('[ar:{}]\n'.format(self.metadata.artist))
                fp.write('[al:{}]\n'.format(self.metadata.album))
            for chapter in self.chapters:
                minutes = chapter.start // (60*1000)
                seconds = (chapter.start % (60*1000)) // 1000
                fraction = (chapter.start % 1000) // 10
                fp.write('[{:02d}:{:02d}.{:02d}]{}\n'.format(
                    minutes,
                    seconds,
                    fraction,
                    chapter.text
                ))

    def _save_cue(self, path: str):
        if self.media_filename is None:
            raise PostShowError("Writing CUE files is not possible without "
                                "the associated media file name. Pass "
                                "media_filename='path' when creating the MCS.")
        with open(path, 'w') as fp:
            fp.write('\ufeff')  # UTF-8 BOM for foobar2000
            fp.write("REM COMMENT \"Generated by PostShow v2: "
                     "https://github.com/vladasbarisas/XBN\"\n")
            fp.write('FILE "{}" MP3\n'.format(self.media_filename))
            if self.metadata is not None:
                fp.write("REM GENRE {}\n".format(self.metadata.genre))
                fp.write('TITLE "{}"\n'.format(self.metadata.title))
                fp.write('PERFORMER "{}"\n'.format(self.metadata.artist))
            for i in range(0, len(self.chapters)):
                chapter = self.chapters[i]
                minutes = chapter.start // (60*1000)
                seconds = (chapter.start % (60*1000)) // 1000
                # Magic constant is 75/1000, or the number of CUE "frames" per
                # millisecond:
                # https://en.wikipedia.org/wiki/Cue_sheet_(computing)#Essential_commands
                fraction = int(math.floor((chapter.start % 1000) * 0.075))
                fp.write('  TRACK {0} AUDIO\n'
                         '    TITLE "{1}"\n'
                         '    INDEX 01 {2:02d}:{3:02d}:{4:02d}\n'.format(
                             i,
                             chapter.text.replace('"', '_'),
                             minutes,
                             seconds,
                             fraction)
                         )

    def _save_simple(self, path: str):
        with open(path, 'w') as fp:
            for chapter in self.chapters:
                start = self._get_time(chapter.start / 1000)\
                    .strftime("%H:%M:%S")
                fp.write('{0} - {1}\n'.format(start, chapter.text))

    def get(self):
        return self.chapters


class PostShowError(Exception):
    """Something went wrong, use this to explain."""


class Main:
    """Main object."""

    def __init__(self):
        """Setup tasks."""
        self.encoder = MP3Encoder()

        def exit_handler(sig, frame):
            m.request_stop()

        signal.signal(signal.SIGINT, exit_handler)
        self.args = self.parse_args()
        self.config = self.check_config(self.args.config)
        self.metadata = None
        self.mp3_path = None
        self.chapters = None

    def ask_metadata(self) -> EpisodeMetadata:
        """Ask the user for metadata about the episode."""
        ep_num = None
        ep_name = None
        ep_comment = ""
        while ep_num is None:
            i = input("Episode number: ")
            if i != "":
                ep_num = i
        while ep_name is None:
            i = input("Episode name: ")
            if i != "":
                ep_name = i
        print("Episode comment (multiple lines OK, enter empty line to "
              "finish):")
        while True:
            i = input("> ")
            if i == "":
                break
            if ep_comment != "":
                ep_comment += "\r\n"
            ep_comment += i

        self.metadata = EpisodeMetadata(ep_num, ep_name, ep_comment)
        self.metadata.title = self.config.get(self.args.profile,
                                              'title').format(
            slug=self.config.get(self.args.profile, 'slug'),
            epnum=self.metadata.number,
            name=self.metadata.name
        )
        self.metadata.album = self.config.get(self.args.profile, 'album')
        self.metadata.artist = self.config.get(self.args.profile, 'artist')
        self.metadata.season = self.config.get(self.args.profile, 'season')
        self.metadata.genre = self.config.get(self.args.profile, 'genre')
        self.metadata.language = self.config.get(self.args.profile, 'language')
        self.metadata.composer = self.config.get(self.args.profile, 'composer',
                                                 fallback=None)
        self.metadata.accompaniment = self.config.get(self.args.profile,
                                                      'accompaniment',
                                                      fallback=None)
        if self.config.getboolean(self.args.profile, 'write_date'):
            self.metadata.date = datetime.datetime.now().strftime("%Y")
        if self.config.getboolean(self.args.profile, 'write_trackno'):
            self.metadata.track = self.metadata.number
        if self.config.getboolean(self.args.profile, 'lyrics_equals_comment'):
            self.metadata.lyrics = self.metadata.comment

        self.confirm_data()
        return self.metadata

    @staticmethod
    def parse_args() -> argparse.Namespace:
        """Parse arguments to this program."""
        parser = argparse.ArgumentParser(description="Convert and tag WAVs and"
                                                     " chapter metadata for podcasts.")
        parser.add_argument("wav",
                            help="WAV file to convert/use")
        parser.add_argument("outdir",
                            help="directory in which to write output files. "
                                 "Will be created if nonexistant.")
        parser.add_argument("-c",
                            "--config",
                            help="configuration file to use",
                            default=os.path.expandvars(
                                "$HOME/.config/postshow.ini"))
        parser.add_argument("-m",
                            "--markers",
                            help="marker file to convert/use. Only Audacity "
                                 "labels are currently supported")
        parser.add_argument("-p",
                            "--profile",
                            default="default",
                            help="the configuration profile on which to base"
                                 "default values")
        parser.add_argument("--no-encode",
                            default=False,
                            action='store_true',
                            help="the MP3 file already exists, don't encode "
                                 "the WAV file.")
        args = parser.parse_args()
        errors = []
        if not os.path.exists(args.config):
            errors.append("Configuration file ({}) does not"
                          " exist".format(args.config))
        if not os.path.exists(args.wav):
            errors.append("Source WAV file ({}) does not exist".format(
                args.wav))
        if args.markers is not None and not os.path.exists(args.markers):
            errors.append("Markers file ({}) does not exist".format(
                args.markers))
        try:
            os.mkdir(args.outdir)
        except OSError as e:
            if e.errno != os.errno.EEXIST:
                errors.append(str(e))
        if len(errors) > 0:
            raise PostShowError(';\n'.join(errors))
        return args

    @staticmethod
    def check_config(path: str) -> configparser.ConfigParser:
        """Load the config file and check it for correctness."""
        config = configparser.ConfigParser()
        config.read(path)
        errors = []
        # Check every section of the config file, except for DEFAULT (which we
        # don't care about)
        for section in config:
            if section == "DEFAULT":
                continue
            so = config[section]
            # Just verify that the REQUIRED_TEXT_KEYS from above exist in the
            # file.  If they're just empty strings, that's the user's problem.
            for key in REQUIRED_TEXT_KEYS:
                if key not in so.keys():
                    errors.append('[{section}] is missing the required key'
                                  ' "{key}"'.format(section=section, key=key))
            # Verify that the REQUIRED_BOOK_KEYS from above exist in the file,
            # and are boolean values.
            for key in REQUIRED_BOOL_KEYS:
                if key not in so.keys():
                    errors.append('[{section}] is missing the required key'
                                  ' "{key}"'.format(section=section, key=key))
                else:
                    if so[key] not in ['True', 'False']:
                        errors.append('[{section}] must use Python boolean '
                                      'values ("True" or "False") for the key '
                                      '"{key}"'.format(section=section,
                                                       key=key))
        if len(errors) > 0:
            raise PostShowError(';\n'.join(errors))
        return config

    def confirm_data(self):
        """Check with the user to make sure that the metadata is correct."""
        print("Metadata to be written:")
        print("Title:\t\t{}".format(self.metadata.title))
        print("Album:\t\t{}".format(self.metadata.album))
        print("Artist:\t\t{}".format(self.metadata.artist))
        print("Season:\t\t{}".format(self.metadata.season))
        print("Genre:\t\t{}".format(self.metadata.genre))
        print("Language:\t{}".format(self.metadata.language))
        if self.metadata.composer is not None:
            print("Composer:\t{}".format(self.metadata.composer))
        if self.metadata.accompaniment is not None:
            print("Accompaniment:\t{}".format(self.metadata.accompaniment))
        if self.metadata.date is not None:
            print("Date:\t\t{}".format(self.metadata.date))
        if self.metadata.number is not None:
            print("Number:\t\t{}".format(self.metadata.number))
        if self.metadata.comment != "":
            print("Comment:\n{}".format(self.metadata.comment))
            if self.metadata.lyrics is not None:
                print("Lyrics will be identical to comment.")
        while True:
            i = input("Does this all look OK (y/N)? ")
            i = i.lower()
            if i == 'y':
                return
            elif i == 'n' or i == '':
                print("The program will now terminate. LAME will continue "
                      "encoding in the background. Edit the config file and "
                      "run me again with --no-encode.")
                raise SystemExit(0)
            else:
                print("Please enter 'y' or 'n'.")

    def build_output_file_path(self, ext: str, parent=None):
        """Create the path for an output file with the given extension.

        This requires a bunch of code, which would be better in its own
        function.
        """
        if parent is None:
            return os.path.join(
                self.args.outdir,
                self.config.get(self.args.profile, 'filename').format(
                    slug=self.config.get(self.args.profile, 'slug').lower(),
                    epnum=self.metadata.number,
                    ext=ext
                )
            )
        else:
            return os.path.join(
                parent,
                'encoding.' + ext
            )

    def build_chapters(self):
        """Create a chapter list"""
        mcs = MCS(metadata=self.metadata,
                  media_filename=self.build_output_file_path('mp3'))
        mcs.load(self.args.markers)
        self.chapters = mcs.get()
        mcs.save(self.build_output_file_path('lrc'), MCS.LRC)
        mcs.save(self.build_output_file_path('cue'), MCS.CUE)
        mcs.save(self.build_output_file_path('txt'), MCS.SIMPLE)

    def do_tag(self):
        """Tag the file."""
        t = MP3Tagger(self.mp3_path)
        t.set_title(self.metadata.title)
        t.set_album(self.metadata.album)
        t.set_artist(self.metadata.artist)
        t.set_season(self.metadata.season)
        t.set_genre(self.metadata.genre)
        t.set_language(self.metadata.language)
        if self.metadata.composer is not None:
            t.set_composer(self.metadata.composer)
        if self.metadata.accompaniment is not None:
            t.set_accompaniment(self.metadata.accompaniment)
        if self.metadata.comment != "":
            t.add_comment(self.metadata.language, 'track list',
                          self.metadata.comment)
            if self.metadata.lyrics is not None:
                t.add_lyrics(self.metadata.language, 'track list',
                             self.metadata.lyrics)
        if self.chapters is not None:
            t.add_chapters(self.chapters)
        t.save()

    def main(self):
        """The primary logic of this program."""
        # Encode the mp3 to a temp file first, then move it later
        tmp_path = tempfile.TemporaryDirectory()
        if not self.args.no_encode:
            self.mp3_path = self.build_output_file_path('mp3',
                                                        parent=tmp_path.name)
            self.encoder.setup(
                self.args.wav,
                self.mp3_path,
                self.config.get(self.args.profile, 'bitrate')
            )
            # Start the encoder on its own thread
            self.encoder.start()
        # Metadata conversion
        self.metadata = self.ask_metadata()
        if self.args.markers is not None:
            self.build_chapters()
        # This isn't inside the if so that do_tag doesn't fail
        self.mp3_path = self.build_output_file_path('mp3')
        # Join the encoder thread, since tagging can't occur until it is done
        if not self.args.no_encode:
            print("Waiting for encoder to finish...")
            self.encoder.join()
            os.rename(
                self.build_output_file_path('mp3', parent=tmp_path.name),
                self.mp3_path
            )
            tmp_path.cleanup()
        # Tagging
        self.do_tag()


if __name__ == "__main__":
    m = Main()
    m.main()
