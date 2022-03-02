"""GUI"""
import tkinter as tk
from tkinter import ttk
import tkinter.simpledialog as tk_dia
import dateutil.parser
from .. import config
from .. import callib
from . import config_gui
from . import display


def apply_styles(widget):
    STYLE_CLASSES = (
        ('default', '.'),
        ('dayOfWeek', 'dayOfWeek.TLabel'),
        ('dateNumber', 'dateNumber.TLabel'),
        ('eventDisplay', 'eventDisplay.TFrame'),
        ('eventDisplay', 'eventDisplay.TLabel'),
    )
    def conf_grey(name):
        opts = {pre + 'ground': style.lookup(name, pre + 'ground') for pre in ('fore', 'back')}
        opts = {k: '#' + ''.join(  # hex -> RGB -> *factor -> hex for fore+back
            format(round(int(v[i:i+2], 16) * config.get('grey_factor')), '0>2x')
            for i in range(1, 7)) for k, v in opts.items()}
        style.configure('grey.' + name, **opts)

    style = ttk.Style(widget)
    for conf_name, style_name in STYLE_CLASSES:
        style.configure(style_name, **config.get('styles', conf_name))
    conf_grey('dateNumber.TLabel')
    conf_grey('dayOfWeek.TLabel')
    conf_grey('dateCell.TFrame')

    for tag, color in config.get('tag_colors').items():
        name = hex(hash(tag)) + '.eventDisplay.'
        assert color.startswith('#') and len(color) == 7
        for suff in ('TFrame', 'TLabel'):
            col_rgb = [int(color[i:i+2], 16) for i in range(1, 7)]
            # formula from https://stackoverflow.com/a/3943023
            lum = col_rgb[0]*0.299 + col_rgb[1]*0.587 + col_rgb[2]*0.114
            fg = '#000000' if lum > config.get('lum_threshold') else '#ffffff'
            opts = {'background': color, 'foreground': fg}
            style.configure(name + suff, **opts)
            conf_grey(name + suff)

    for style_name, options in config.get('direct_styles').items():
        style.configure(style_name, **options)


def create_menu(root, dis):
    main_menu = tk.Menu(root, relief='sunken')
    nav_menu = tk.Menu(main_menu, tearoff=0)

    def jump_handler():
        target = tk_dia.askstring('Jump to date', 'Date to jump to')
        try:
            day = dateutil.parser.parse(target, dayfirst=True)
        except (TypeError, dateutil.parser.ParserError):
            return
        dis.display(day.date())

    nav_menu.add_command(label='Jump to', underline=0, command=jump_handler)
    nav_menu.add_command(
        label='Previous',
        underline=0,
        command=lambda: dis.move(-1),
    )
    nav_menu.add_command(
        label='Next',
        underline=0,
        command=lambda: dis.move(1),
    )
    main_menu.add_cascade(label='Navigation', menu=nav_menu, underline=0)
    main_menu.add_command(
        label='Configuration',
        underline=0,
        command=lambda: config_gui.display_config_popup(root),
    )
    root.config(menu=main_menu)


def run_app(date):
    root = tk.Tk()
    apply_styles(root)
    # TODO: as soon as there are a bit more features,
    # move the calendar to a separate file
    events = []
    for cal in config.get('calendars'):
        try:
            with open(cal) as f:
                data = f.read()
        except OSError:
            continue
        events += callib.get_events(data)
    display_name = config.get('display')
    if display_name.startswith(('v', 'h')):
        vertical = display_name.startswith('v')
        display_name = display_name[1:]
    dis_cls = {
        'month': display.MonthDisplay,
        'timeline': display.TimelineDisplay,
        'week': display.WeekDisplay,
    }[display_name]
    dis = dis_cls(root, events)
    try:
        dis.vertical = vertical
    except NameError:
        pass
    dis.display(date)
    dis.frame.pack(expand=True, fill=tk.BOTH)
    create_menu(root, dis)
    root.mainloop()
