import os
import time
import json
import threading
import tkinter as tk
from tkinter import filedialog, simpledialog
import re

CONFIG_FILE = "config.json"
FILE_EXTENSION = ".gzr"

MAX_WAIT_SECONDS = 180
monitoring_thread = None

# Update RENAMED_PATTERN to match your actual renamed filename format
RENAMED_PATTERN = re.compile(r"^\d{3}_.+\[[^\[\]]+\]_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.gzr$")


#Frame initialization
root = tk.Tk()
root.title("GunZ Replay Organizer")
root.iconbitmap("icon.ico") # Make an Icon for the program
root.geometry("700x400")

main_frame = tk.Frame(root)
main_frame.pack(padx=10, pady=10, fill="both", expand=True)

# Left frame for controls
left_frame = tk.Frame(main_frame)
left_frame.pack(side="left", fill="y")


# Right frame for log
right_frame = tk.Frame(main_frame)
right_frame.pack(side="left", fill="both", expand=True, padx=(20,0))

log_label = tk.Label(right_frame, text="Log")
log_label.pack(anchor="w")

log_text = tk.Text(right_frame, height=12, width=50, state="disabled")
log_text.pack(fill="both", expand=True)

def log_message(msg):
    log_text.config(state="normal")
    log_text.insert("end", msg + "\n")
    log_text.see("end")
    log_text.config(state="disabled")








def ensure_config():
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "WATCHED_FOLDER": "",
            "FILE_IDENTIFIER": "Replay",
            "counter": 1
        }
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(default_config, f, indent=4)
            log_message("config.json not found. Created default config.json.")
        except Exception as e:
            log_message(f"Error creating default config.json: {e}")


# Load config or set defaults
def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
                return {
                    "WATCHED_FOLDER": cfg.get("WATCHED_FOLDER", ""),
                    "FILE_IDENTIFIER": cfg.get("FILE_IDENTIFIER", "Replay"),
                    "counter": cfg.get("counter", 1)
                }
        else:
            return {"WATCHED_FOLDER": "", "FILE_IDENTIFIER": "Replay", "counter": 1}
    except Exception as e:
        log_message(f"Error loading config: {e}")
        return {"WATCHED_FOLDER": "", "FILE_IDENTIFIER": "Replay", "counter": 1}

def save_config():
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump({
                "WATCHED_FOLDER": WATCHED_FOLDER,
                "FILE_IDENTIFIER": FILE_IDENTIFIER,
                "counter": counter
            }, f, indent=4)
    except Exception as e:
        log_message(f"Error saving config: {e}")



# Load initial config
ensure_config()
config = load_config()
WATCHED_FOLDER = config["WATCHED_FOLDER"]
FILE_IDENTIFIER = config["FILE_IDENTIFIER"]
counter = config["counter"]

def select_folder():
    global WATCHED_FOLDER
    try:
        folder = filedialog.askdirectory()
        if folder:
            WATCHED_FOLDER = folder
            folder_label.config(text=f"Watching: {WATCHED_FOLDER}")
            save_config()
    except Exception as e:
        log_message(f"Error selecting folder: {e}")

def set_identifier():
    global FILE_IDENTIFIER
    try:
        identifier = simpledialog.askstring("Set Identifier", "Enter file identifier:")
        if identifier:
            FILE_IDENTIFIER = identifier
            counter = 1  # Reset counter when identifier changes
            identifier_label.config(text=f"Identifier: {FILE_IDENTIFIER}")
            save_config()
            log_message(f"Identifier set to: {FILE_IDENTIFIER}. Counter reset to 1.")
    except Exception as e:
        log_message(f"Error setting identifier: {e}")

def get_next_filename(timestamp, gamemode):
    global counter
    try:
        gamemode_clean = gamemode.replace("[", "").replace("]", "")
        while True:
            filename = f"{counter:03d}_{FILE_IDENTIFIER}[{gamemode_clean}]_{timestamp}{FILE_EXTENSION}"
            if not os.path.exists(os.path.join(WATCHED_FOLDER, filename)):
                return filename
            counter += 1
    except Exception as e:
        log_message(f"Error generating filename: {e}")
        return f"error_{int(time.time())}{FILE_EXTENSION}"

def is_renamed(fname):
    return bool(RENAMED_PATTERN.match(fname))

def monitor_folder():
    global counter
    try:
        pending_files = {}
        file_timestamps = {}
        while True:
            time.sleep(1)
            try:
                current_files = set(f for f in os.listdir(WATCHED_FOLDER) if f.endswith(FILE_EXTENSION))
            except Exception as e:
                log_message(f"Error reading folder: {e}")
                continue

            # Add new files to pending_files, but skip already-renamed files
            for fname in current_files:
                if is_renamed(fname):
                    # Make sure to remove any already-renamed files from pending_files
                    if fname in pending_files:
                        pending_files.pop(fname, None)
                        file_timestamps.pop(fname, None)
                    continue
                if fname not in pending_files:
                    pending_files[fname] = {'wait': 0, 'last_size': None, 'last_mtime': None, 'stable': 0}
                    log_message(f"Queued new file: {fname}")

            # Remove files that no longer exist
            for fname in list(pending_files.keys()):
                if fname not in current_files or is_renamed(fname):
                    log_message(f"File disappeared or already renamed: {fname}")
                    pending_files.pop(fname, None)
                    file_timestamps.pop(fname, None)

            # Process pending files
            for fname in list(pending_files.keys()):
                file_path = os.path.join(WATCHED_FOLDER, fname)
                try:
                    stat = os.stat(file_path)
                    size = stat.st_size
                    mtime = stat.st_mtime
                except Exception:
                    log_message(f"Could not stat file (may have been deleted): {fname}")
                    continue  # File might have been deleted/moved

                entry = pending_files[fname]

                if size == 0:
                    entry['wait'] += 1
                    # if entry['wait'] % 10 == 0:
                    #     log_message(f"Waiting for file to finalize (still 0 bytes): {fname} ({entry['wait']}s)")
                    if entry['wait'] > MAX_WAIT_SECONDS:
                        log_message(f"File {fname} did not finalize in time (>{MAX_WAIT_SECONDS}s), skipping.")
                        pending_files.pop(fname, None)
                        file_timestamps.pop(fname, None)
                    continue

                if entry['last_size'] == size and entry['last_mtime'] == mtime:
                    entry['stable'] += 1
                    if entry['stable'] == 1:
                        log_message(f"File {fname} appears finalized, checking for stability...")
                else:
                    if entry['stable'] > 0:
                        log_message(f"File {fname} changed again, resetting stability counter.")
                    entry['stable'] = 0
                entry['last_size'] = size
                entry['last_mtime'] = mtime

                if entry['stable'] >= 3:
                    gamemode = fname.split("_", 1)[0]
                    try:
                        with open(file_path, "rb"):
                            pass
                        if fname not in file_timestamps:
                            file_timestamps[fname] = time.strftime("%Y-%m-%d_%H-%M-%S")
                        timestamp = file_timestamps[fname]
                        new_name = get_next_filename(timestamp, gamemode)
                        os.rename(
                            file_path,
                            os.path.join(WATCHED_FOLDER, new_name)
                        )
                        counter += 1
                        save_config()
                        log_message(f"Renamed {fname} to {new_name}")
                        # Remove the old name from the queue
                        pending_files.pop(fname, None)
                        file_timestamps.pop(fname, None)
                    except Exception as e:
                        log_message(f"Error renaming {fname}: {e}")
    except Exception as e:
        log_message(f"Error in monitor_folder: {e}")

def start_monitoring():
    global monitoring_thread
    try:
        if not WATCHED_FOLDER:
            log_message("No folder selected to monitor.")
            return
        if monitoring_thread is not None and monitoring_thread.is_alive():
            log_message("Monitoring is already running.")
            return
        monitoring_thread = threading.Thread(target=monitor_folder, daemon=True)
        monitoring_thread.start()
        log_message(f"Monitoring started. Watching: {WATCHED_FOLDER} Starting with counter: {counter}")
    except Exception as e:
        log_message(f"Error starting monitoring: {e}")

def reset_counter():
    global counter
    try:
        counter = 1
        save_config()
        log_message("Counter reset to 1.")
    except Exception as e:
        log_message(f"Error resetting counter: {e}")



#UI Setup New


folder_btn = tk.Button(left_frame, text="Select Folder", command=select_folder)
folder_btn.pack(pady=5)

folder_label = tk.Label(left_frame, text=f"Watching: {WATCHED_FOLDER or '(none)'}")
folder_label.pack()

identifier_btn = tk.Button(left_frame, text="Set Identifier", command=set_identifier)
identifier_btn.pack(pady=5)

identifier_label = tk.Label(left_frame, text=f"Identifier: {FILE_IDENTIFIER}")
identifier_label.pack()

start_btn = tk.Button(left_frame, text="Start Monitoring", command=start_monitoring)
start_btn.pack(pady=10)

reset_btn = tk.Button(left_frame, text="Reset Counter", command=reset_counter)
reset_btn.pack(pady=5)

status_label = tk.Label(left_frame, text="")
status_label.pack()



root.mainloop()