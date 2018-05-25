import urwid
import random


def null_handler(arg):
    pass


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

def basic_metadata():
    blank = urwid.Divider()
    controls = [
        urwid.Text("Show Number:"),
        urwid.AttrWrap(urwid.Edit("", ""), 'textbox', 'textbox_focused'),
        blank,
        urwid.Text("Show Title:"),
        urwid.AttrWrap(urwid.Edit("", "", multiline=False),
                       'textbox', 'textbox_focused'),
        blank,
        urwid.Text("Comment:"),
        urwid.AttrWrap(urwid.Edit("", "", multiline=True),
                       'textbox', 'textbox_focused'),
        blank,
        urwid.Padding(urwid.GridFlow(
            [urwid.AttrWrap(urwid.Button(txt, null_handler), 'btn',
                            'btn_focus') for txt in ('OK', 'Cancel')],
            10, 3, 1, 'left'), left=15, right=15, min_width=13, align='center')
    ]

    list = urwid.Padding(urwid.ListBox(urwid.SimpleFocusListWalker(controls)),
                         left=2, width=54)
    window = urwid.Padding(
        urwid.Filler(
            urwid.AttrWrap(
                urwid.LineBox(list, 'Basic Metadata'),
                'dialog'
            ), height=13),
        width=60,
        align='center'
    )
    footer = urwid.AttrWrap(urwid.Text("<Tab> moves between items; <Space> "
                                       "selects; <Enter> activates buttons; "
                                       "<F8> quits"), 'background')
    frame = urwid.Frame(urwid.AttrWrap(window, 'background'), footer=footer)

    palette = get_palette()
    urwid.MainLoop(frame, palette, urwid.raw_display.Screen(),
                   unhandled_input=exit_program).run()


def tabular_pad(label, width, value):
    return (label + ":").ljust(width) + value


def confirm_basics():
    controls = [
        urwid.Divider(),
        urwid.Text("The metadata below will be written to the file."),
        urwid.Divider(),
        urwid.Text(tabular_pad("Title", 15, "FNT-196 Analog Checksum")),
        urwid.Text(tabular_pad("Album", 15, "The Friday Night Tech Podcast")),
        urwid.Text(tabular_pad("Artist", 15, "..::XANA::.. Creations")),
        urwid.Text(tabular_pad("Season", 15, "9")),
        urwid.Text(tabular_pad("Genre", 15, "Podcast")),
        urwid.Text(tabular_pad("Language", 15, "eng")),
        urwid.Text(tabular_pad("Composer", 15, "..::XANA::.. Creations")),
        urwid.Text(tabular_pad("Accompaniment", 15, "..::XANA::.. Creations")),
        urwid.Text(tabular_pad("Date", 15, "2018")),
        urwid.Text(tabular_pad("Number", 15, "196")),
        urwid.Text(tabular_pad("Comment", 15, "This is a lot of text, "
                                              "which will be too wide for the "
                                              "box, and hopefully reveal how "
                                              "it handles long messages.")),
        urwid.Divider(),
        urwid.Padding(urwid.GridFlow(
            [urwid.AttrWrap(urwid.Button(txt, null_handler), 'btn',
                            'btn_focus') for txt in ('OK', 'Cancel')],
            10, 4, 1, 'left'), left=10, right=10, min_width=13, align='center'),
        urwid.Divider(),
    ]

    list = urwid.Padding(urwid.ListBox(urwid.SimpleFocusListWalker(controls)),
                         left=5, width=50)
    window = urwid.Padding(
        urwid.Filler(
            urwid.AttrWrap(
                urwid.LineBox(list, 'Confirm Metadata'),
                'dialog'
            ), height=20),
        width=60,
        align='center'
    )

    footer = urwid.AttrWrap(urwid.Text("<Tab> moves between items; <Space> "
                                       "selects; <Enter> activates buttons; "
                                       "<F8> quits"), 'background')
    frame = urwid.Frame(urwid.AttrWrap(window, 'background'), footer=footer)
    palette = get_palette()
    urwid.MainLoop(frame, palette, urwid.raw_display.Screen(),
                   unhandled_input=exit_program).run()


def encoder_progress():
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
    controls = [
        divider,
        ('pack', urwid.Text("Feel free to {} while LAME does its magic.".format(
            random.choice(activities)
        ))),
        divider,
        ('pack', urwid.ProgressBar('progress_background',
                                   'progress_foreground')),
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
                                       "selects; <Enter> activates buttons; "
                                       "<F8> quits"), 'background')
    frame = urwid.Frame(urwid.AttrWrap(window, 'background'), footer=footer)
    palette = get_palette()
    urwid.MainLoop(frame, palette, urwid.raw_display.Screen(),
                   unhandled_input=exit_program).run()


def confirm_chapters():
    controls = [

    ]
    list = urwid.Padding(urwid.ListBox(urwid.SimpleFocusListWalker(controls)),
                         left=5, width=50)
    window = urwid.Padding(
        urwid.Filler(
            urwid.AttrWrap(
                urwid.LineBox(list, 'Confirm Chapters'),
                'dialog'
            ), height=20),
        width=60,
        align='center'
    )

    footer = urwid.AttrWrap(urwid.Text("<Tab> moves between items; <Space> "
                                       "selects; <Enter> activates buttons; "
                                       "<F8> quits"), 'background')
    frame = urwid.Frame(urwid.AttrWrap(window, 'background'), footer=footer)
    palette = get_palette()
    urwid.MainLoop(frame, palette, urwid.raw_display.Screen(),
                   unhandled_input=exit_program).run()


def exit_program(button):
    if button in ('f8',):
        raise urwid.ExitMainLoop()


if __name__ == "__main__":
    encoder_progress()
