import urwid
import threading
import os
from lcm_mon.core import *
from lcm_mon.network import *
from lcm_mon.util import *

class Row(urwid.Columns):
    def __init__(self, layout, labels, selectable):
        self._widgets = [urwid.Text(label) for label in labels]
        config = [(*s, w) for s, w in zip(layout, self._widgets)]
        urwid.Columns.__init__(self, config)
        self._selectable = selectable

    def keypress(self, size, key):
        return key

    def selectable(self):
        return self._selectable

    def set_labels(self, labels):
        for widget, label in zip(self._widgets, labels):
            if label is not None:
                widget.set_text(label)

class StatusBar(Row):
    def __init__(self):
        self._state = self.default()
        Row.__init__(self, self.layout(), self._get_label(self._state), False)

    def fields(self):
        raise NotImplementedError

    def layout(self):
        raise NotImplementedError

    def default(self):
        raise NotImplementedError

    def state(self):
        return self._state

    def update(self):
        self.set_labels(self._get_label(self._state))

    def set(self, **mapping):
        self._state = mapping
        self.update()

    def reset(self):
        self._state = self.default()
        self.update()

    def _get_label(self, mapping):
        labels = []
        for field in self.fields():
            if field in mapping:
                pretty_print = getattr(self, "print_" + field)
                value = mapping[field]
                labels.append(pretty_print(value))
            else:
                labels.append(None)
        return labels

class CustomListBox(urwid.ListBox):
    def __init__(self, body, callback=id):
        urwid.ListBox.__init__(self, body)
        self._callback = callback
        self._previous_focus = None

    def current_focus(self):
        try:
            focus = self.focus_position - 1
        except IndexError:
            return None
        if focus >= 0:
            return focus

    def on_focus_change(self):
        focus = self.current_focus()
        if not (focus is None or focus == self._previous_focus):
            self._previous_focus = focus
            self._callback(focus)

    def keypress(self, size, key):
        result = urwid.ListBox.keypress(self, size, key)
        self.on_focus_change()
        return result

    def mouse_event(self, size, event, button, col, row, focus):
        result = urwid.ListBox.mouse_event(self, size, event, button, col, row, focus)
        self.on_focus_change()
        return result

class Table(Database):
    def __init__(self, header, layout, callback=id, divided=False, buffered=False):
        self._n = len(header)
        self._layout = layout
        self._walker = urwid.SimpleFocusListWalker([])
        self._table = CustomListBox(self._walker, callback=self._focus_callback)
        Database.__init__(self, header, body=self._walker, buffered=buffered)
        self._callback = callback
        self._divided = divided

    def widget(self):
        return self._table

    def _focus_callback(self, focus):
        self._callback(self[focus])

    def format_header(self, header):
        widget = Row(self._layout, header, False)
        return urwid.Pile([urwid.AttrMap(widget, "item.header")])

    def format_entry(self, entry):
        widget = Row(self._layout, entry[:self._n], True)
        if self._divided:
            widget = urwid.LineBox(widget)
        return urwid.AttrMap(widget, "item.normal", "item.focus")

    def current_focus(self):
        return self._table.current_focus()

class LCMStatusBar(StatusBar):
    def __init__(self):
        self._read_format = u"\u25b2 {} {:.3f}s / {:.3f}s @ {}x"
        self._write_format = u"   \u25bc {} {:.3f} kB"
        self._dumped_format = u"   \u25bc Wrote {} ({:.3f} kB)"
        self._refresh_format = u"   \u27f3 {} Hz"
        self._spinner = Spinner()
        self.spin()
        StatusBar.__init__(self)

    def spin(self):
        self._spin = self._spinner.spin()

    def layout(self):
        return [("weight", 1), ("pack",), ("pack",), ("pack",)]

    def fields(self):
        return ["command", "read", "write", "refresh"]

    def default(self):
        return { "command" : "", "read" : None, "write" : None, "refresh" : 1.5 }

    def reset(self):
        StatusBar.reset(self)

    def print_command(self, command):
        if command is None:
            return ""
        else:
            return command

    def print_read(self, log):
        if log is None:
            return ""
        else:
            if log.is_playing():
                spin = self._spin
            else:
                spin = u"\u00b7"
            position = log.position()
            total = log.length()
            speed = log.get_playback_speed()
            return self._read_format.format(spin, position, total, speed)

    def print_write(self, log):
        if log is None:
            return ""
        elif log.is_open():
            spin = self._spin
            written = log.tell() / 1e3
            return self._write_format.format(spin, written)
        else:
            path = log.path()
            written = log.size() / 1e3
            return self._dumped_format.format(path, written)

    def print_refresh(self, refresh):
        return self._refresh_format.format(refresh)

class ChannelsTable(Table):
    def __init__(self, callback=id):
        self.header = ["== CHANNEL ==", "== HZ =="]
        self.layout = [("weight", 1), (8,)]
        Table.__init__(self, self.header, self.layout,
            callback=callback, divided=False, buffered=True)
        self._hz_format = "{: 7.2f}"

    def format_entry(self, entry):
        pretty_entry = [entry[0], self._hz_format.format(entry[1])]
        return Table.format_entry(self, pretty_entry)

    def find_channel(self, channel):
        return self.search(lambda entry: entry[0] == channel)

    def selected_entry(self):
        focus = self.current_focus()
        if focus is not None:
            return self[focus]

class DataTable(Table):
    def __init__(self, lcm_classes, callback=id):
        self.lcm_classes = lcm_classes
        self.header = ["== VARIABLE ==", "== VALUE =="]
        self.layout = [("weight", 1), ("weight", 1)]
        self.current_channel = None
        self.current_class = None
        self.classes = {}
        Table.__init__(self, self.header, self.layout,
            callback=callback, divided=True, buffered=True)

    def format_entry(self, entry):
        val = entry[1]
        if type(val) == type(()) or type(val) == type([]):
            pretty_val = os.linesep.join(["[%i] %s" % (i, v) for i, v in enumerate(val)])
        else:
            pretty_val = str(val)
        pretty_entry = [entry[0], pretty_val]
        return Table.format_entry(self, pretty_entry)

    def selected_entry(self):
        focus = self.current_focus()
        if focus is not None:
            return self[focus]

    def set(self, channel, data):
        self.lock()
        self.clear()
        for lcm_class in self.lcm_classes:
            try:
                msg = lcm_class.decode(data)
                break
            except ValueError:
                pass
        else:
            self.current_channel = None
            self.current_class = None
            self.unlock()
            return False
        self.extend(unpack_msg(msg))
        self.current_channel = channel
        self.current_class = lcm_class
        self.classes[channel] = lcm_class
        self.unlock()
        return True

    def update(self, data):
        self.lock()
        if self.current_class is None:
            raise ValueError
        try:
            msg = self.current_class.decode(data)
        except ValueError:
            self.unlock()
            raise ValueError
        for i, (variable, value) in enumerate(unpack_msg(msg)):
            self[i] = (variable, value)
        self.unlock()

    def clear(self):
        self.lock()
        Table.clear(self)
        self.current_channel = None
        self.current_class = None
        self.unlock()
