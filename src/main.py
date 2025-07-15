import sys
import subprocess
import time
from typing import Literal
from threading import Timer
from pynput import mouse, keyboard
import ctypes
import os

# Load the dynamic library
lib = ctypes.CDLL(os.path.abspath("libaudioutil.dylib"))

# Set return type of the function
lib.is_audio_playing.restype = ctypes.c_int


def is_system_playing_audio():
    return bool(lib.is_audio_playing())


class InactivityMonitor:
    def __init__(self, timeout, time_format: Literal["Seconds", "Minutes", "Hours"], file_to_open, *args_to_file):
        time_map = {
            "Seconds": 1,
            "Minutes": 60,
            "Hours": 3600
        }
        self.timeout = timeout * time_map[time_format]
        self.file_to_open = file_to_open
        self.timer = None
        self.active = False
        self.rc = None
        self.args = args_to_file
        print(f"[DEBUG] Made InactivityMonitor with timeout: {self.timeout} seconds")
        self.reset_timer()

    def reset_timer(self):
        if self.timer:
            self.timer.cancel()
        self.timer = Timer(self.timeout, self.on_inactivity)
        self.timer.start()

    def on_inactivity(self):
        if is_system_playing_audio():
            print("[DEBUG] System is playing audio. Skipping screensaver.")
            print("[DEBUG] Retrying...")
            self.reset_timer()
            return

        print(f"[DEBUG] No activity for {self.timeout} seconds")
        self.stop_listening()
        result = subprocess.run([sys.executable, self.file_to_open, *self.args])
        self.rc = result.returncode
        self.active = False

    def stop_listening(self):
        self.mouse_listener.stop()
        self.keyboard_listener.stop()

    def on_input(self, *args):
        self.reset_timer()

    def run(self):
        self.active = True
        self.mouse_listener = mouse.Listener(
            on_move=self.on_input,
            on_click=self.on_input,
            on_scroll=self.on_input
        )
        self.keyboard_listener = keyboard.Listener(on_press=self.on_input)

        self.mouse_listener.start()
        self.keyboard_listener.start()

        while self.active:
            time.sleep(0.1)  # avoids high CPU usage
        return self.rc

if __name__ == "__main__":
    print("[DEBUG] Starting monitor")
    INACTIVITY_LIMIT = 3
    if len(sys.argv) > 1:
        if sys.argv[1].isnumeric():
            INACTIVITY_LIMIT = int(sys.argv[1])
    FILE_TO_OPEN = os.path.join(os.path.dirname(sys.argv[0]), 'matrix.py')
    monitor = InactivityMonitor(INACTIVITY_LIMIT, "Minutes", FILE_TO_OPEN)
    rc = monitor.run()
    if rc != 0:
        print(f"[ERROR] matrix.py crashed with error code: {rc}")
    print("[DEBUG] Screen Saver executed")
