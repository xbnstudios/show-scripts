import urwid


def null_handler(arg):
    pass


def main():
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

    palette = [
        ('background', urwid.WHITE, urwid.DARK_BLUE),
        ('dialog', urwid.BLACK, urwid.WHITE),
        ('textbox', urwid.LIGHT_GRAY, urwid.DARK_BLUE),
        ('textbox_focused', urwid.WHITE, urwid.DARK_BLUE, 'bold'),
        ('btn', urwid.BLACK, urwid.LIGHT_GRAY),
        ('btn_focus', urwid.WHITE, urwid.DARK_RED, 'bold'),
    ]
    urwid.MainLoop(frame, palette, urwid.raw_display.Screen(),
                   unhandled_input=exit_program).run()


def exit_program(button):
    if button in ('f8',):
        raise urwid.ExitMainLoop()


if __name__ == "__main__":
    main()
