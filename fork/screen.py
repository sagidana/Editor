#!/usr/bin/python3

# VT100 escape codes:
# https://www.csie.ntu.edu.tw/~r92094/c++/VT100.html

from .settings import *
from .log import elog
from .events import *
from .hooks import *

from signal import signal, SIGWINCH

from termios import tcgetattr, tcsetattr, TCSADRAIN
from tty import setraw
import sys
import os


BACKGROUND_TRUE_COLOR = "\x1b[48;2;{}m"
FOREGROUND_TRUE_COLOR = "\x1b[38;2;{}m"
BACKGROUND_256_COLOR = "\x1b[48;5;{}m"
FOREGROUND_256_COLOR = "\x1b[38;5;{}m"

REVERSE = "\x1b[7m"
MOVE = "\x1b[{};{}H"

ECHO = "\x1b[28m"
NO_ECHO = "\x1b[8m"

WRAP = "\x1b[?7h"
NO_WRAP = "\x1b[?7l"

CURSOR_DISABLE = "\x1b[?25l"
CURSOR_ENABLE = "\x1b[?25h"
CURSOR_I_BEAM = "\x1b[6 q"
CURSOR_I_BEAM_BLINK = "\x1b[5 q"
CURSOR_UNDERLINE = "\x1b[4 q"
CURSOR_UNDERLINE_BLINK = "\x1b[3 q"
CURSOR_BLOCK = "\x1b[2 q"
CURSOR_BLOCK_BLINK = "\x1b[1 q"
CURSOR_RESET = "\x1b[0 q"

DIM = "\x1b[2m"
NO_DIM = "\x1b[22m"

SAVE_CURSOR = "\x1b[s"
RESTORE_CURSOR = "\x1b[u"

CLEAR_LINE = "\x1b[2K"
CLEAR = "\x1b[2J"

CTRL_D_KEY = 4
CTRL_F_KEY = 6
CTRL_H_KEY = 8
TAB_KEY = 9
CTRL_I_KEY = 9
CTRL_J_KEY = 10
CTRL_K_KEY = 11
ENTER_KEY = 13
CTRL_L_KEY = 12
CTRL_N_KEY = 14
CTRL_O_KEY = 15
CTRL_P_KEY = 16
CTRL_R_KEY = 18
CTRL_S_KEY = 19
CTRL_T_KEY = 20
CTRL_U_KEY = 21
CTRL_V_KEY = 22
CTRL_W_KEY = 23
CTRL_X_KEY = 24
ESC_KEY = 27
CTRL_BACKSLASH_KEY = 28
CTRL_CLOSE_BRACKET_KEY = 29
BACKSPACE_KEY = 127

PGDN_KEY = 10
PGUP_KEY = 10


from functools import lru_cache
@lru_cache(None)
def convert(a):
    r, g, b = int(a[1:3], 16), int(a[3:5], 16), int(a[5:7], 16)
    return f"{r};{g};{b}"

def get_terminal_size():
    import os
    env = os.environ
    def ioctl_GWINSZ(fd):
        try:
            import fcntl, termios, struct, os
            cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ,
        '1234'))
        except:
            return
        return cr
    cr = ioctl_GWINSZ(sys.stdin.fileno()) or \
         ioctl_GWINSZ(sys.stdout.fileno()) or \
         ioctl_GWINSZ(sys.stderr.fileno())

    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        cr = (env.get('LINES', 25), env.get('COLUMNS', 80))

        ### Use get(key[, default]) instead of a try/catch
        #try:
        #    cr = (env['LINES'], env['COLUMNS'])
        #except:
        #    cr = (25, 80)
    return int(cr[1]), int(cr[0])

class Screen():
    def screen_resize_handler(self, signum, frame):
        size = get_terminal_size()
        self.width, self.height = size
        Hooks.execute(ON_RESIZE, size)

    def __init__(self):
        import os
        if not os.isatty(sys.stdin.fileno()):
            self.stdout = open(os.ctermid(), 'w')
            self.stdin = open(os.ctermid(), 'rb')
            # sys.__stdin__ = self.stdin.fileno()
            # sys.__stdout__ = self.stdout.fileno()
            # sys.__stderr__ = self.stdout.fileno()
            # self.stdin = os.open(os.ctermid(), os.O_RDONLY)
            # self.stdout = os.open(os.ctermid(), os.O_WRONLY)
            # stdin = self.stdin
            # stdout = self.stdout
        else:
            self.stdin = sys.stdin
            self.stdout = sys.stdout

        size = get_terminal_size()
        self.width, self.height = size

        signal(SIGWINCH, self.screen_resize_handler)
        self._disable_wrap()

        self.queue = []

        self.old_stdin_settings = tcgetattr(self.stdin)
        r = setraw(self.stdin.fileno())

    def __del__(self):
        tcsetattr(  self.stdin,
                    TCSADRAIN,
                    self.old_stdin_settings)
        self._enable_wrap()

    def _write_to_stdout(self, to_write, to_flush=True):
        # os.write(self.stdout, to_write.encode())
        self.stdout.write(to_write)
        if to_flush: self.flush()

    def set_keys(self, keys):
        self.queue.extend(reversed(keys))

    def get_key(self):
        try:
            if len(self.queue) > 0:
                k = self.queue.pop()
            else:
                k = ord(self.stdin.read(1))
            # elog(f"key: {k}")
            Hooks.execute(ON_KEY, k)
            return k
        except Exception as e:
            elog(f"get_key: {e}", type="ERROR")
            return None

    def get_height(self):
        return self.height

    def get_width(self):
        return self.width

    def _enable_wrap(self, to_flush=True):
        self._write_to_stdout(WRAP, to_flush)

    def _disable_wrap(self, to_flush=True):
        self._write_to_stdout(NO_WRAP, to_flush)

    def _enable_echo(self, to_flush=True):
        self._write_to_stdout(ECHO, to_flush)

    def _disable_echo(self, to_flush=True):
        self._write_to_stdout(NO_ECHO, to_flush)

    def _save_cursor(self, to_flush=True):
        self._write_to_stdout(SAVE_CURSOR, to_flush)

    def _restore_cursor(self, to_flush=True):
        self._write_to_stdout(RESTORE_CURSOR, to_flush)

    def clear_line(self, y):
        self._save_cursor(to_flush=False)

        self.move_cursor(y, 0, to_flush=False)
        self._write_to_stdout(CLEAR_LINE, to_flush=False)

        self._restore_cursor(to_flush=False)
        self.flush()

    def clear_line_partial(self, y, start_x, end_x):
        empty = " " * (end_x - start_x)
        self.write(y, start_x, empty)

    def clear(self):
        self._write_to_stdout(CLEAR)

    def set_cursor_i_beam(self):
        self._write_to_stdout(CURSOR_I_BEAM)

    def set_cursor_underline(self):
        self._write_to_stdout(CURSOR_UNDERLINE)

    def set_cursor_block_blink(self):
        self._write_to_stdout(CURSOR_BLOCK_BLINK)

    def disable_cursor(self):
        self._write_to_stdout(CURSOR_DISABLE)
    def enable_cursor(self):
        self._write_to_stdout(CURSOR_ENABLE)

    def move_cursor(self, y, x, to_flush=True):
        y += 1; x += 1
        escape = MOVE.format(y, x)
        self._write_to_stdout(escape, to_flush=to_flush)

    def _set_style(self, style, to_flush=True):
        if not style: style = {}
        fg =    style['foreground'] if 'foreground' in style else  \
                get_settings()['theme']['colors']['editor.foreground']
        bg =    style['background'] if 'background' in style else  \
                get_settings()['theme']['colors']['editor.background']

        if fg: self._write_to_stdout(FOREGROUND_TRUE_COLOR.format(convert(fg)), to_flush=False)
        if bg: self._write_to_stdout(BACKGROUND_TRUE_COLOR.format(convert(bg)), to_flush=False)

        if 'reverse' in style:
            self._write_to_stdout(REVERSE, to_flush=False)
        if to_flush: self.flush()

    def flush(self):
        self.stdout.flush()
        # pass

    def write(self, y, x, string, style=None, to_flush=True):
        self._save_cursor(to_flush=False)

        self.move_cursor(y, x, to_flush=False)
        self._set_style(style, to_flush=False)
        self._write_to_stdout(string, to_flush=False)

        self._restore_cursor(to_flush=False)
        if to_flush: self.flush()


if __name__ == '__main__':
    screen = Screen()

    screen.clear()

    screen.write(0,0,
                "Hello World",
                # {"foreground": "#A6E22E"})
                {"foreground": "#F9262E"})

    screen.move_cursor(0,0)
    # screen.set_cursor_block_blink()
    screen.set_cursor_underline()
    # screen.disable_cursor()
    screen.move_cursor(0,1)


    # screen._write_to_stdout("\x1b[5m") # set blink
    # screen._write_to_stdout("\x1b[25m") # set blink
    # screen._write_to_stdout("\x1b[4h") # set insert mod

    # screen._write_to_stdout("\x1b[6 q") # set i-beam
    # screen._write_to_stdout("\x1b[5 q") # set i-beam blnking
    # screen._write_to_stdout("\x1b[4 q") # set underline
    # screen._write_to_stdout("\x1b[3 q") # set underline blinking
    # screen._write_to_stdout("\x1b[2 q") # set block
    # screen._write_to_stdout("\x1b[1 q") # set block blinking
    # screen._write_to_stdout("\x1b[0 q") # reset

    # screen._write_to_stdout("\x1b[?17;14;224c")
    # screen._write_to_stdout("\x1b[?17;14;224c")
    # screen._write_to_stdout("\x1b[?16;1000]")
    # screen._write_to_stdout("\x1b[4h")
    # screen._write_to_stdout("\x1b[?16;20]")

    for i in range(1):
        c = screen.get_key()
        print(f"{c}")
    # screen.enable_cursor()
