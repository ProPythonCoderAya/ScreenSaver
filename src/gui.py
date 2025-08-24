import os
import sys

from classes import Button, ObjectPool, TextBox, DoubleOut, Alert
expand = os.path.expanduser
os.makedirs(expand("~/.screensaver"), exist_ok=True)
sys.stdout = DoubleOut(expand("~/.screensaver/log.log"))

import json
import subprocess
import threading
import requests
import io
import zipfile
import shutil
from typing import Literal

import pygame
from update import UpdateChecker

def abspath(path):
    if path.startswith("/"):
        return path
    else:
        return os.path.join(os.path.dirname(__file__), path)

# --- Initialization ---
pygame.init()
pygame.mixer.quit()

expand = os.path.expanduser
WIDTH, HEIGHT = 800, 600
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_icon(pygame.image.load("icon.png"))
pygame.display.set_caption("ScreenSaver")

# --- Updation ---
updater = UpdateChecker("ProPythonCoderAya", "ScreenSaver", "update/version.json", "version.json")

def update(version):
    url = f"https://raw.githubusercontent.com/ProPythonCoderAya/ScreenSaver/main/update/versions/{version}/ScreenSaver.zip"
    print(f"Downloading update from {url}")

    try:
        response = requests.get(url)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to get update: {e}")
        return 1

    # Extract ZIP from bytes into update/
    try:
        with zipfile.ZipFile(io.BytesIO(response.content)) as zipf:
            zipf.extractall(abspath("update/"))
        print("Extracted update zip")
    except zipfile.BadZipFile as e:
        print(f"Bad ZIP file: {e}")
        return 1

    # Apply the update safely
    try:
        src_dir = "update"
        dst_dir = os.path.abspath("../")  # This is ../

        for root, dirs, files in os.walk(src_dir):
            for file in files:
                src_path = os.path.join(root, file)
                rel_path = os.path.relpath(src_path, src_dir)  # Relative path from update/
                dst_path = os.path.join(dst_dir, rel_path)  # New path in ../

                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(src_path, dst_path)

        with open("version.json", "w") as f:
            json.dump({"version": version}, f, indent=4)

        shutil.rmtree(src_dir)

        shutil.rmtree(abspath("C/dist/"))

        os.mkdir(abspath("C/dist"))

        os.system(f""" clang -dynamiclib "{abspath("C/src/main.c")}" -framework CoreAudio -o "{abspath("C/dist/libaudioutil.dylib")}" """.strip())
        os.system(f""" cp "{abspath("C/dist/libaudioutil.dylib")}" "{abspath("libaudioutil.dylib")}" """.strip())

        print("Update applied successfully!")
    except Exception as e:
        print(f"Failed to apply update: {e}")
        return 1
    return 0

result = updater.check()
if result == -1:
    update_available, _, version = False, "", "err"
else:
    update_available, _, version = result

# --- Logging ---
def log(text: str, level: Literal[0, 1, 2] = 0):
    level_map = {0: "INFO", 1: "WARN", 2: "DEBUG", 3: "ERROR"}
    print(f"[{level_map[level]}] {text}")

# --- GUI Setup ---
def create_textbox(x, y, default_text):
    return TextBox(
        x=x, y=y, width=60, height=30, max_chars=3,
        start_text=default_text, text_default=default_text,
        color=(220, 220, 220), text_color=(0, 0, 0), start_text_color=(120, 120, 120),
        font="comicsans", font_size=22, fit_to_text=True
    )

def create_button(x, y, text, color, hover_color):
    return Button(
        x=x, y=y, width=120, height=40,
        color=color, hover_color=hover_color, text_color=(0, 0, 0),
        text=text, font_size=22
    )

widget_timeout = create_textbox(200, 29, "3")
widget_save = create_button(100, 545, "Save", (0, 200, 100), (0, 230, 130))
widget_runit = create_button(700, 545, "Run", (200, 100, 0), (230, 130, 0))
widget_stopit = create_button(550, 545, "Stop", (200, 0, 0), (230, 50, 50))
if update_available:
    update_widget = Alert(500, 200, "Update available!", "There is an update available! Do you want to install it?", icon="icon.png", button_names=["No", "Yes"])
else:
    if version == "err":
        update_widget = Alert(500, 200, "Uh oh!", "Do you have internet? I need internet to check for updates.",
                              icon="warning.svg", button_names=["", "Ok"])
    else:
        update_widget = None

# --- Object Pool ---
pool = ObjectPool()
for name, obj in globals().copy().items():
    if name.startswith("widget_"):
        pool.add(obj)
widget_stopit.disable()

# --- Config Load ---
config_path = "config.json"
if os.path.exists(config_path):
    try:
        with open(config_path, "r") as f:
            data = json.load(f)
            widget_timeout.text = str(data.get("timeout", 180) // 60)
    except Exception as e:
        log(f"Failed to load config: {e}", level=1)

# --- Globals ---
font = pygame.font.SysFont("comicsans", 24)
active = True
run = True
process = None
loop_thread = None
clock = pygame.time.Clock()
stop_requested = False
is_running = False

# --- Launch Logic ---
def launch_loop(timeout_val):
    global process, stop_requested, is_running
    is_running = True
    try:
        while not stop_requested:
            log("Launching main.py")
            try:
                process = subprocess.Popen(
                    [sys.executable, "main.py", timeout_val],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, bufsize=1, universal_newlines=True
                )

                while True:
                    if stop_requested:
                        process.terminate()
                        break

                    stdout_line = process.stdout.readline()
                    if stdout_line:
                        print(stdout_line.strip())

                    stderr_line = process.stderr.readline()
                    if stderr_line:
                        print(stderr_line.strip(), file=sys.stderr)

                    if stdout_line == '' and stderr_line == '' and process.poll() is not None:
                        break

                exit_code = process.wait()

                if exit_code != 0:
                    print(process.stderr)
                    print(process.stdout)
                    log("main.py exited with error, stopping loop.", level=3)
                    return 1

                log("main.py completed, restarting.", level=2)

            except Exception as e:
                log(f"Failed to start process: {e}", level=3)
                return 1

    finally:
        process = None
        is_running = False
        widget_runit.enable()
        widget_runit.change_text("Run")
        widget_stopit.disable()
        stop_requested = False

# --- Main Loop ---
while run:
    events = pygame.event.get()
    if update_widget:
        if update_widget.done():
            pool.update(events)
            result = update_widget.result
            update_widget = None
            if result == "Yes":
                update(version)
        else:
            update_widget.update(events)
    else:
        pool.update(events)

    for event in events:
        if event.type == pygame.QUIT:
            if pygame.key.get_mods() & pygame.KMOD_META or not active:
                run = False
            else:
                pygame.display.iconify()

    active = pygame.display.get_active()

    if active:
        WIN.fill("#666666")
        pool.draw(WIN)
        if update_widget:
            update_widget.draw(WIN)

        time = widget_timeout.text

        color = (0, 0, 0) if time.isnumeric() else (255, 0, 0)
        WIN.blit(font.render("Timeout (min):", True, color), (25, 25))

        is_valid_input = time.isnumeric()

        if not is_valid_input:
            widget_save.disable()
            widget_runit.disable()
        else:
            widget_save.enable()
            if not is_running:
                widget_runit.enable()
            else:
                widget_runit.disable()

        if widget_save.is_clicked() and is_valid_input:
            with open(config_path, "w") as f:
                json.dump({"timeout": int(time) * 60}, f, indent=4)
            log("Saved configuration")

        if widget_runit.is_clicked() and is_valid_input and (loop_thread is None or not loop_thread.is_alive()):
            stop_requested = False
            widget_runit.disable()
            widget_runit.change_text("Running...")
            widget_stopit.enable()
            loop_thread = threading.Thread(target=launch_loop, args=(time,), daemon=True)
            loop_thread.start()

        if widget_stopit.is_clicked() and process:
            log("Stop button clicked")
            stop_requested = True
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                log("Force killed process", level=1)
                process.kill()
            log("Process killed")
            process = None

        pygame.display.flip()
        clock.tick(60)

pygame.quit()

if process:
    stop_requested = True
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        log("Force killed process", level=1)
        process.kill()
    log("Process killed")
    process = None

sys.exit(0)
