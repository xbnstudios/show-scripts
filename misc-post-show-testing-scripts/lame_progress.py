import re
import urwid
import random
import threading
import subprocess


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
            text = block.decode('utf-8')
            groups = self.matcher.findall(text)
            if len(groups) < 1:
                continue
            percent = int(groups[-1])
            self.percent = percent
            if percent == 100 and self.p.poll() is not None:
                break
        self.finished = True
        # while self.p.poll() is None:
        #     try:
        #         (stdout, stderr) = self.p.communicate(timeout=1)
        #         stderr = stderr.decode('utf-8')
        #         groups = self.matcher.findall(stderr)
        #         if len(groups) < 1:
        #             continue
        #         self.observer.notify(int(groups[-1]))
        #     except subprocess.TimeoutExpired:
        #         continue
        #     except ValueError:
        #         continue

    def request_stop(self):
        self.p.terminate()


class TUI:
    PROGRESS_UPDATE_SECONDS = 0.2

    def __init__(self):
        self.progressbar = None
        self.encoder = None
        self.loop = None

    def build(self):
        activities = [
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

        divider = ('pack', urwid.Divider())
        self.progressbar = urwid.ProgressBar('progress_background',
                                             'progress_foreground')
        controls = [
            divider,
            ('pack', urwid.Text("Feel free to {} while LAME does its magic.".format(
                random.choice(activities)
            ))),
            divider,
            ('pack', self.progressbar),
            divider,
        ]

        # list = urwid.Pile(controls)
        list = urwid.Padding(urwid.Pile(controls, focus_item=0), left=4, width=40)
        window = urwid.Padding(
            urwid.Filler(
                urwid.AttrWrap(
                    urwid.LineBox(list, 'Encoding'),
                    'dialog'
                ), height=8),
            width=50,
            align='center',
        )

        footer = urwid.AttrWrap(urwid.Text("<Tab> moves between items; <Space> "
                                           "selects; <Enter> activates buttons;"
                                           " <F8> quits"), 'background')
        return urwid.Frame(urwid.AttrWrap(window, 'background'), footer=footer)

    def start(self):
        frame = self.build()
        palette = self.get_palette()
        self.loop = urwid.MainLoop(frame, palette, urwid.raw_display.Screen(),
                                   unhandled_input=self.exit_program)
        self.encoder = MP3Encoder()
        self.encoder.setup('/Users/s0ph0s/Desktop/beep-test/bte.wav',
                           '/Users/s0ph0s/Desktop/beep-test-2/out.mp3',
                           '64')
        self.loop.set_alarm_in(
            TUI.PROGRESS_UPDATE_SECONDS,
            self.update_progress)
        self.encoder.start()
        self.loop.run()
        self.encoder.join()

    def update_progress(self, loop, user_data):
        if not self.encoder.finished:
            self.loop.set_alarm_in(
                TUI.PROGRESS_UPDATE_SECONDS,
                self.update_progress)
        else:
            # Don't do this in the final version.
            raise urwid.ExitMainLoop()
        self.progressbar.set_completion(self.encoder.percent)

    @staticmethod
    def exit_program(button):
        if button in ('f8',):
            raise urwid.ExitMainLoop()

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


if __name__ == "__main__":
    TUI().start()
