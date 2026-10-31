"""Console colours, usable before the config is loaded (the banner prints first)."""
import os
import sys

NEON = [(255, 43, 214), (214, 59, 255), (155, 92, 255), (106, 125, 255), (63, 160, 255), (34, 211, 238), (34, 245, 200)]


def use_color():
    """TRAKTARR_COLOR=1 forces colour (docker logs isn't a terminal), 0 turns it off; otherwise only on a terminal."""
    setting = os.environ.get('TRAKTARR_COLOR', '').lower()
    if setting in ('1', 'true', 'yes', 'always'):
        return True
    if setting in ('0', 'false', 'no', 'never'):
        return False
    return sys.stdout.isatty()


def rgb(r, g, b, bold=False):
    return '\x1b[%s38;2;%d;%d;%dm' % ('1;' if bold else '', r, g, b)
