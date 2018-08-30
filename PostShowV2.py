#!/usr/bin/env python3
"""Run conversion and tagging tasks for XBN shows.

Written by s0ph0s. https://github.com/vladasbarisas/XBN"""

import os
import re
import csv
import math
import urwid
import random
import signal
import argparse
import datetime
import tempfile
import mimetypes
import threading
import subprocess
import mutagen.id3
import mutagen.mp3
import configparser
import urllib.parse

# These keys must be in the configuration file, with text values
REQUIRED_TEXT_KEYS = ['slug', 'filename', 'bitrate', 'title', 'album',
                      'artist', 'season', 'language', 'genre']
# These keys must be in the configuration file, with boolean values
REQUIRED_BOOL_KEYS = ['write_date', 'write_trackno', 'lyrics_equals_comment']


#
# MODEL CLASSES
#
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

    def set_cover_art(self, path: str):
        """Set the cover art of the MP3."""
        self.tag.delall('APIC')
        mime, ignored = mimetypes.guess_type(path)
        if mime is None:
            raise PostShowError("Unable to guess MIME type of cover image.")
        data = None
        try:
            with open(path, 'rb') as fp:
                data = fp.read()
        except IOError:
            raise PostShowError("Unable to read cover image file.")
        apic = mutagen.id3.APIC(
            mime=mime,
            type=mutagen.id3.PictureType.COVER_FRONT,
            desc='podcast cover art',
            data=data
        )
        self.tag.add(apic)

    def set_date(self, year: str) -> None:
        """Set the date of recording of the MP3."""
        self.tag.delall('TDRC')
        self.tag.add(mutagen.id3.TDRC(text=[mutagen.id3.ID3TimeStamp(year), ]))

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
        self.tag.add(mutagen.id3.COMM(lang=lang, desc=desc, text=[comment, ]))

    def add_lyrics(self, lang: str, desc: str, lyrics: str) -> None:
        """Add lyrics to the MP3."""
        self.tag.add(mutagen.id3.USLT(lang=lang, desc=desc, text=lyrics))

    def add_chapter(self, chapter: Chapter):
        """Add a chapter to the MP3."""
        self.tag.add(chapter.as_chap())

    def add_chapters(self, chapters: list):
        """Add a whole list of chapters to the MP3."""
        child_element_ids = []
        for chapter in chapters:
            self.add_chapter(chapter)
            if chapter.indexed:
                child_element_ids.append(chapter.elem_id)
        self.tag.add(mutagen.id3.CTOC(
            element_id="toc",
            flags=
            mutagen.id3.CTOCFlags.TOP_LEVEL | mutagen.id3.CTOCFlags.ORDERED,
            child_element_ids=child_element_ids,
            sub_frames=[
                mutagen.id3.TIT2(text="Primary Chapter List"),
            ]
        ))


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
        self.matcher = re.compile(r'\(([0-9]?[0-9 ][0-9])%\)')
        self.p = None
        self.percent = 0
        self.finished = False

    def run(self):
        self.p = subprocess.Popen(['lame', '-t', '-b', self.bitrate, '--cbr',
                                   self.infile, self.outfile],
                                  stdout=subprocess.DEVNULL,
                                  stderr=subprocess.PIPE)
        for block in iter(lambda: self.p.stderr.read(1024), ''):
            # Stop when the process terminates.
            if self.p.poll() is not None:
                break
            text = block.decode('utf-8')
            groups = self.matcher.findall(text)
            if len(groups) < 1:
                continue
            percent = int(groups[-1])
            self.percent = percent
            if percent == 100 and self.p.poll() is not None:
                break
        self.finished = True

    def request_stop(self):
        self.p.terminate()


class EpisodeMetadata(object):
    """Metadata about an episode."""

    def __init__(self, number: str, name: str):
        self.number = number
        self.name = name
        self.lyrics = None
        self.title = None
        self.album = None
        self.artist = None
        self.season = None
        self.genre = None
        self.language = None
        self.composer = None
        self.accompaniment = None
        self.date = None
        self.comment = None
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

    @staticmethod
    def _split_url(text: str):
        """Split text into a label and a URL. Return a (text, url) tuple.

        The URL part of the tuple is None if there isn't a URL in the text.
        """
        url = None
        url_parsed = None
        if '|' in text:
            url = text[text.rindex('|') + 1:]
            text = text[:text.rindex('|')]
            url_parsed = urllib.parse.urlparse(url)
        return text, url

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
        elif type == "lrc":
            # Decoding an LRC file
            self._load_lrc(path)
        else:
            raise PostShowError("Unsupported marker file: {}".format(type))
        self._canonicalize()

    def _load_audacity(self, path: str):
        """Load an Audacity labels file.

        This plugin also supports URLs, if they are appended to the end of
        the marker with a pipe character:
            Some Marker Name|https://example.com
        """
        with open(path, 'r', encoding='utf-8-sig') as fp:
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
                text, url = self._split_url(text)
                chap = Chapter(start, end, text=text, url=url)
                self.chapters.append(chap)

    def _load_lrc(self, path: str):
        """Load an LRC file.

        This plugin also supports URLs, if they are appended to the end of the
        marker with a pipe character:
            Some Marker Name|https://example.com
        """
        with open(path, 'r', encoding='utf-8-sig') as fp:
            previous = None
            for line in fp:
                if re.match(r"^\[(ti|ar|al):(.*)\]$", line) is not None:
                    continue
                result = re.match(r"^\[(\d+):(\d\d\.\d+)\](.*)$", line)
                if result is None:
                    continue
                minutes = int(result.group(1))
                seconds = float(result.group(2))
                label = result.group(3)
                millisec = (minutes * 60 * 1000) + int(round(seconds * 1000))
                if previous is not None:
                    self.chapters.append(
                        Chapter(previous[0], millisec, text=previous[1],
                                url=previous[2])
                    )
                text, url = self._split_url(label)
                previous = (millisec, text, url)
            self.chapters.append(
                Chapter(previous[0], previous[0], text=previous[1],
                        url=previous[2])
            )

    def save(self, path: str, type: int):
        if type == self.LRC:
            self._save_lrc(path)
        elif type == self.CUE:
            self._save_cue(path)
        elif type == self.SIMPLE:
            self._save_simple(path)
        elif type == self.AUDACITY:
            self._save_audacity(path)

    def _save_lrc(self, path: str):
        with open(path, 'w') as fp:
            if self.metadata is not None:
                fp.write('[ti:{}]\n'.format(self.metadata.title))
                fp.write('[ar:{}]\n'.format(self.metadata.artist))
                fp.write('[al:{}]\n'.format(self.metadata.album))
            for chapter in self.chapters:
                minutes = chapter.start // (60 * 1000)
                seconds = (chapter.start % (60 * 1000)) // 1000
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
                minutes = chapter.start // (60 * 1000)
                seconds = (chapter.start % (60 * 1000)) // 1000
                # Magic constant is 75/1000, or the number of CUE "frames" per
                # millisecond:
                # https://en.wikipedia.org/wiki/Cue_sheet_(computing)#Essential_commands
                fraction = int(math.floor((chapter.start % 1000) * 0.075))
                fp.write('  TRACK {0:02d} AUDIO\n'
                         '    TITLE "{1}"\n'
                         '    INDEX 01 {2:02d}:{3:02d}:{4:02d}\n'.format(
                    i + 1,
                    chapter.text.replace('"', '_'),
                    minutes,
                    seconds,
                    fraction)
                )

    def _save_simple(self, path: str):
        with open(path, 'w') as fp:
            for chapter in self.chapters:
                start = self._get_time(chapter.start / 1000) \
                    .strftime("%H:%M:%S")
                fp.write('{0} - {1}\n'.format(start, chapter.text))

    def _save_audacity(self, path: str):
        with open(path, 'w', newline='') as fp:
            writer = csv.writer(fp, delimiter='\t', quoting=csv.QUOTE_NONE)
            last_chap = None
            for chapter in self.chapters:
                text = chapter.text
                if chapter.url is not None:
                    text += "|" + chapter.url
                writer.writerow([
                    chapter.start / 1000,
                    chapter.end / 1000,
                    text
                ])

    def get(self):
        return self.chapters


class PostShowError(Exception):
    """Something went wrong, use this to explain."""


#
# VIEW CLASSES
#
class ViewUtil:
    """Utilities for the view classes."""
    FOOTER_TEXT = "<Up>/<Down> to move between items; <Enter> " \
                  "selects/activates controls; <F8> quits"

    @staticmethod
    def window_wrap(func):
        def f_wrap(*args, **kwargs):
            footer = urwid.AttrWrap(
                urwid.Text(ViewUtil.FOOTER_TEXT),
                'background'
            )
            return urwid.Frame(
                urwid.AttrWrap(
                    func(*args, **kwargs),
                    'background'
                ),
                footer=footer
            )

        return f_wrap


class EncoderProgress:
    """Display a progress bar while the encoder is running."""
    UPDATE_INTERVAL_SECONDS = 0.2
    MSG_TEMPLATE = "Feel free to {} while LAME does its magic."
    ACTIVITIES = [
        "hum the Jeopardy! theme",
        "scroll through Twitter",
        "mindlessly eject and close your CD tray",
        "take a walk",
        "water your desk plants",
        "notice the bulge",
        "do something else",
        "hang a spoon on your nose",
        "play tiddlywinks",
        "start reading a new book",
        "play with the new shiny",
        "hug someone you love",
        "put on your favorite song",
        "go make sure you turned off the oven",
        "explore rotational inertia with your office chair",
        "tune up your bicycle",
        "answer an email",
        "text them back",
    ]

    def __init__(self, controller):
        self.progressbar = None
        self.controller = controller
        self.controller.set_alarm_in(
            EncoderProgress.UPDATE_INTERVAL_SECONDS,
            self.update_progress
        )

    def update_progress(self, loop, user_data):
        if not self.controller.encoder_finished():
            loop.set_alarm_in(
                EncoderProgress.UPDATE_INTERVAL_SECONDS,
                self.update_progress
            )
        else:
            self.controller.progress_view_finished()
        self.progressbar.set_completion(
            self.controller.get_encoder_percent()
        )

    @ViewUtil.window_wrap
    def get_view(self):
        """Get the stuff this view will show on screen."""
        divider = ('pack', urwid.Divider())
        self.progressbar = urwid.ProgressBar('progress_background',
                                             'progress_foreground')
        controls = [
            divider,
            ('pack', urwid.Text(EncoderProgress.MSG_TEMPLATE.format(
                random.choice(EncoderProgress.ACTIVITIES)))),
            divider,
            ('pack', self.progressbar),
            divider,
        ]
        contents = urwid.Padding(
            urwid.Pile(controls, focus_item=0),
            left=4,
            width=40
        )
        return urwid.Padding(
            urwid.Filler(
                urwid.AttrWrap(
                    urwid.LineBox(contents, 'Encoding'),
                    'dialog'
                ),
                height=8,
            ),
            width=50,
            align='center'
        )


class TaggerProgress:
    """Display a message while the tagger saves the file."""
    MESSAGE = "Please wait while the MP3 tagger writes to the file."

    def __init__(self, controller):
        self.controller = controller

    @ViewUtil.window_wrap
    def get_view(self):
        """Get the stuff this view will show on screen."""
        controls = [
            ('pack', urwid.Divider()),
            ('pack', urwid.Text(TaggerProgress.MESSAGE)),
            ('pack', urwid.Divider()),
        ]
        contents = urwid.Padding(
            urwid.Pile(controls, focus_item=0),
            left=4,
            width=40
        )
        return urwid.Padding(
            urwid.Filler(
                urwid.AttrWrap(
                    urwid.LineBox(contents, "Tagging"),
                    'dialog'
                ),
                height=5,
            ),
            width=50,
            align='center'
        )


class EnterBasics:
    """Display a dialog requesting basic episode information."""
    NUMBER_TEXT = "Show Number:"
    TITLE_TEXT = "Show Title:"
    LYRICS_TEXT = "Lyrics:"

    def __init__(self, controller):
        self.controller = controller
        self.number_box = urwid.Edit("", "", multiline=False)
        self.title_box = urwid.Edit("", "", multiline=True)

    @ViewUtil.window_wrap
    def get_view(self) -> urwid.Widget:
        """Get the stuff this view displays on screen."""
        blank = urwid.Divider()
        buttons = [
            urwid.AttrWrap(
                urwid.Button("OK", self.handle_ok),
                'btn', 'btn_focus'
            ),
            urwid.AttrWrap(
                urwid.Button("Cancel", self.handle_cancel),
                'btn', 'btn_focus'
            ),
        ]
        controls = [
            urwid.Text(EnterBasics.NUMBER_TEXT),
            urwid.AttrWrap(self.number_box, 'textbox', 'textbox_focused'),
            blank,
            urwid.Text(EnterBasics.TITLE_TEXT),
            urwid.AttrWrap(self.title_box, 'textbox', 'textbox_focused'),
            blank,
            urwid.Padding(urwid.GridFlow(buttons, 10, 3, 1, 'left'),
                          left=15, right=15, min_width=13, align='center')
        ]

        contents = urwid.Padding(
            TabbableListBox(
                urwid.SimpleFocusListWalker(controls)
            ),
            left=2,
            width=54
        )
        return urwid.Padding(
            urwid.Filler(
                urwid.AttrWrap(
                    urwid.LineBox(contents, 'Basic Metadata'),
                    'dialog'
                ), height=10),
            width=60,
            align='center'
        )

    def handle_ok(self, button):
        """Give the data from this view to the controller."""
        self.controller.set_metadata(EpisodeMetadata(
            self.number_box.edit_text,
            self.title_box.edit_text,
        ))

    def handle_cancel(self, button):
        """Tell the controller to exit the program."""
        self.controller.exit()


class ConfirmMetadata:
    """Check with the user to ensure everything is OK before writing."""

    def __init__(self, controller):
        self.controller = controller
        self.metadata = controller.metadata

    @staticmethod
    def build_row(label: str, width: int, value: str):
        cols = [
            ('fixed', width, urwid.Text(label)),
            ('weight', 1, urwid.AttrWrap(urwid.Edit('', value, multiline=True),
                                         'textbox', 'textbox_focused'))
        ]
        return urwid.Columns(cols, dividechars=1)

    def handle_ok(self, button):
        """Set the metadata in the controller."""
        self.controller.finalize_metadata(self.metadata)

    def handle_cancel(self, button):
        """Tell the controller to exit the program."""
        self.controller.exit()

    @ViewUtil.window_wrap
    def get_view(self):
        buttons = [
            urwid.AttrWrap(
                urwid.Button("OK", self.handle_ok),
                'btn', 'btn_focus'
            ),
            urwid.AttrWrap(
                urwid.Button("Cancel", self.handle_cancel),
                'btn', 'btn_focus'
            ),
        ]
        controls = [
            urwid.Divider(),
            urwid.Text("The metadata below will be written to the file."),
            urwid.Divider(),
            self.build_row("Title:", 14, self.metadata.title),
            self.build_row("Album:", 14, self.metadata.album),
            self.build_row("Artist:", 14, self.metadata.artist),
            self.build_row("Season:", 14, self.metadata.season),
            self.build_row("Genre:", 14, self.metadata.genre),
            self.build_row("Language:", 14, self.metadata.language),
        ]
        if self.metadata.composer is not None:
            controls.append(self.build_row(
                "Composer:", 14, self.metadata.composer))
        if self.metadata.accompaniment is not None:
            controls.append(self.build_row(
                "Accompaniment:", 14, self.metadata.accompaniment))
        if self.metadata.date is not None:
            controls.append(self.build_row("Year:", 14, self.metadata.date))
        if self.metadata.number is not None:
            controls.append(self.build_row("Number:", 14, self.metadata.number))
        if self.metadata.lyrics is not None:
            controls.append(self.build_row(
                "Lyrics:", 14, self.metadata.lyrics))
        if self.metadata.comment is not None:
            controls.append(self.build_row(
                "Comment:", 14, self.metadata.comment))
        controls.extend([
            urwid.Divider(),
            urwid.Padding(urwid.GridFlow(buttons, 10, 4, 1, 'left'),
                          left=10, right=10, min_width=13, align='center'),
            urwid.Divider(),
        ])

        contents = urwid.Padding(
            TabbableListBox(urwid.SimpleFocusListWalker(controls)),
            left=5,
            width=50
        )
        return urwid.Padding(
            urwid.Filler(
                urwid.AttrWrap(
                    urwid.LineBox(contents, 'Confirm Metadata'),
                    'dialog'
                ), height=20),
            width=60,
            align='center'
        )


class TabbableListBox(urwid.ListBox):
    """Wrap urwid's ListBox and let the user tab and shift-tab between widgets.
    """

    def keypress(self, size, key):
        """Move selection through the list elements scrolling when
        necessary. Keystrokes are first passed to widget in focus
        in case that widget can handle them.
        Keystrokes handled by this widget are:
         'up'        up one line (or widget)
         'down'      down one line (or widget)
         'tab'       down one line (or widget)
         'shift tab' up one line (or widget)
         'page up'   move cursor up one listbox length (or widget)
         'page down' move cursor down one listbox length (or widget)
        """
        (maxcol, maxrow) = size

        if self.set_focus_pending or self.set_focus_valign_pending:
            self._set_focus_complete((maxcol, maxrow), focus=True)

        focus_widget, pos = self._body.get_focus()
        if focus_widget is None:  # empty listbox, can't do anything
            return key

        if focus_widget.selectable():
            key = focus_widget.keypress((maxcol,), key)
            if key is None:
                self.make_cursor_visible((maxcol, maxrow))
                return None

        def actual_key(unhandled):
            if unhandled:
                return key

        # pass off the heavy lifting
        if self._command_map[key] == urwid.CURSOR_UP or key == 'shift tab':
            return actual_key(self._keypress_up((maxcol, maxrow)))

        if self._command_map[key] == urwid.CURSOR_DOWN or key == 'tab':
            return actual_key(self._keypress_down((maxcol, maxrow)))

        if self._command_map[key] == urwid.CURSOR_PAGE_UP:
            return actual_key(self._keypress_page_up((maxcol, maxrow)))

        if self._command_map[key] == urwid.CURSOR_PAGE_DOWN:
            return actual_key(self._keypress_page_down((maxcol, maxrow)))

        if self._command_map[key] == urwid.CURSOR_MAX_LEFT:
            return actual_key(self._keypress_max_left())

        if self._command_map[key] == urwid.CURSOR_MAX_RIGHT:
            return actual_key(self._keypress_max_right())

        return key


#
# CONTROLLER CLASSES
#
class Controller:
    """Define the control flow of the application as a whole.

    The path is a little confusing, since urwid's event loop doesn't make
    that part easy:
    1. Start the encoder in a separate thread
    2. Display the ``EnterBasics`` view
    3. Use the data from ``EnterBasics`` to fill out the rest of the metadata
    4. Display the ``ConfirmMetadata`` view
    5. Display the ``EncoderProgress`` view
    6. Display the ``TaggerProgress`` view
    7. Save the tags to the file, which will lock up the UI ( threading :( )
    8. Exit
    """

    def __init__(self, args, config):
        self.loop = urwid.MainLoop(None, palette=self.get_palette(),
                                   screen=urwid.raw_display.Screen(),
                                   unhandled_input=self.unhandled_input)
        self.encoder = MP3Encoder()

        def exit_handler(sig, frame):
            self.encoder.request_stop()

        signal.signal(signal.SIGINT, exit_handler)
        self.args = args
        self.config = config
        self.metadata = None
        self.mp3_path = None
        self.chapters = None
        self.tmp_path = None

    @staticmethod
    def get_palette():
        return [
            ('background', urwid.WHITE, urwid.DARK_BLUE),
            ('dialog', urwid.BLACK, urwid.WHITE),
            ('textbox', urwid.LIGHT_GRAY, urwid.DARK_BLUE),
            ('textbox_focused', urwid.WHITE, urwid.DARK_BLUE, 'bold'),
            ('btn', urwid.BLACK, urwid.LIGHT_GRAY),
            ('btn_focus', urwid.WHITE, urwid.DARK_RED, 'bold'),
            ('progress_background', urwid.BLACK, urwid.LIGHT_GRAY),
            ('progress_foreground', urwid.WHITE, urwid.DARK_RED),
        ]

    def unhandled_input(self, button):
        if button == 'f8':
            self.exit()

    def start(self):
        """Do steps 1 and 2.

        1. Start the encoder in a separate thread
        2. Display the ``EnterBasics`` view
        """
        # Encode the mp3 to a temp file first, then move it later
        self.tmp_path = tempfile.TemporaryDirectory()
        if not self.args.no_encode:
            self.mp3_path = self.build_output_file_path(
                'mp3', parent=self.tmp_path.name)
            self.encoder.setup(
                self.args.wav,
                self.mp3_path,
                self.config.get(self.args.profile, 'bitrate')
            )
            # Start the encoder on its own thread
            self.encoder.start()
        basics_view = EnterBasics(self)
        self.loop.widget = basics_view.get_view()

    def set_metadata(self, metadata: EpisodeMetadata):
        """Do steps 3 and 4.

        3. Use the data from ``EnterBasics`` to fill out the rest of the
           metadata
        4. Display the ``ConfirmMetadata`` view
        """
        self.metadata = metadata
        # Metadata conversion
        self.complete_metadata()
        if self.args.markers is not None:
            self.build_chapters()
        confirm_view = ConfirmMetadata(self)
        self.loop.widget = confirm_view.get_view()

    def finalize_metadata(self, metadata: EpisodeMetadata):
        """Do step 5.

        5. Display the ``EncoderProgress`` view
        """
        self.metadata = metadata
        if not self.args.no_encode:
            progress_view = EncoderProgress(self)
            self.loop.widget = progress_view.get_view()
        else:
            self.progress_view_finished()

    def exit(self):
        print("Waiting for the encoder to stop...")
        self.encoder.request_stop()
        self.encoder.join()
        raise urwid.ExitMainLoop()

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
        self.metadata.lyrics = "\n".join([
            chapter.text for chapter in self.chapters
        ])

    def do_tag(self, loop, user_data):
        """Tag the file, and do step 8.

        8. Exit
        """
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
        if self.metadata.lyrics is not None and self.metadata.lyrics != "":
            t.add_comment(self.metadata.language, 'track list',
                          self.metadata.comment)
            if self.metadata.comment is not None:
                t.add_lyrics(self.metadata.language, 'track list',
                             self.metadata.lyrics)
        if self.config.getboolean(self.args.profile, 'write_date'):
            t.set_date(datetime.datetime.now().strftime('%Y'))
        if self.config.getboolean(self.args.profile, 'write_trackno'):
            t.set_trackno(self.metadata.track)
        if self.chapters is not None:
            t.add_chapters(self.chapters)
        if 'cover_art' in self.config[self.args.profile].keys():
            t.set_cover_art(self.config.get(self.args.profile, 'cover_art'))
        t.save()
        raise urwid.ExitMainLoop()

    def set_alarm_in(self, *args, **kwargs):
        """Pass the call to the event loop."""
        self.loop.set_alarm_in(*args, **kwargs)

    def progress_view_finished(self):
        """Do steps 6 and 7.

        6. Display the ``TaggerProgress`` view
        7. Save the tags to the file, which will lock up the UI ( threading :( )

        This method is supposed to be called by the EncoderProgress view
        after it finishes.
        """
        # This isn't inside the if so that do_tag doesn't fail
        self.mp3_path = self.build_output_file_path('mp3')
        # Join the encoder thread, since tagging can't occur until it is
        # done
        if not self.args.no_encode:
            self.encoder.join()
            os.rename(
                self.build_output_file_path(
                    'mp3', parent=self.tmp_path.name),
                self.mp3_path
            )
            self.tmp_path.cleanup()
        tag_progress_view = TaggerProgress(self)
        self.loop.widget = tag_progress_view.get_view()
        # Do async so that this function returns immediately
        self.loop.set_alarm_in(0.1, self.do_tag)

    def encoder_finished(self) -> bool:
        """Return true if the encoder is finished."""
        return self.encoder.finished

    def get_encoder_percent(self) -> int:
        return self.encoder.percent

    def complete_metadata(self) -> None:
        """Complete the metadata using the config file.

        Take the information from the config file and the information entered by
        the user and combine them into the complete information for this
        episode.
        """
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
        self.metadata.composer = self.config.get(
            self.args.profile, 'composer', fallback=None)
        self.metadata.accompaniment = self.config.get(
            self.args.profile, 'accompaniment', fallback=None)
        if self.config.getboolean(self.args.profile, 'write_date'):
            self.metadata.date = datetime.datetime.now().strftime("%Y")
        if self.config.getboolean(self.args.profile, 'write_trackno'):
            self.metadata.track = self.metadata.number
        if self.config.getboolean(self.args.profile, 'lyrics_equals_comment'):
            self.metadata.comment = self.metadata.lyrics


class Main:
    """Main object."""

    def __init__(self):
        """Setup tasks."""
        self.args = self.parse_args()
        self.config = self.check_config(self.args.config)

    @staticmethod
    def parse_args() -> argparse.Namespace:
        """Parse arguments to this program."""
        parser = argparse.ArgumentParser(description="Convert and tag WAVs and"
                                                     " chapter metadata for"
                                                     "podcasts.")
        parser.add_argument("wav",
                            help="WAV file to convert/use")
        parser.add_argument("outdir",
                            help="directory in which to write output files. "
                                 "Will be created if nonexistent.")
        parser.add_argument("-c",
                            "--config",
                            help="configuration file to use, defaults to "
                                 "$HOME/.config/postshow.ini",
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
                                 " default values")
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
            if 'cover_art' in so.keys():
                so['cover_art'] = os.path.expandvars(so['cover_art'])
        if len(errors) > 0:
            raise PostShowError(';\n'.join(errors))
        return config

    def main(self):
        """Kickstart the application."""
        c = Controller(self.args, self.config)
        c.start()
        c.loop.run()


if __name__ == "__main__":
    m = Main()
    m.main()
