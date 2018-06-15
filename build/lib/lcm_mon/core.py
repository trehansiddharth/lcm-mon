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

class Database:
    def __init__(self, header, body=[]):
        self._entries = []
        self._body = body
        self._body.append(self.format_header(header))
        self._begin = len(self._body)
        self._lock = threading.RLock()

    def lock(self):
        self._lock.acquire()

    def unlock(self):
        self._lock.release()

    def append(self, entry):
        self._entries.append(entry)
        self._body.append(self.format_entry(entry))

    def extend(self, entries):
        self._entries.extend(entries)
        for entry in entries:
            self._body.append(self.format_entry(entry))

    def clear(self):
        self._entries.clear()
        del self._body[self._begin:]

    def length(self):
        return len(self._entries)

    def __getitem__(self, index):
        return self._entries[index]

    def __setitem__(self, index, entry):
        self._entries[index] = entry
        self._body[self._begin+index] = self.format_entry(entry)

    def __delitem__(self, index):
        del self._entries[index]
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

    def format_header(self, header):
        raise NotImplementedError

    def format_entry(self, entry):
        raise NotImplementedError
