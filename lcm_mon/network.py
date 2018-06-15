import lcm
import threading
import tempfile
import time
import os
import glob
import shutil
import subprocess
import importlib.util
import sys
from lcm_mon.core import *
from lcm_mon.util import *

class ReadLog(lcm.EventLog):
    def __init__(self, path, playback_speed=1.0):
        lcm.EventLog.__init__(self, path, mode="r")
        self._path = path
        self._playback_speed = playback_speed
        self._playing = threading.Event()
        self._playing.set()
        self._first_time = None
        self._time = 0.0
        self._lock = threading.Lock()
        offset = 0
        while True:
            self.seek(self.size() - offset)
            try:
                last_timestamp = lcm.EventLog.next(self).timestamp
                break
            except StopIteration:
                pass
            offset += 1
        self.seek(0)
        first_timestamp = lcm.EventLog.next(self).timestamp
        self.seek(0)
        self._last_time = (last_timestamp - first_timestamp) / 1e6

    def path(self):
        return self._path

    def get_playback_speed(self):
        return self._playback_speed

    def set_playback_speed(self, speed):
        self._playback_speed = speed

    def pause(self):
        self._playing.clear()

    def resume(self):
        self._playing.set()

    def is_playing(self):
        return self._playing.is_set()

    def position(self):
        return self._time

    def length(self):
        return self._last_time

    def seek_to_time(self, t):
        timestamp = int(1e6 * (t + self._first_time))
        self._lock.acquire()
        self.seek_to_timestamp(timestamp)
        self._time = t
        self._delay = None
        self._lock.release()

    def play_next(self):
        self._playing.wait()
        if self.next() is not None:
            time.sleep(self._delay / self._playback_speed)
        return self._event

    def next(self):
        self._lock.acquire()
        try:
            self._event = lcm.EventLog.next(self)
        except StopIteration:
            self._event = None
        if self._event is not None:
            if self._first_time is None:
                self._first_time = self._event.timestamp / 1e6
                self._time = 0.0
                self._delay = 0.0
            else:
                event_time = self._event.timestamp / 1e6 - self._first_time
                self._delay = max(event_time - self._time, 0.0)
                self._time = event_time
        self._lock.release()
        return self._event

class WriteLog(lcm.EventLog):
    def __init__(self, path):
        lcm.EventLog.__init__(self, path, mode="w", overwrite=True)
        self._path = path
        self._open = True
        self._size = None

    def path(self):
        return self._path

    def close(self):
        self._open = False
        self._size = lcm.EventLog.size(self)
        lcm.EventLog.close(self)

    def size(self):
        if self._size is None:
            return lcm.EventLog.size(self)
        else:
            return self._size

    def is_open(self):
        return self._open

def load_lcm_modules(folders):
    lcm_files = []
    for folder in folders:
        lcm_pattern = os.path.join(folder, "**/*.lcm")
        lcm_files.extend(glob.glob(lcm_pattern, recursive=True))
    lcm_dir = tempfile.mkdtemp()
    for lcm_file in lcm_files:
        filename = os.path.basename(lcm_file)
        dest_file = os.path.join(lcm_dir, filename)
        new_lcm_file = shutil.copyfile(lcm_file, dest_file)
        subprocess.call(["lcm-gen", "-p", new_lcm_file,
            "--ppath", lcm_dir,
            "--python-no-init"])
    py_pattern = os.path.join(lcm_dir, "**/*.py")
    py_files = glob.glob(py_pattern, recursive=True)
    lcm_classes = []
    for py_file in py_files:
        module_name = os.path.basename(py_file).split(".")[0]
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        lcm_classes.append(getattr(module, module_name))
    shutil.rmtree(lcm_dir)
    return lcm_classes

def handle_lcm(url=None, channels=".*", callback=id):
    if url is None:
        node = lcm.LCM()
    else:
        node = lcm.LCM(url)
    subscription = node.subscribe(channels, callback)
    def handler(node):
        while True:
            node.handle()
    handler_thread = threading.Thread(target=handler, args=(node,))
    handler_thread.setDaemon(True)
    handler_thread.start()
    return node

def play_log(node, log, callback=id):
    while True:
        event = log.play_next()
        if event is None:
            break
        else:
            node.publish(event.channel, event.data)
    callback()

def decode(data, lcm_class):
    try:
        msg = lcm_class.decode(data)
    except ValueError:
        return None
    return unpack_msg(msg)

def init_node():
    return lcm.LCM()
