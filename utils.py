from os import path
import re

from log import elog


def is_binary_file(file):
    bytes = open(file, 'rb').read()
    textchars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})
    return bytes.translate(None, textchars)

def extract_destination(string):
    file_path = None
    file_line = None
    file_col = None

    try:
        m = re.match(f'^(?P<file_path>[\w\.\/\-]+)(:(?P<file_line>\d+):(?P<file_col>\d+))?.*$',
                    string)
        if not m: return None, None, None

        file_path = m.group('file_path')
        file_line = m.group('file_line')
        if file_line: file_line = int(file_line) - 1
        file_col = m.group('file_col')
        if file_col: file_col = int(file_col) - 1
        if not path.isfile(file_path): return None, None, None
    except Exception as e: elog(f"Exception: {e}")

    return file_path, file_line, file_col
