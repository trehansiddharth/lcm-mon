import threading

class MonState:
    def __init__(self):
        self.reset()

    def reset(self):
        self._write_log = None
        self._read_log = None
        self._refresh_rate = 1.5
        self._channel = None
        self._class = None
        self._lock = threading.RLock()
        self._current_channel = None
        self._current_class = None

    def lock(self):
        self._lock.acquire()

    def unlock(self):
        self._lock.release()

class Buffer(list):
    def __init__(self, initial=[]):
        list.__init__(self, initial)
        self.flush()

    def __setitem__(self, key, value):
        list.__setitem__(self, key, value)

    def __delitem___(self, key):
        list.__delitem__(self, key)
        self._present[i] = False

    def append(self, value):
        list.append(self, value)

    def extend(self, values):
        list.extend(self, values)

    def clear(self):
        self._present = [False] * len(self)
        list.clear(self)

    def apply(self, other, begin=0, mapper=id):
        i = 0
        j = begin
        while j < len(other):
            if self._present[j - begin]:
                other[j] = mapper(self[i])
                i += 1
                j += 1
            else:
                del other[j]
        other.extend(list(map(mapper, self[i:])))

    def flush(self):
        self._present = [True] * len(self)

class Database:
    def __init__(self, header, body=[], buffered=False):
        if buffered:
            self._entries = Buffer([])
        else:
            self._entries = []
        self._body = body
        self._body.append(self.format_header(header))
        self._begin = len(self._body)
        self._buffered = buffered
        self._lock = threading.RLock()

    def lock(self):
        self._lock.acquire()

    def unlock(self):
        self._lock.release()

    def append(self, entry):
        self._entries.append(entry)
        if not self._buffered:
            self._body.append(self.format_entry(entry))

    def extend(self, entries):
        self._entries.extend(entries)
        if not self._buffered:
            for entry in entries:
                self._body.append(self.format_entry(entry))

    def clear(self):
        self._entries.clear()
        if not self._buffered:
            del self._body[self._begin:]

    def length(self):
        return len(self._entries)

    def __getitem__(self, index):
        return self._entries[index]

    def __setitem__(self, index, entry):
        self._entries[index] = entry
        if not self._buffered:
            self._body[self._begin+index] = self.format_entry(entry)

    def __delitem__(self, index):
        del self._entries[index]
        if not self._buffered:
            del self._body[self._begin+index]

    def search(self, matches):
        try:
            return next(i for i, entry in enumerate(self._entries) if matches(entry))
        except StopIteration:
            return None

    def entries(self):
        return self._entries

    def body(self):
        return self._body

    def flush(self):
        if self._buffered:
            self._entries.apply(self._body, begin=self._begin, mapper=self.format_entry)
            self._entries.flush()

    def format_header(self, header):
        raise NotImplementedError

    def format_entry(self, entry):
        raise NotImplementedError
