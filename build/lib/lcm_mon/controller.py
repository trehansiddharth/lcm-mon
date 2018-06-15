import urwid
import threading
from lcm_mon.core import *
from lcm_mon.network import *
from lcm_mon.util import *

def parse_command(command_string, current_state):
    args = command_string.split()
    if args[0] == ":q" or args[0] == ":quit":
        return "quit", []
    elif args[0] == ":l" or args[0] == ":log":
        if current_state._write_log is None or not current_state._write_log.is_open():
            if len(args) == 1:
                filename = None
            elif len(args) == 2:
                filename = args[1]
            else:
                return None, []
            return "start_write_log", [filename]
        else:
            return "stop_write_log", []
    elif args[0] == ":play" or args[0] == ":p":
        if current_state._read_log is None:
            if len(args) == 2:
                return "start_read_log", [args[1], None]
            elif len(args) == 3 and is_float(args[2]):
                return "start_read_log", [args[1], float(args[2])]
            else:
                return None, []
        elif len(args) == 2 and is_float(args[1]):
            speed = float(args[1])
            return "set_playback_speed", [speed]
        elif len(args) == 1:
            if current_state._read_log.is_playing():
                return "pause_read_log", []
            else:
                return "resume_read_log", []
        else:
            return None, []
    elif args[0] == ":pause":
        if current_state._read_log is not None:
            if current_state._read_log.is_playing():
                return "pause_read_log", []
            else:
                return None, []
        else:
            return None, []
    elif args[0] == ":s" or args[0] == ":seek":
        if current_state._read_log is not None:
            if len(args) == 2 and is_float(args[1]):
                if args[1][0] == "+" or args[1][0] == "-":
                    seek_time = current_state._read_log.position() + float(args[1])
                else:
                    seek_time = float(args[1])
                return "seek_read_log", [seek_time]
            else:
                return None, []
        else:
            return None, []
    elif args[0] == ":r" or args[0] == ":refresh":
        if len(args) == 2 and is_float(args[1]):
            rate = float(args[1])
            return "set_refresh_rate", [rate]
        else:
            return None, []
    elif args[0] == ":v" or args[0] == ":view":
        if len(args) == 2 and args[1] == "-":
            return "stop_visualize", []
        else:
            return "visualize", []
    elif args[0] == ":c" or args[0] == ":clear":
        return "clear", []
    else:
        return None, []

def run_command(command, state, status, node, table, data_table, visualizer):
    action, args = parse_command(command, state)
    if action == "quit":
        raise urwid.ExitMainLoop()
        return True
    elif action == "start_write_log":
        if args[0] is None:
            _, path = tempfile.mkstemp(prefix="lcmlog-", dir=".")
        else:
            path = args[0]
        state.lock()
        state._write_log = WriteLog(path)
        state.unlock()
        status.set(write=state._write_log)
    elif action == "stop_write_log":
        state.lock()
        state._write_log.close()
        status.set(write=state._write_log)
        state.unlock()
    elif action == "start_read_log":
        if args[1] is None:
            state._read_log = ReadLog(args[0])
        else:
            state._read_log = ReadLog(args[0], playback_speed=args[1])
        status.set(read=state._read_log)
        def play_callback():
            state._read_log = None
            status.set(read=None)
        read_log_thread = threading.Thread(target=play_log,
            args=(node, state._read_log, play_callback))
        read_log_thread.setDaemon(True)
        read_log_thread.start()
    elif action == "set_playback_speed":
        state._read_log.set_playback_speed(args[0])
    elif action == "pause_read_log":
        state._read_log.pause()
    elif action == "resume_read_log":
        state._read_log.resume()
    elif action == "seek_read_log":
        state._read_log.seek_to_time(args[0])
    elif action == "set_refresh_rate":
        state._refresh_rate = args[0]
        status.set(refresh=args[0])
    elif action == "visualize":
        table.lock()
        data_table.lock()
        channels_entry = table.selected_entry()
        data_entry = data_table.selected_entry()
        if channels_entry is not None and data_entry is not None:
            channel = channels_entry[0]
            variable = data_entry[0]
            if (channel, variable) in visualizer.tags():
                visualizer.stop()
            else:
                time = channels_entry[2]
                value = data_entry[1]
                visualizer.update((channel, variable), time, value)
        data_table.unlock()
        table.unlock()
    elif action == "stop_visualize":
        visualizer.stop()
    elif action == "clear":
        state.lock()
        table.lock()
        table.clear()
        table.unlock()
        data_table.clear()
        if state._write_log is None or not state._write_log.is_open():
            state._write_log = None
            status.set(write=state._write_log)
        state.unlock()
    else:
        raise ValueError
