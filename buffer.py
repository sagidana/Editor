from log import elog

from events import *
from hooks import *
from idr import *

from treesitter import TreeSitter

from difflib import Differ
import hashlib
import json
import re

class Buffer():
    def on_buffer_change_callback(self, change):
        if self.treesitter and change:
            self.treesitter.edit(change, self.get_file_bytes())

    def raise_event(func):
        def event_wrapper(self):
            # self = args[0]
            func_name = func.__name__
            event = f"on_buffer_{func_name}_before"
            self._raise_event(event, self)
            # if event in self.events:
                # for cb in self.events[event]: cb(self)
            func(self)
            event = f"on_buffer_{func_name}_after"
            self._raise_event(event, self)
            # if event in self.events:
                # for cb in self.events[event]: cb(self)
        return event_wrapper

    def _raise_event(self, event, args):
            if event in self.events:
                for cb in self.events[event]: cb(args)

    def register_events(self, handlers):
        for event in handlers:
            if event not in self.events:
                self.events[event] = []
            self.events[event].append(handlers[event])

    def __init__(self, file_path=None):
        Hooks.execute(ON_BUFFER_CREATE_BEFORE, self)

        # When change is starting, this is where original is saved
        self.id = get_id(BUFFER_ID)
        self.shadow = None
        self.change_start_position = None
        self.undo_stack = []
        self.redo_stack = []

        self.highlights = []

        self.visual_mode = None
        self.visual_start_point = None
        self.visual_current_point = None

        self.events = {}
        self.lines = []
        self.file_path = file_path

        if not file_path: 
            raise Exception('Not implemented!')
            Hooks.execute(ON_BUFFER_CREATE_AFTER, self)
            return
        
        with open(file_path, 'r') as f:
            self.lines = f.readlines()

        self.hash = self._hash_file()
        if not self.hash:
            elog("here2")
            raise Exception('Not implemented!')
            Hooks.execute(ON_BUFFER_CREATE_AFTER, self)
            return

        language = self.detect_language()
        self.treesitter = None
        if language:
            with open(file_path, "rb") as f: file_bytes = f.read()
            self.treesitter = TreeSitter(file_bytes, language)

        handlers = {}
        handlers[ON_BUFFER_CHANGE] = self.on_buffer_change_callback
        self.register_events(handlers)

        Hooks.execute(ON_BUFFER_CREATE_AFTER, self)

    def _hash_file(self):
        try:
            with open(self.file_path, 'rb') as h_file:
                return hashlib.md5(h_file.read()).hexdigest()
        except: return None

    def _match_hash(self):
        try:
            with open(self.file_path, 'rb') as h_file:
                curr_hash = hashlib.md5(h_file.read()).hexdigest()
                return self.hash == curr_hash
        except:
            return False

    def file_changed_on_disk(self):
        return not self._match_hash()

    def detect_language(self):
        if      self.file_path.endswith('.py'):
            return "python"
        elif    self.file_path.endswith('.c') or \
                self.file_path.endswith('.h'):
            return "c"
        elif    self.file_path.endswith('.md'):
            return "markdown"
        elif    self.file_path.endswith('.php'):
            return "php"
        elif    self.file_path.endswith('.go'):
            return "go"
        elif    self.file_path.endswith('.html'):
            return "html"
        elif    self.file_path.endswith('.css'):
            return "css"
        elif    self.file_path.endswith('.java'):
            return "java"
        elif    self.file_path.endswith('.js'):
            return "javascript"
        elif    self.file_path.endswith('.rb'):
            return "ruby"
        elif    self.file_path.endswith('.rs'):
            return "rust"
        elif    self.file_path.endswith('.sh'):
            return "sh"
        elif    self.file_path.endswith('.cpp') or \
                self.file_path.endswith('.hpp'):
            return "cpp"
        elif    self.file_path.endswith('.json'):
            return "json"
        elif    self.file_path.endswith('.xml'):
            # return "xml"  # treesitter not supporting
            return None
        elif    self.file_path.endswith('.vim'):
            # return "vimscript"  # treesitter not supporting
            return None
        else: 
            if len(self.lines) == 0: return None

            first_line = self.lines[0]
            if not first_line.startswith("#!/"): return None

            m = re.match("#!(?P<program>[a-zA-Z0-9/]+)\s*$", first_line)
            if not m: 
                elog("1")
                return None
            program = m.groups('program')[0]
            elog(f"{program}")
            if  program == "/usr/bin/python3" or \
                program == "/usr/bin/python2" or \
                program == "/usr/bin/python":
                return "python"
            return None

    def resync_treesitter(self):
        if self.treesitter:
            self.treesitter.resync(self.get_file_bytes())

    def get_file_bytes(self):
        return ''.join(self.lines).encode()

    def get_file_stream(self):
        return ''.join(self.lines)

    def get_file_pos(self, x, y):
        for line in self.lines[:y]: x += len(line)
        return x

    def get_file_x_y(self, pos):
        curr = 0
        y = 0
        for line in self.lines: 
            if curr <= pos < curr + len(line):
                x = pos - curr
                return (x, y)
            curr += len(line)
            y += 1
        return None

    def destroy(self):
        Hooks.execute(ON_BUFFER_DESTROY_BEFORE, self)
        Hooks.execute(ON_BUFFER_DESTROY_AFTER, self)

    def reload(self):
        with open(self.file_path, 'r') as f:
            self.lines = f.readlines()

        self.hash = self._hash_file()
        if not self.hash:
            raise Exception('Not implemented!')
            Hooks.execute(ON_BUFFER_CREATE_AFTER, self)
            return

        self.resync_treesitter()
        self._raise_event(ON_BUFFER_RELOAD, None)

    def write(self):
        elog("BUFFER: writing to file!")
        if not self.file_path: 
            raise Exception("No file attached to buffer.")

        with open(self.file_path, 'w+') as f:
            f.writelines(self.lines)

        self.hash = self._hash_file()

    def set_highlights(self, highlights):
        self.highlights = highlights

    def clear_highlights(self):
        self.highlights = []

    def add_highlights(self, highlights): pass

    def visual_begin(self, mode, x, y):
        self.visual_mode = mode
        self.visual_start_point = [x, y]
        self.visual_current_point = [x, y]

    def visual_set_scope(self, start_x, start_y, end_x, end_y):
        self.visual_start_point[0] = start_x
        self.visual_start_point[1] = start_y
        self.visual_current_point[0] = end_x
        self.visual_current_point[1] = end_y

    def visual_set_current(self, x, y):
        if not self.visual_mode: return

        self.visual_current_point[0] = x
        self.visual_current_point[1] = y

    def visual_get_scope(self):
        if not self.visual_mode: return None

        if self.visual_start_point[1] < self.visual_current_point[1]:
            return  self.visual_start_point[0],     \
                    self.visual_start_point[1],     \
                    self.visual_current_point[0],   \
                    self.visual_current_point[1]    
        if self.visual_current_point[1] < self.visual_start_point[1]:
            return  self.visual_current_point[0],   \
                    self.visual_current_point[1],   \
                    self.visual_start_point[0],     \
                    self.visual_start_point[1]

        if self.visual_start_point[0] < self.visual_current_point[0]:
            return  self.visual_start_point[0],     \
                    self.visual_start_point[1],     \
                    self.visual_current_point[0],   \
                    self.visual_current_point[1]
        return  self.visual_current_point[0],   \
                self.visual_current_point[1],   \
                self.visual_start_point[0],     \
                self.visual_start_point[1]

    def visual_end(self):
        self.visual_mode = None
        self.visual_start_point = None
        self.visual_current_point = None

    def _insert_char_to_line(self, x, y, char):
        try:
            line = self.lines[y]
            line = line[:x] + char + line[x:]
            self.lines[y] = line
            return True
        except: return False

    def _split_line(self, x, y):
        line = self.lines[y]
        first = line[:x] + '\n'
        second = line[x:]
        self.lines[y] = first
        self.lines.insert(y + 1, second) 

    def _join_line(self, y):
        line = self.lines[y]
        next_line = self.lines.pop(y + 1)
        joined = line[:-1] + next_line
        self.lines[y] = joined

    # CORE: change
    def remove_char(self, x, y):
        start_byte = self.get_file_pos(x, y)
        if x == 0: 
            if y == 0: return 
            new_x = len(self.lines[y - 1]) - 1
            self._join_line(y - 1)
            change = {
                    'start_byte': start_byte,
                    'old_end_byte': start_byte,
                    'new_end_byte': start_byte - 1,
                    'start_point': (y, x),
                    'old_end_point': (y, x),
                    'new_end_point': (y - 1, new_x),
                    }
        else:
            line = self.lines[y]
            line = line[:x-1] + line[x:]
            self.lines[y] = line

            change = {
                    'start_byte': start_byte,
                    'old_end_byte': start_byte,
                    'new_end_byte': start_byte - 1,
                    'start_point': (y, x),
                    'old_end_point': (y, x),
                    'new_end_point': (y, x - 1),
                    }

        self._raise_event(ON_BUFFER_CHANGE, change)

    # CORE: change
    def insert_char(self, x, y, char):
        start_byte = self.get_file_pos(x, y)
        if char == '\n' or char == '\r':
            self._split_line(x, y)
            change = {
                    'start_byte': start_byte,
                    'old_end_byte': start_byte,
                    'new_end_byte': start_byte + 1,
                    'start_point': (y, x),
                    'old_end_point': (y, x),
                    'new_end_point': (y + 1, 0),
                    }
        else:
            self._insert_char_to_line(x, y, char)
            change = {
                    'start_byte': start_byte,
                    'old_end_byte': start_byte,
                    'new_end_byte': start_byte + 1,
                    'start_point': (y, x),
                    'old_end_point': (y, x),
                    'new_end_point': (y, x + 1),
                    }

        self._raise_event(ON_BUFFER_CHANGE, change)

    # CORE: change
    def insert_line(self, y, new_line):
        change = {}
        start_byte = self.get_file_pos(0, y)
        change['start_byte'] = start_byte
        change['old_end_byte'] = start_byte
        change['new_end_byte'] = start_byte + len(new_line) - 1

        change['start_point'] = (y, 0)
        change['old_end_point'] = (y, 0)
        change['new_end_point'] = (y + 1, 0)

        self.lines.insert(y, new_line)

        self._raise_event(ON_BUFFER_CHANGE, change)

    # CORE: change
    def remove_line(self, y):
        if y >= len(self.lines): return y

        change = {}
        # new_x = len(self.lines[y-1]) - 1
        # new_end_byte = self.get_file_pos(new_x, y - 1)

        line = self.lines[y]
        start_byte = self.get_file_pos(0, y)

        change['start_byte'] = start_byte
        change['old_end_byte'] = start_byte + len(line) 
        change['new_end_byte'] = start_byte
        change['start_point'] = (y, 0)
        change['old_end_point'] = (y, len(line))
        change['new_end_point'] = (y, 0)

        self.lines.pop(y)

        self._raise_event(ON_BUFFER_CHANGE, change)
        return y

    def replace_char(self, x, y, char):
        self.remove_char(x+1, y)
        self.insert_char(x, y, char)

    def replace_line(self, y, new_line):
        self.remove_line(y)
        self.insert_line(y, new_line)

    def remove_scope(   self,
                        start_x,
                        start_y,
                        end_x,
                        end_y):
        if start_y > len(self.lines) - 1: return 0, 0
        if end_y > len(self.lines) - 1: return 0, 0

        # switch
        if  (start_y > end_y) or \
            (start_y == end_y and start_x > end_x):
            tmp_y, tmp_x, = start_y, start_x
            start_y, start_x = end_y, end_x
            end_y, end_x = tmp_y, tmp_x

        if start_y == end_y:
            if start_x > end_x: return  0, 0

            line_len = len(self.lines[start_y]) - 1
            line = self.lines[start_y]
            if start_x - end_x < line_len:
                line = line[:start_x] + line[end_x + 1:]
                self.replace_line(start_y, line)
            else:
                self.remove_line(start_y)
        else:
            start_line = self.lines[start_y]
            # adjust start_x
            if start_x >= len(start_line): start_x = len(start_line) - 1

            end_line = self.lines[end_y]
            # adjust end_x
            if end_x + 1 >= len(end_line): end_x = len(end_line) - 2

            start_line = start_line[:start_x]
            end_line = end_line[end_x + 1:]

            # remove lines from top to bottom
            for i in range(end_y - start_y): 
                self.remove_line(end_y - i)

            new_line = start_line + end_line

            if len(new_line) > 1:
                self.replace_line(start_y, new_line)
            else:
                self.remove_line(start_y)

        return start_x, start_y

    def _change(self, change, undo=True):
        lines_for_deletion = []
        lines_for_insertion = {}
        lines_for_replacement = {}

        _from = "new" if undo else "old"
        _to = "old" if undo else "new"

        for line_num in change:
            # new lines needs to be removed
            if  _from in change[line_num] and \
                _to not in change[line_num]:
                lines_for_deletion.append(line_num)
                # self._remove_line(line_num)

            # changed lines needs to be replaced
            elif    _from in change[line_num] and \
                    _to in change[line_num]:
                lines_for_replacement[line_num] = change[line_num][_to]
                # self._replace_line(line_num, change[line_num]['old'])

            # removed lines neeeds to be reinserted
            elif    _to in change[line_num] and \
                    _from not in change[line_num]:
                lines_for_insertion[line_num] = change[line_num][_to]
                # self._insert_line(line_num, change[line_num]['old'])

        # lines removals must be in decreasing order to no mess up with the
        # line numbers
        for line in reversed(sorted(lines_for_deletion)):
            self.remove_line(line)

        # lines insertions must be in increasing order to no mess up with the
        # line numbers
        for line in sorted(lines_for_insertion):
            self.insert_line(line, lines_for_insertion[line])

        # for line replacements order is not important.
        for line in lines_for_replacement:
            self.replace_line(line, lines_for_replacement[line])

    def undo(self): 
        if self.file_changed_on_disk():
            self.reload()
            # if file was changed under us,
            # all our stack are irrelevant as the entire file's content might
            # be compromised
            self.undo_stack = []
            self.redo_stack = []
            return

        if len(self.undo_stack) == 0: return
        change_wrapper = self.undo_stack.pop()
        change = change_wrapper['change']

        self._change(change)
        self.write()

        self.redo_stack.append(change_wrapper)
        return change_wrapper['start_position']

    def redo(self): 
        if self.file_changed_on_disk():
            self.reload()
            # if file was changed under us,
            # all our stack are irrelevant as the entire file's content might
            # be compromised
            self.undo_stack = []
            self.redo_stack = []
            return

        if len(self.redo_stack) == 0: return
        change_wrapper = self.redo_stack.pop()
        change = change_wrapper['change']

        self._change(change, undo=False)
        self.write()

        self.undo_stack.append(change_wrapper)
        return change_wrapper['end_position']

    def change_begin(self, x, y):
        if self.file_changed_on_disk(): 
            elog("BUFFER: change begin: file changed!")
            self.reload()
        if self.shadow: elog("BUFFER: WTF, already in a change?")
        if self.change_start_position: elog("BUFFER: WTF, already in a change?")
        self.shadow = self.lines.copy()
        self.change_start_position = (x, y)
        self.redo_stack = [] # reset the redo stack on new edit.

    def _analyze_change(self):
        """
        The change format is as follows:
        A list of chnages per line:
        [
        <line_nume>, <old_line>, <new_line>
        ...
        <line_nume>, <old_line>, <new_line>
        ]

        In case there are no old/new line (removal/addition) the apropriate
        action is done correspondingly.
        """
        change = {}

        d = Differ()
        old_line_num = 0
        new_line_num = 0
        for line in d.compare(self.shadow, self.lines):
            if not (line.startswith('?') or \
                    line.startswith('-') or \
                    line.startswith('+')): 
                old_line_num += 1
                new_line_num += 1
                continue

            if line.startswith('+'): 
                if new_line_num not in change: change[new_line_num] = {}

                elog(f"BUFFER: {new_line_num}: {line.strip()}")
                change[new_line_num]['new'] = line[2:]

                new_line_num += 1
            elif line.startswith('-'):
                if old_line_num not in change: change[old_line_num] = {}

                elog(f"BUFFER: {old_line_num}: {line.strip()}")
                change[old_line_num]['old'] = line[2:]
                old_line_num += 1

        return change
            
    def change_end(self, x, y):
        if self.file_changed_on_disk(): 
            elog("BUFFER: file_changed_on_disk")
            elog("BUFFER: change end: file changed!")
            self.reload()
            # discard changes if file changed underneath us
            change = None 
            self.shadow = None
            self.change_start_position = None
            return

        change = self._analyze_change()
        change_wrapper = {}
        if change: 
            change_wrapper['change'] = change
            change_wrapper['start_position'] = self.change_start_position
            change_wrapper['end_position'] = (x,y)
            self.undo_stack.append(change_wrapper)

        self.shadow = None
        self.change_start_position = None
        self.write()
    
    # CORE: movement
    def find_next_char_regex(self, x, y, char_regex): pass
    # CORE: movement
    def find_prev_char_regex(self, x, y, char): pass

    # CORE: movement
    def find_next_char(self, x, y, char):
        pos = self.get_file_pos(x, y)
        stream = self.get_file_stream()

        found = pos + 1
        for c in stream[pos + 1:]:
            if c == char: 
                return self.get_file_x_y(found)
            found += 1
        return None

    # CORE: movement
    def find_prev_char(self, x, y, char):
        pos = self.get_file_pos(x, y)
        stream = self.get_file_stream()

        found = pos - 1
        for c in stream[:pos][::-1]:
            if c == char: 
                return self.get_file_x_y(found)
            found -= 1
        return None

    def find_prev_and_next_char(self, x, y, char):
        prev = self.find_prev_char(x, y, char)
        if not prev: return None
        next = self.find_next_char(x, y, char)
        if not next: return None

        return (prev, next)

    # CORE: movement
    def find_next_word(self, x, y, skip_current=True):
        word_regex = '[a-zA-Z0-9_-]'
        single_regex = '[\)\(\}\{\]\[\,\.\/\'\;\:]'

        pos = self.get_file_pos(x, y)
        stream = self.get_file_stream()

        # skip current word
        if skip_current:
            found = pos + 1
            if re.match(single_regex, stream[pos]): pass
            else:
                for c in stream[found:]:
                    if not re.match(word_regex, c):
                        break
                    found += 1
        else: found = pos

        if found >= len(stream) - 1: return None
        for c in stream[found:]:
            if re.match(word_regex, c):
                return self.get_file_x_y(found)
            elif re.match(single_regex, c):
                return self.get_file_x_y(found)

            found += 1
        return None

    # CORE: movement
    def find_prev_word(self, x, y, skip_current=True):
        word_regex = '[a-zA-Z0-9_-]'
        symbols_regex = '[\)\(\}\{\]\[\,\.\/\'\;]'
        pos = self.get_file_pos(x, y)
        stream = self.get_file_stream()

        # skip current word
        found = pos - 1 if skip_current else pos
        for c in stream[:found+1][::-1]:
            if re.match(word_regex, c):
                break
            elif re.match(symbols_regex, c):
                return self.get_file_x_y(found)

            found -= 1
        if found <= 0: return None
        for c in stream[:found][::-1]:
            if not re.match(word_regex, c):
                return self.get_file_x_y(found)
            found -= 1
        return None

    # CORE: movement
    def find_next_WORD(self, x, y, skip_current=True):
        pos = self.get_file_pos(x, y)
        stream = self.get_file_stream()

        # skip current word
        found = pos + 1 if skip_current else pos
        for c in stream[found:]:
            if re.match('\s', c): break
            found += 1

        if found >= len(stream) - 1: return None
        for c in stream[found:]:
            if not re.match('\s', c):
                return self.get_file_x_y(found)
            found += 1
        return None

    # CORE: movement
    def find_prev_WORD(self, x, y, skip_current=True):
        pos = self.get_file_pos(x, y)
        stream = self.get_file_stream()

        # skip current word begin
        found = pos - 1 if skip_current else pos
        for c in stream[:found+1][::-1]:
            if not re.match('\s', c): break
            found -= 1
        if found <= 0: return None
        for c in stream[:found][::-1]:
            if re.match('\s', c):
                return self.get_file_x_y(found)
            found -= 1
        return None

    # CORE: movement
    def find_word_end(self, x, y, skip_current=True): 
        word_regex = '[a-zA-Z0-9_-]'
        pos = self.get_file_pos(x, y)
        stream = self.get_file_stream()

        # skip current end
        found = pos + 1 if skip_current else pos
        for c in stream[found:]:
            if re.match(word_regex, c): break
            found += 1

        if found >= len(stream) - 1: return None
        for c in stream[found:]:
            if not re.match(word_regex, c):
                return self.get_file_x_y(found - 1)
            found += 1
        return None

    # CORE: movement
    def find_WORD_end(self, x, y, skip_current=True): 
        pos = self.get_file_pos(x, y)
        stream = self.get_file_stream()

        # skip current end
        found = pos + 1 if skip_current else pos
        for c in stream[found:]:
            if not re.match('\s', c): break
            found += 1

        if found >= len(stream) - 1: return None
        for c in stream[found:]:
            if re.match('\s', c):
                return self.get_file_x_y(found - 1)
            found += 1
        return None

    def _find_relevant_object(self, pattern, x, y):
        curr_index = len(''.join(self.lines[:y])) + x

        found = None
        for m in pattern.finditer(''.join(self.lines)):
            elog(f"BUFFER: {m}")
            start, end = m.span()
            if start <= curr_index <= end:
                found = m
                break
            elif curr_index < start: break
        if not found: return None
        start, end = found.span()

        start_x = 0
        start_y = 0
        end_x = 0
        end_y = 0

        curr_offset = 0
        curr_y = 0
        for i in range(len(self.lines)):
            if curr_offset <= start <= curr_offset + (len(self.lines[i]) - 1):
                start_y = i
                start_x = start - curr_offset
            if curr_offset <= end <= curr_offset + (len(self.lines[i]) - 1):
                end_y = i
                end_x = end - curr_offset
                break
            curr_offset += len(self.lines[i])
        return start_x, start_y, end_x, end_y

    def arround_parentheses(self, x, y): 
        prev = self.find_prev_char(x, y, '(')
        if not prev: return None
        next = self.find_next_char(x, y, ')')
        if not next: return None
        return prev[0], prev[1], next[0], next[1]

    def arround_quotation(self, x, y): 
        ret = self.find_prev_and_next_char(x, y, '"')
        if not ret: return None
        return ret[0][0], ret[0][1], ret[1][0], ret[1][1]

    def arround_square_brackets(self, x, y): 
        prev = self.find_prev_char(x, y, '[')
        if not prev: return None
        next = self.find_next_char(x, y, ']')
        if not next: return None
        return prev[0], prev[1], next[0], next[1]

    def arround_curly_brackets(self, x, y): 
        prev = self.find_prev_char(x, y, '{')
        if not prev: return None
        next = self.find_next_char(x, y, '}')
        if not next: return None
        return prev[0], prev[1], next[0], next[1]

    def arround_greater_than(self, x, y): 
        prev = self.find_prev_char(x, y, '<')
        if not prev: return None
        next = self.find_next_char(x, y, '>')
        if not next: return None
        return prev[0], prev[1], next[0], next[1]

    def arround_apostrophe(self, x, y): 
        ret = self.find_prev_and_next_char(x, y, '\'')
        if not ret: return None
        return ret[0][0], ret[0][1], ret[1][0], ret[1][1]

    def arround_backtick(self, x, y): 
        ret = self.find_prev_and_next_char(x, y, '`')
        if not ret: return None
        return ret[0][0], ret[0][1], ret[1][0], ret[1][1]

    def arround_word(self, x, y): 
        begin = self.find_prev_word(x, y, skip_current=False)
        if not begin: return None
        end = self.find_word_end(x, y, skip_current=False)
        if not end: return None
        return begin[0]-1, begin[1], end[0]+1, end[1]

    def arround_WORD(self, x, y): 
        begin = self.find_prev_WORD(x, y, skip_current=False)
        if not begin: return None
        end = self.find_WORD_end(x, y, skip_current=False)
        if not end: return None
        return begin[0]-1, begin[1], end[0]+1, end[1]

    def inner_parentheses(self, x, y): 
        ret = self.arround_parentheses(x, y)
        if not ret: return None
        start_x, start_y, end_x, end_y = ret

        start_x += 1
        end_x -= 1

        return start_x, start_y, end_x, end_y

    def inner_quotation(self, x, y): 
        ret = self.arround_quotation(x, y)
        if not ret: return None
        start_x, start_y, end_x, end_y = ret

        start_x += 1
        end_x -= 1

        return start_x, start_y, end_x, end_y

    def inner_square_brackets(self, x, y): 
        ret = self.arround_square_brackets(x, y)
        if not ret: return None
        start_x, start_y, end_x, end_y = ret

        start_x += 1
        end_x -= 1

        return start_x, start_y, end_x, end_y

    def inner_curly_brackets(self, x, y): 
        ret = self.arround_curly_brackets(x, y)
        if not ret: return None
        start_x, start_y, end_x, end_y = ret

        start_x += 1
        end_x -= 1

        return start_x, start_y, end_x, end_y

    def inner_greater_than(self, x, y): 
        ret = self.arround_greater_than(x, y)
        if not ret: return None
        start_x, start_y, end_x, end_y = ret

        start_x += 1
        end_x -= 1

        return start_x, start_y, end_x, end_y

    def inner_apostrophe(self, x, y): 
        ret = self.arround_apostrophe(x, y)
        if not ret: return None
        start_x, start_y, end_x, end_y = ret

        start_x += 1
        end_x -= 1

        return start_x, start_y, end_x, end_y

    def inner_backtick(self, x, y): 
        ret = self.arround_backtick(x, y)
        if not ret: return None
        start_x, start_y, end_x, end_y = ret

        start_x += 1
        end_x -= 1

        return start_x, start_y, end_x, end_y

    def inner_word(self, x, y): 
        ret = self.arround_word(x, y)
        if not ret: return None
        start_x, start_y, end_x, end_y = ret

        start_x += 1
        end_x -= 1

        return start_x, start_y, end_x, end_y

    def inner_WORD(self, x, y): 
        ret = self.arround_WORD(x, y)
        if not ret: return None
        start_x, start_y, end_x, end_y = ret

        start_x += 1
        end_x -= 1

        return start_x, start_y, end_x, end_y

    def search_pattern(self, pattern):
        results = []
        try:
            for y, line in enumerate(self.lines):
                for m in re.finditer(pattern, line):
                    start_x = m.start()
                    end_x = m.end()

                    results.append((start_x, y, end_x, y))
        except: pass
        return results
